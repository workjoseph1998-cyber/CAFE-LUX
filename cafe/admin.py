import json
import re
import secrets
import time
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import (
    Blueprint,
    request,
    session,
    redirect,
    url_for,
    render_template,
    flash,
    abort,
    current_app,
    send_file,
)
from werkzeug.security import check_password_hash, generate_password_hash
from .db import db, audit, settings, DEFAULTS
from .public import integer, cents
from .catalog import publication_issues, validate_publication

bp = Blueprint("admin", __name__, url_prefix="/admin")
STATUSES = [
    "Pending WhatsApp Submission",
    "Received",
    "Confirmed",
    "Preparing",
    "Ready",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]


def protected(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        user = (
            db()
            .execute(
                "SELECT * FROM users WHERE id=? AND active=1", (session.get("user_id"),)
            )
            .fetchone()
        )
        if not user or user["session_version"] != session.get("session_version"):
            return redirect(url_for("admin.login"))
        if time.time() - session.get("auth_time", 0) > 3600:
            session.clear()
            return redirect(url_for("admin.login"))
        if user["role"] != "admin" and request.endpoint not in (
            "admin.dashboard",
            "admin.orders",
            "admin.order_detail",
            "admin.notify",
            "admin.logout",
        ):
            abort(403)
        return fn(*a, **kw)

    return wrapped


def text(name, limit=5000):
    value = request.form.get(name, "").strip()
    if len(value) > limit:
        raise ValueError(name + " is too long.")
    return value


def checked(name):
    return int(request.form.get(name) == "1")


def image_reference(value):
    if (
        value
        and not db()
        .execute("SELECT 1 FROM media WHERE filename=?", (value,))
        .fetchone()
    ):
        raise ValueError("Choose an uploaded image.")
    return value


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        now = time.time()
        row = db().execute("SELECT * FROM login_attempts WHERE ip=?", (ip,)).fetchone()
        if row and row["until"] > now:
            flash("Too many attempts. Try again in 15 minutes.")
            return render_template("login.html"), 429
        username = request.form.get("username", "")[:100]
        user = (
            db()
            .execute("SELECT * FROM users WHERE username=? AND active=1", (username,))
            .fetchone()
        )
        # Always evaluate a password hash, including for unknown users.
        good = check_password_hash(
            user["password"] if user else current_app.config["DUMMY_HASH"],
            request.form.get("password", "")[:1024],
        )
        if user and good:
            session.clear()
            session.update(
                user_id=user["id"],
                username=user["username"],
                session_version=user["session_version"],
                auth_time=now,
                csrf=secrets.token_urlsafe(32),
            )
            session.permanent = True
            db().execute("DELETE FROM login_attempts WHERE ip=?", (ip,))
            audit("Login")
            db().commit()
            return redirect(url_for("admin.dashboard"))
        db().execute("BEGIN IMMEDIATE")
        row = db().execute("SELECT * FROM login_attempts WHERE ip=?", (ip,)).fetchone()
        attempts = (row["attempts"] if row and now - row["until"] < 900 else 0) + 1
        db().execute(
            "INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)",
            (ip, attempts, now + 900 if attempts >= 5 else now),
        )
        db().commit()
        flash("Invalid credentials.")
    return render_template("login.html")


@bp.post("/logout")
@protected
def logout():
    session.clear()
    return redirect(url_for("public.home"))


@bp.get("")
@bp.get("/")
@protected
def dashboard():
    conn = db()
    stats = {
        row["status"]: row["n"]
        for row in conn.execute("SELECT status,count(*) n FROM orders GROUP BY status")
    }
    stats["today"] = conn.execute(
        "SELECT count(*) FROM orders WHERE date(created)=date('now')"
    ).fetchone()[0]
    attention_sql = """ FROM products p WHERE p.image='' OR p.description='' OR NOT EXISTS (SELECT 1 FROM variants v WHERE v.product_id=p.id AND v.price IS NOT NULL AND v.active=1)"""
    stats["attention"] = conn.execute("SELECT count(*)" + attention_sql).fetchone()[0]
    return render_template(
        "admin_dashboard.html",
        stats=stats,
        revenue=conn.execute(
            "SELECT currency,sum(subtotal) total FROM orders WHERE status='Delivered' GROUP BY currency"
        ).fetchall(),
        recent=conn.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT 10"
        ).fetchall(),
        attention=conn.execute(
            "SELECT p.*, (SELECT count(*) FROM variants v WHERE v.product_id=p.id AND v.price IS NULL) missing_prices"
            + attention_sql
            + " ORDER BY p.active,p.id LIMIT 10"
        ).fetchall(),
        inventory=conn.execute(
            "SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id WHERE stock<=5 ORDER BY stock LIMIT 10"
        ).fetchall(),
        audit=conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 8").fetchall(),
    )


@bp.get("/drinks")
@bp.get("/coffee")
@bp.get("/products")
@protected
def products():
    kind = (
        "drink"
        if request.path.endswith("/drinks")
        else (
            "ground"
            if request.path.endswith("/coffee")
            else request.args.get("kind", "")
        )
    )
    clauses, args = [], []
    if kind in ("drink", "ground"):
        clauses.append("p.kind=?")
        args.append(kind)
    query = request.args.get("q", "").strip()[:100]
    if query:
        clauses.append("(p.name LIKE ? OR p.name_ar LIKE ?)")
        args.extend(["%" + query + "%"] * 2)
    status = request.args.get("status", "")
    if status in ("draft", "published"):
        clauses.append("p.active=?")
        args.append(int(status == "published"))
    category = request.args.get("category", type=int)
    if category:
        clauses.append("p.category_id=?")
        args.append(category)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sort = {
        "name": "p.name COLLATE NOCASE",
        "category": "c.position,c.name",
        "position": "p.position,p.id",
        "status": "p.active,p.name",
    }.get(request.args.get("sort"), "c.position,p.position,p.id")
    page = max(1, request.args.get("page", 1, type=int) or 1)
    count = db().execute("SELECT count(*) FROM products p" + where, args).fetchone()[0]
    rows = (
        db()
        .execute(
            """SELECT p.*,c.name category,
        (SELECT count(*) FROM variants WHERE product_id=p.id) variant_count,
        (SELECT min(price) FROM variants WHERE product_id=p.id) min_price,
        (SELECT count(*) FROM variants WHERE product_id=p.id AND price IS NULL) missing_prices,
        (SELECT sum(stock) FROM variants WHERE product_id=p.id) stock
        FROM products p LEFT JOIN categories c ON c.id=p.category_id"""
            + where
            + " ORDER BY "
            + sort
            + " LIMIT 30 OFFSET ?",
            [*args, (page - 1) * 30],
        )
        .fetchall()
    )
    items = [dict(p, issues=publication_issues(dict(p))) for p in rows]
    return render_template(
        "admin_products.html",
        products=items,
        kind=kind,
        page=page,
        pages=max(1, (count + 29) // 30),
        count=count,
        categories=db()
        .execute("SELECT * FROM categories ORDER BY position,name")
        .fetchall(),
    )


@bp.post("/products/bulk")
@protected
def bulk_products():
    try:
        ids = sorted(set(integer(x, 1) for x in request.form.getlist("ids")))
        if not ids or len(ids) > 30:
            raise ValueError("Select up to 30 products.")
        action = request.form.get("action")
        if action not in ("draft", "publish"):
            raise ValueError("Choose draft or publish.")
        conn = db()
        conn.execute("BEGIN IMMEDIATE")
        for pid in ids:
            product = conn.execute(
                "SELECT * FROM products WHERE id=?", (pid,)
            ).fetchone()
            if not product:
                raise ValueError("Product no longer exists.")
            if action == "publish":
                validate_publication(product)
            conn.execute(
                "UPDATE products SET active=? WHERE id=?",
                (int(action == "publish"), pid),
            )
        audit(f"Bulk {action}: {ids}")
        conn.commit()
        flash(f"Updated {len(ids)} product(s).")
    except ValueError as e:
        db().rollback()
        flash(str(e))
    return redirect(url_for("admin.products"))


@bp.post("/products/<int:pid>/quick")
@protected
def quick_product(pid):
    try:
        conn = db()
        conn.execute("BEGIN IMMEDIATE")
        product = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not product:
            abort(404)
        active = checked("active")
        if active:
            validate_publication(product)
        conn.execute(
            "UPDATE products SET active=?,position=? WHERE id=?",
            (active, integer(request.form.get("position", "0")), pid),
        )
        audit(f"Quick product update {pid}")
        conn.commit()
        flash("Product saved.")
    except ValueError as e:
        db().rollback()
        flash(str(e))
    return redirect(url_for("admin.products", kind=request.form.get("kind", "")))


@bp.route("/products/<int:pid>", methods=["GET", "POST"])
@protected
def edit_product(pid):
    p = (
        db().execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if pid
        else None
    )
    if pid and not p:
        abort(404)
    if request.method == "POST":
        try:
            kind = text("kind", 20)
            if kind not in ("drink", "ground"):
                raise ValueError("Invalid product type.")
            name = text("name", 150)
            if not name:
                raise ValueError("A product name is required.")
            category = (
                integer(request.form["category_id"], 1)
                if request.form.get("category_id")
                else None
            )
            temperature = text("temperature", 10)
            if temperature not in ("hot", "cold", "both"):
                raise ValueError("Invalid temperature.")
            gallery = [
                image_reference(x.strip())
                for x in request.form.getlist("gallery")
                if x.strip()
            ]
            fields = dict(
                name=name,
                name_ar=text("name_ar", 150),
                description=text("description"),
                description_ar=text("description_ar"),
                kind=kind,
                category_id=category,
                image=image_reference(text("image", 100)),
                gallery=json.dumps(gallery),
                temperature=temperature,
                active=int(
                    checked("active") or request.form.get("intent") == "publish"
                ),
                featured=checked("featured"),
                position=integer(request.form.get("position", "0")),
                **{
                    f: text(f, 1000)
                    for f in (
                        "roast",
                        "origin",
                        "bean",
                        "notes",
                        "grinds",
                        "preparation",
                    )
                },
            )
            db().execute("BEGIN IMMEDIATE")
            if fields["active"]:
                validate_publication({**fields, "id": pid})
            if pid:
                db().execute(
                    "UPDATE products SET "
                    + ",".join(f"{f}=?" for f in fields)
                    + " WHERE id=?",
                    (*fields.values(), pid),
                )
            else:
                cur = db().execute(
                    "INSERT INTO products("
                    + ",".join(fields)
                    + ") VALUES ("
                    + ",".join("?" for _ in fields)
                    + ")",
                    tuple(fields.values()),
                )
                pid = cur.lastrowid
            audit("Saved product " + str(pid))
            db().commit()
            flash("Product saved.")
            return redirect(url_for("admin.edit_product", pid=pid))
        except (ValueError, __import__("sqlite3").IntegrityError) as e:
            db().rollback()
            flash(str(e))
    return render_template(
        "admin_product.html",
        p=p,
        categories=db()
        .execute("SELECT * FROM categories ORDER BY position")
        .fetchall(),
        media=db().execute("SELECT * FROM media").fetchall(),
        variants=db()
        .execute("SELECT * FROM variants WHERE product_id=?", (pid,))
        .fetchall(),
        addons=db()
        .execute("SELECT * FROM addons WHERE product_id=?", (pid,))
        .fetchall(),
    )


@bp.post("/products/<int:pid>/option")
@protected
def option(pid):
    if not db().execute("SELECT 1 FROM products WHERE id=?", (pid,)).fetchone():
        abort(404)
    try:
        kind = request.form.get("kind")
        oid = integer(request.form.get("id", "0"))
        if kind == "variant":
            label = text("label", 100)
            if not label:
                raise ValueError("Label required.")
            values = dict(
                sku=text("sku", 100),
                position=integer(request.form.get("position", "0")),
                allowed_grinds=text("allowed_grinds", 1000),
                allowed_temperatures=text("allowed_temperatures", 100),
                label=label,
                label_ar=text("label_ar", 100),
                grams=(
                    integer(request.form["grams"], 1, 100000)
                    if request.form.get("grams")
                    else None
                ),
                price=(
                    cents(request.form["price"]) if request.form.get("price") else None
                ),
                stock=(
                    integer(request.form["stock"])
                    if request.form.get("stock")
                    else None
                ),
                active=checked("active"),
            )
            table = "variants"
        elif kind == "addon":
            name = text("name", 100)
            if not name:
                raise ValueError("Name required.")
            values = dict(
                name=name,
                option_group=text("option_group", 100),
                name_ar=text("name_ar", 100),
                price=cents(request.form["price"]) if request.form.get("price") else 0,
                price_pending=int(not bool(request.form.get("price"))),
                active=checked("active"),
            )
            table = "addons"
        else:
            abort(400)
        if kind == "addon" and values["active"] and values["price_pending"]:
            raise ValueError(
                "Enter an explicit extra price (0 is allowed) before enabling it."
            )
        if oid:
            db().execute(
                "UPDATE "
                + table
                + " SET "
                + ",".join(f"{k}=?" for k in values)
                + " WHERE id=? AND product_id=?",
                (*values.values(), oid, pid),
            )
        else:
            db().execute(
                "INSERT INTO "
                + table
                + "(product_id,"
                + ",".join(values)
                + ") VALUES ("
                + ",".join("?" for _ in range(len(values) + 1))
                + ")",
                (pid, *values.values()),
            )
        product = db().execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if product["active"]:
            validate_publication(product)
        audit("Updated " + kind + " for product " + str(pid))
        db().commit()
        flash("Option saved.")
    except ValueError as e:
        db().rollback()
        flash(str(e))
    return redirect(url_for("admin.edit_product", pid=pid))


@bp.route("/categories", methods=["GET", "POST"])
@protected
def categories():
    if request.method == "POST":
        try:
            cid = integer(request.form.get("id", "0"))
            if "delete" in request.form:
                db().execute(
                    "UPDATE products SET category_id=NULL WHERE category_id=?", (cid,)
                )
                db().execute("DELETE FROM categories WHERE id=?", (cid,))
            else:
                name = text("name", 100)
                if not name:
                    raise ValueError("Name required.")
                values = (
                    name,
                    text("name_ar", 100),
                    integer(request.form.get("position", "0")),
                    checked("active"),
                )
                if cid:
                    db().execute(
                        "UPDATE categories SET name=?,name_ar=?,position=?,active=? WHERE id=?",
                        (*values, cid),
                    )
                else:
                    db().execute(
                        "INSERT INTO categories(name,name_ar,position,active) VALUES (?,?,?,?)",
                        values,
                    )
            audit("Updated categories")
            db().commit()
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("admin.categories"))
    return render_template(
        "admin_categories.html",
        categories=db()
        .execute("SELECT * FROM categories ORDER BY position")
        .fetchall(),
    )


@bp.route("/settings", methods=["GET", "POST"])
@protected
def config():
    if request.method == "POST":
        try:
            values = {}
            for key in DEFAULTS:
                if key not in request.form:
                    continue
                value = text(key)
                if key in ("delivery_fee", "minimum"):
                    cents(value)
                if key == "currency" and not re.fullmatch("[A-Z]{3}", value):
                    raise ValueError("Currency must be a three-letter code.")
                if key in (
                    "logo",
                    "hero_image",
                    "story_image",
                    "cafe_image",
                    "choice_drink_image",
                    "choice_coffee_image",
                ):
                    image_reference(value)
                if (
                    key
                    in (
                        "maps",
                        "map_embed",
                        "instagram",
                        "facebook",
                        "tiktok",
                        "youtube",
                    )
                    and value
                ):
                    u = urlsplit(value)
                    if u.scheme != "https" or not u.hostname or u.username:
                        raise ValueError("Links must use HTTPS.")
                    if key == "map_embed" and (
                        u.hostname != "www.google.com"
                        or not u.path.startswith("/maps/embed")
                    ):
                        raise ValueError("Use a www.google.com/maps/embed URL.")
                if key == "whatsapp" and value and not re.fullmatch(r"\d{6,20}", value):
                    raise ValueError("WhatsApp requires international digits only.")
                if (
                    key == "email"
                    and value
                    and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value)
                ):
                    raise ValueError("Invalid email.")
                if key in (
                    "ordering",
                    "pickup",
                    "delivery",
                    "pickup_time",
                    "show_drinks",
                    "show_ground",
                    "show_story",
                    "show_location",
                ) and value not in ("0", "1"):
                    raise ValueError("Invalid switch.")
                if key == "retention_days":
                    integer(value, 1, 3650)
                values[key] = value
            merged = {**settings(), **values}
            if (
                merged["ordering"] == "1"
                and merged["pickup"] != "1"
                and merged["delivery"] != "1"
            ):
                raise ValueError("Enable a fulfillment method or close ordering.")
            if "brand" in values and not values["brand"]:
                raise ValueError("Brand name is required.")
            if (
                values.get("ordering") == "1"
                and not db()
                .execute(
                    "SELECT 1 FROM products p JOIN variants v ON p.id=v.product_id WHERE p.active=1 AND v.active=1 AND v.price IS NOT NULL"
                )
                .fetchone()
            ):
                raise ValueError(
                    "Publish a product with a price before enabling ordering."
                )
            for k, v in values.items():
                db().execute("UPDATE settings SET value=? WHERE key=?", (v, k))
            audit("Updated website settings")
            db().commit()
            flash("Settings saved.")
        except ValueError as e:
            db().rollback()
            flash(str(e))
        return redirect(url_for("admin.config"))
    return render_template(
        "admin_settings.html", media=db().execute("SELECT * FROM media").fetchall()
    )


@bp.route("/media", methods=["GET", "POST"])
@protected
def media():
    if request.method == "POST":
        try:
            conn = db()
            if "upload" in request.files:
                file = request.files["upload"]
                Image.MAX_IMAGE_PIXELS = 20000000
                with Image.open(file.stream) as img:
                    if img.format not in ("JPEG", "PNG", "WEBP"):
                        raise ValueError("Use JPEG, PNG or WebP images.")
                    if img.width * img.height > 20000000:
                        raise ValueError("Image is too large.")
                    img = ImageOps.exif_transpose(img).convert("RGB")
                    img.thumbnail((1600, 1600))
                    filename = secrets.token_hex(16) + ".jpg"
                    img.save(
                        Path(current_app.config["DATA_DIR"]) / "uploads" / filename,
                        "JPEG",
                        quality=85,
                        optimize=True,
                    )
                conn.execute(
                    "INSERT INTO media(filename,title,alt) VALUES (?,?,?)",
                    (filename, text("title", 150) or "Image", text("alt", 300)),
                )
            else:
                mid = integer(request.form.get("id"), 1)
                m = conn.execute("SELECT * FROM media WHERE id=?", (mid,)).fetchone()
                if not m:
                    abort(404)
                if "delete" in request.form:
                    if media_usage(m["filename"]):
                        raise ValueError(
                            "Image is in use. Replace its references before deleting."
                        )
                    conn.execute("DELETE FROM media WHERE id=?", (mid,))
                    (
                        Path(current_app.config["DATA_DIR"]) / "uploads" / m["filename"]
                    ).unlink(missing_ok=True)
                else:
                    conn.execute(
                        "UPDATE media SET title=?,alt=? WHERE id=?",
                        (text("title", 150), text("alt", 300), mid),
                    )
            if request.form.get("assign_product") and "upload" in request.files:
                pid = integer(request.form["assign_product"], 1)
                if not conn.execute(
                    "SELECT 1 FROM products WHERE id=?", (pid,)
                ).fetchone():
                    raise ValueError("Product not found.")
                conn.execute("UPDATE products SET image=? WHERE id=?", (filename, pid))
            audit("Updated media library")
            conn.commit()
            flash("Media saved.")
            if request.form.get("assign_product"):
                return redirect(
                    url_for(
                        "admin.edit_product",
                        pid=integer(request.form["assign_product"], 1),
                    )
                )
        except (
            ValueError,
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
        ) as e:
            flash("Upload or media action rejected: " + str(e))
        return redirect(url_for("admin.media"))
    rows = [
        dict(m, usage=media_usage(m["filename"]))
        for m in db().execute("SELECT * FROM media ORDER BY id DESC")
    ]
    return render_template("admin_media.html", media=rows)


def media_usage(filename):
    uses = []
    for p in db().execute("SELECT * FROM products"):
        if p["image"] == filename or filename in json.loads(p["gallery"]):
            uses.append("Product: " + p["name"])
    uses.extend(
        "Website: " + r["key"]
        for r in db().execute("SELECT * FROM settings WHERE value=?", (filename,))
    )
    return uses


@bp.route("/orders", methods=["GET", "POST"])
@protected
def orders():
    if request.method == "POST":
        try:
            oid = integer(request.form.get("id"), 1)
            status = request.form.get("status")
            if status not in STATUSES:
                raise ValueError("Invalid status.")
            conn = db()
            conn.execute("BEGIN IMMEDIATE")
            order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            if not order:
                abort(404)
            if "anonymize" in request.form:
                if order["status"] not in ("Delivered", "Cancelled"):
                    raise ValueError(
                        "Close the order before removing customer details."
                    )
                conn.execute(
                    "UPDATE orders SET name='[removed]',phone='[removed]',address='',notes='',requested_time='' WHERE id=?",
                    (oid,),
                )
                audit("Removed customer details from " + order["reference"])
                conn.commit()
                return redirect(url_for("admin.orders"))
            if order["status"] == "Cancelled" and status != "Cancelled":
                raise ValueError(
                    "Cancelled orders cannot be reopened. Create a new order."
                )
            if (
                status
                in ("Confirmed", "Preparing", "Ready", "Out for Delivery", "Delivered")
                and not order["stock_deducted"]
            ):
                stock_changes = []
                for item in json.loads(order["items"]):
                    variant = conn.execute(
                        "SELECT stock FROM variants WHERE id=?", (item["variant"],)
                    ).fetchone()
                    if not variant:
                        raise ValueError(
                            "A product variant was removed. Review this order."
                        )
                    if variant["stock"] is not None:
                        result = conn.execute(
                            "UPDATE variants SET stock=stock-? WHERE id=? AND stock>=?",
                            (item["qty"], item["variant"], item["qty"]),
                        )
                        if result.rowcount != 1:
                            raise ValueError(
                                "Insufficient stock to confirm this order."
                            )
                        stock_changes.append(
                            {"variant": item["variant"], "qty": item["qty"]}
                        )
                conn.execute(
                    "UPDATE orders SET stock_deducted=1,stock_changes=? WHERE id=?",
                    (json.dumps(stock_changes), oid),
                )
            if (
                status == "Cancelled"
                and order["status"] != "Cancelled"
                and order["stock_deducted"]
            ):
                for item in json.loads(
                    order["stock_changes"]
                    if order["stock_changes"] is not None
                    else order["items"]
                ):
                    conn.execute(
                        "UPDATE variants SET stock=stock+? WHERE id=? AND stock IS NOT NULL",
                        (item["qty"], item["variant"]),
                    )
                conn.execute("UPDATE orders SET stock_deducted=0 WHERE id=?", (oid,))
            conn.execute(
                "INSERT INTO order_history(order_id,status,username) VALUES (?,?,?)",
                (oid, status, session["username"]),
            )
            conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
            audit("Order " + order["reference"] + " → " + status)
            conn.commit()
        except ValueError as e:
            db().rollback()
            flash(str(e))
        return redirect(url_for("admin.orders"))
    page = max(1, request.args.get("page", 1, type=int) or 1)
    status = request.args.get("status", "")
    date = request.args.get("date", "")
    query = request.args.get("q", "")[:100]
    where = " WHERE (?='' OR status=?) AND (?='' OR date(created)=?) AND (?='' OR reference LIKE ? OR name LIKE ? OR phone LIKE ?)"
    args = [status, status, date, date, query, *(["%" + query + "%"] * 3)]
    count = db().execute("SELECT count(*) FROM orders" + where, args).fetchone()[0]
    rows = (
        db()
        .execute(
            "SELECT * FROM orders" + where + " ORDER BY id DESC LIMIT 30 OFFSET ?",
            [*args, (page - 1) * 30],
        )
        .fetchall()
    )
    return render_template(
        "admin_orders.html",
        orders=rows,
        statuses=STATUSES,
        page=page,
        pages=max(1, (count + 29) // 30),
        count=count,
    )


@bp.route("/users", methods=["GET", "POST"])
@protected
def users():
    if request.method == "POST":
        try:
            username = text("username", 100)
            password = text("password", 1024)
            role = request.form.get("role", "admin")
            if role not in ("admin", "operator"):
                raise ValueError("Invalid role.")
            if username == session["username"] and role != "admin":
                raise ValueError("You cannot remove your own administrative access.")
            if not re.fullmatch(r"[A-Za-z0-9_.-]{3,100}", username):
                raise ValueError(
                    "Use 3–100 letters, digits, dots, dashes or underscores."
                )
            existing = (
                db()
                .execute("SELECT * FROM users WHERE username=?", (username,))
                .fetchone()
            )
            if "disable" in request.form:
                if existing and existing["id"] == session["user_id"]:
                    raise ValueError("You cannot disable yourself.")
                db().execute(
                    "UPDATE users SET active=0,session_version=session_version+1 WHERE username=?",
                    (username,),
                )
            else:
                if len(password) < 12:
                    raise ValueError("Use at least 12 characters.")
                hashed = generate_password_hash(password)
                if existing:
                    db().execute(
                        "UPDATE users SET password=?,role=?,active=1,session_version=session_version+1 WHERE id=?",
                        (hashed, role, existing["id"]),
                    )
                else:
                    db().execute(
                        "INSERT INTO users(username,password,role) VALUES (?,?,?)",
                        (username, hashed, role),
                    )
            audit("Updated admin " + username)
            db().commit()
            flash("Administrator saved.")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("admin.users"))
    return render_template(
        "admin_users.html",
        users=db().execute("SELECT id,username,active,role FROM users").fetchall(),
    )


@bp.post("/backup")
@protected
def backup():
    from .commands import make_backup

    path = make_backup()
    audit("Created backup")
    db().commit()
    return send_file(path, as_attachment=True, download_name=path.name)


@bp.post("/retention")
@protected
def retention():
    days = integer(settings()["retention_days"], 1, 3650)
    db().execute(
        "UPDATE orders SET name='[removed]',phone='[removed]',address='',notes='',requested_time='' WHERE status IN ('Delivered','Cancelled') AND datetime(created)<datetime('now',?)",
        (f"-{days} days",),
    )
    audit("Anonymized closed orders older than " + str(days) + " days")
    db().commit()
    flash("Retention policy applied. Existing backups must be expired separately.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/operations", methods=["GET", "POST"])
@protected
def operations():
    if request.method == "POST":
        try:
            kind = request.form.get("kind")
            oid = integer(request.form.get("id", "0"))
            if kind == "number":
                phone = text("phone", 20)
                if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
                    raise ValueError(
                        "Use international format, for example +961 followed by the full number."
                    )
                label = text("label", 100)
                if not label:
                    raise ValueError("A label is required.")
                default = checked("is_default")
                active = checked("active")
                if default and not active:
                    raise ValueError("The default number must be active.")
                if default:
                    db().execute("UPDATE whatsapp_numbers SET is_default=0")
                if oid:
                    db().execute(
                        "UPDATE whatsapp_numbers SET label=?,phone=?,active=?,is_default=? WHERE id=?",
                        (label, phone, active, default, oid),
                    )
                else:
                    db().execute(
                        "INSERT INTO whatsapp_numbers(label,phone,active,is_default) VALUES (?,?,?,?)",
                        (label, phone, active, default),
                    )
            elif kind == "area":
                name = text("name", 100)
                if not name:
                    raise ValueError("Area name is required.")
                values = (
                    name,
                    checked("active"),
                    cents(request.form["fee"]) if request.form.get("fee") else None,
                    cents(request.form.get("minimum", "0")),
                    text("estimate", 100),
                    (
                        integer(request.form["whatsapp_id"], 1)
                        if request.form.get("whatsapp_id")
                        else None
                    ),
                )
                if oid:
                    db().execute(
                        "UPDATE delivery_areas SET name=?,active=?,fee=?,minimum=?,estimate=?,whatsapp_id=? WHERE id=?",
                        (*values, oid),
                    )
                else:
                    db().execute(
                        "INSERT INTO delivery_areas(name,active,fee,minimum,estimate,whatsapp_id) VALUES (?,?,?,?,?,?)",
                        values,
                    )
            elif kind == "slot":
                label = text("label", 100)
                if not label:
                    raise ValueError(
                        "Slot label is required; include the date and time range."
                    )
                if oid:
                    db().execute(
                        "UPDATE schedule_slots SET label=?,active=? WHERE id=?",
                        (label, checked("active"), oid),
                    )
                else:
                    db().execute(
                        "INSERT INTO schedule_slots(label,active) VALUES (?,?)",
                        (label, checked("active")),
                    )
            elif kind == "hours":
                for key in ("opening", "closing"):
                    if not re.fullmatch(
                        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", text(key, 5)
                    ):
                        raise ValueError("Enter valid opening and closing hours.")
                from datetime import date

                for day in text("closures", 2000).split():
                    date.fromisoformat(day)
                for key in (
                    "ordering",
                    "paused",
                    "scheduled",
                    "opening",
                    "closing",
                    "closures",
                ):
                    value = (
                        str(checked(key))
                        if key in ("ordering", "paused", "scheduled")
                        else text(key, 2000)
                    )
                    db().execute(
                        "UPDATE settings SET value=? WHERE key=?", (value, key)
                    )
            else:
                raise ValueError("Invalid settings section.")
            audit("Updated operations: " + str(kind))
            db().commit()
            flash("Settings saved.")
        except (ValueError, __import__("sqlite3").IntegrityError) as e:
            db().rollback()
            flash(str(e))
        return redirect(url_for("admin.operations"))
    return render_template(
        "admin_operations.html",
        numbers=db().execute("SELECT * FROM whatsapp_numbers").fetchall(),
        areas=db().execute("SELECT * FROM delivery_areas").fetchall(),
        slots=db().execute("SELECT * FROM schedule_slots").fetchall(),
    )


@bp.get("/orders/<int:oid>/notify/<status>")
@protected
def notify(oid, status):
    from urllib.parse import quote

    order = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not order or status not in STATUSES[2:-1] or order["phone"] == "[removed]":
        abort(404)
    phone = re.sub(r"\D", "", order["phone"])
    if len(phone) == 8:
        phone = "961" + phone.lstrip("0")
    message = f"Café LUX — {order['reference']}\nHello {order['name']}, your order status: {status}."
    return redirect("https://wa.me/" + phone + "?text=" + quote(message, safe=""))


@bp.get("/orders/<int:oid>")
@protected
def order_detail(oid):
    order = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not order:
        abort(404)
    row = dict(
        order,
        lines=json.loads(order["items"]),
        history=db()
        .execute("SELECT * FROM order_history WHERE order_id=? ORDER BY id", (oid,))
        .fetchall(),
    )
    return render_template("admin_order_detail.html", o=row, statuses=STATUSES)


@bp.post("/catalog-preview/prepare")
@protected
def prepare_catalog_assets():
    from .catalog_preview import prepare_catalog_preview

    try:
        result = prepare_catalog_preview()
        flash(
            f"Catalog ready: {result['images']} sample images added; {result['descriptions']} missing descriptions filled. Your existing content, prices and publication settings were preserved."
        )
    except (ValueError, OSError) as error:
        flash(str(error))
    return redirect(url_for("admin.catalog_preview"))


@bp.get("/catalog-preview")
@protected
def catalog_preview():
    from .catalog_preview import starter_descriptions, sample_source

    kind = request.args.get("kind", "drink")
    if kind not in ("drink", "ground"):
        abort(404)
    descriptions = starter_descriptions()
    rows = (
        db()
        .execute(
            """SELECT p.*,c.name category,
        (SELECT min(price) FROM variants WHERE product_id=p.id AND active=1) starting_price,
        (SELECT count(*) FROM variants WHERE product_id=p.id) variant_count
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.starter_key LIKE 'starter.v21.product.%' AND p.kind=?
        ORDER BY c.position,p.position,p.id""",
            (kind,),
        )
        .fetchall()
    )
    products = []
    for p in rows:
        item = dict(p)
        item["description"] = p["description"] or descriptions.get(p["starter_key"], "")
        source = sample_source(p["starter_key"])
        item["preview_asset"] = (
            "images/starter-samples/" + source.name
            if source
            else "images/" + p["kind"] + ".jpg"
        )
        item["sample_image"] = not p["image"] or p["image"].startswith(
            "starter-sample-"
        )
        products.append(item)
    return render_template("catalog_preview.html", products=products, kind=kind)


@bp.post("/catalog-preview/publish")
@protected
def publish_starter_samples():
    from .catalog_test_data import prepare_and_publish_starters

    try:
        result = prepare_and_publish_starters()
        flash(
            f"Published {result['published']} starter products to the customer website. Added {result['images']} missing images, {result['descriptions']} descriptions and {result['prices']} editable sample prices. Existing prices and content were kept."
        )
        for issue in result["skipped"]:
            flash(issue)
    except (ValueError, OSError) as error:
        flash(str(error))
    return redirect("/drinks")
