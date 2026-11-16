import json
import secrets
import os
from decimal import Decimal, InvalidOperation
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    abort,
    flash,
    send_from_directory,
    current_app,
)
from .db import db, settings

bp = Blueprint("public", __name__)


def cents(value):
    try:
        amount = Decimal(str(value))
        if (
            not amount.is_finite()
            or amount < 0
            or amount > 1000000
            or amount.as_tuple().exponent < -2
        ):
            raise ValueError()
        return int(amount * 100)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a valid price with at most two decimal places.")


def integer(value, minimum=0, maximum=100000000):
    try:
        n = int(value)
    except (ValueError, TypeError):
        raise ValueError("Enter a valid whole number.")
    if not minimum <= n <= maximum:
        raise ValueError("Number is outside the allowed range.")
    return n


def catalog(kind=None):
    sql = """SELECT p.*, c.name category, c.name_ar category_ar,
        (SELECT min(v.price) FROM variants v WHERE v.product_id=p.id AND v.active=1) starting_price,
        (SELECT max(v.price) FROM variants v WHERE v.product_id=p.id AND v.active=1) highest_price
        FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.active=1"""
    args = []
    if kind:
        sql += " AND p.kind=?"
        args.append(kind)
    rows = db().execute(sql + " ORDER BY p.position,p.id", args).fetchall()
    options = {}
    for v in db().execute("SELECT * FROM variants WHERE active=1 ORDER BY id"):
        options.setdefault(v["product_id"], []).append(dict(v))
    result = []
    for row in rows:
        item = dict(row)
        item["display_variants"] = options.get(row["id"], [])
        result.append(item)
    return result


def priced_cart():
    lines = []
    for item in session.get("cart", []):
        v = (
            db()
            .execute(
                "SELECT v.*,p.name,p.name_ar,p.kind,p.grinds,p.temperature,p.category_id,(SELECT c.name FROM categories c WHERE c.id=p.category_id) category_name,p.active product_active FROM variants v JOIN products p ON p.id=v.product_id WHERE v.id=?",
                (item["variant"],),
            )
            .fetchone()
        )
        if not v or not v["active"] or not v["product_active"] or v["price"] is None:
            raise ValueError(
                "An item is unavailable. Clear your cart and choose again."
            )
        if v["stock"] is not None and v["stock"] < item["qty"]:
            raise ValueError("Insufficient stock for " + v["name"])
        addons = []
        for aid in item["addons"]:
            a = (
                db()
                .execute(
                    "SELECT * FROM addons WHERE id=? AND active=1 AND product_id=?",
                    (aid, v["product_id"]),
                )
                .fetchone()
            )
            if not a:
                raise ValueError("An add-on is unavailable. Please rebuild your cart.")
            addons.append(dict(a))
        unit = v["price"] + sum(a["price"] for a in addons)
        lines.append(
            dict(
                variant=v["id"],
                product=v["product_id"],
                name=v["name"],
                name_ar=v["name_ar"],
                kind=v["kind"],
                category=v["category_id"],
                category_name=v["category_name"] or "Uncategorized",
                label=v["label"],
                label_ar=v["label_ar"],
                grind=item.get("grind", ""),
                temperature=item.get("temperature", ""),
                addons=addons,
                qty=item["qty"],
                unit=unit,
                total=unit * item["qty"],
            )
        )
    return lines


@bp.get("/")
def home():
    return render_template(
        "home.html",
        categories=menu_categories(),
        drinks=[p for p in catalog("drink") if p["featured"]][:4],
        ground=[p for p in catalog("ground") if p["featured"]][:4],
    )


@bp.get("/shop")
def shop():
    kind = request.args.get("kind") or "drink"
    if kind not in ("drink", "ground", None):
        abort(404)
    products = catalog(kind)
    category = request.args.get("category", type=int)
    if category:
        products = [p for p in products if p["category_id"] == category]
    search = request.args.get("q", "").strip()[:100]
    if search:
        products = [
            p
            for p in products
            if search.lower() in (p["name"] + " " + p["name_ar"]).lower()
        ]
    categories = menu_categories(kind)
    groups = []
    for c in categories:
        group_products = [p for p in products if p["category_id"] == c["id"]]
        if group_products:
            groups.append(
                dict(title=c["name"], title_ar=c["name_ar"], products=group_products)
            )
    uncategorized = [p for p in products if p["category_id"] is None]
    if uncategorized:
        groups.append(
            dict(title="More choices", title_ar="خيارات أخرى", products=uncategorized)
        )
    return render_template(
        "shop.html",
        groups=groups,
        selected_category=category,
        product_count=len(products),
        products=products,
        kind=kind,
        categories=db()
        .execute("SELECT * FROM categories ORDER BY position,name")
        .fetchall(),
        menu_categories=menu_categories(kind),
        search=search,
    )


@bp.get("/product/<int:pid>")
def product(pid):
    p = (
        db()
        .execute("SELECT * FROM products WHERE id=? AND active=1", (pid,))
        .fetchone()
    )
    if not p:
        abort(404)
    return render_template(
        "product.html",
        p=p,
        variants=db()
        .execute(
            "SELECT * FROM variants WHERE product_id=? AND active=1 ORDER BY id", (pid,)
        )
        .fetchall(),
        addons=db()
        .execute("SELECT * FROM addons WHERE product_id=? AND active=1", (pid,))
        .fetchall(),
        gallery=json.loads(p["gallery"]),
        related=[r for r in catalog(p["kind"]) if r["id"] != pid][:3],
    )


@bp.post("/cart/add")
def add():
    try:
        vid = integer(request.form.get("variant"), 1)
        qty = integer(request.form.get("qty"), 1, 99)
        aids = sorted(set(integer(x, 1) for x in request.form.getlist("addon")))
        if len(aids) > 20:
            raise ValueError("Too many add-ons.")
        p = (
            db()
            .execute(
                "SELECT p.* FROM products p JOIN variants v ON p.id=v.product_id WHERE v.id=?",
                (vid,),
            )
            .fetchone()
        )
        if not p:
            raise ValueError("Select an available size.")
        grind = request.form.get("grind", "")
        temp = request.form.get("temperature", "")
        if p["grinds"] and grind not in p["grinds"].split(","):
            raise ValueError("Select a grind option.")
        if p["kind"] == "drink" and temp not in (
            ["hot", "cold"] if p["temperature"] == "both" else [p["temperature"]]
        ):
            raise ValueError("Select a temperature.")
        old = session.get("cart", [])
        if len(old) >= 30:
            raise ValueError("Cart limit reached.")
        session["cart"] = old + [
            dict(variant=vid, qty=qty, addons=aids, grind=grind, temperature=temp)
        ]
        try:
            lines = priced_cart()
            counts = {}
            for line in lines:
                counts[line["variant"]] = counts.get(line["variant"], 0) + line["qty"]
            for key, count in counts.items():
                stock = (
                    db()
                    .execute("SELECT stock FROM variants WHERE id=?", (key,))
                    .fetchone()["stock"]
                )
                if stock is not None and count > stock:
                    raise ValueError("Not enough stock.")
        except ValueError:
            session["cart"] = old
            raise
        flash("Added to your bag.")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for("public.cart"))


@bp.route("/cart", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        items = session.get("cart", [])
        try:
            if "clear" in request.form:
                items = []
            else:
                idx = integer(request.form.get("index"), 0, len(items) - 1)
                qty = (
                    0
                    if "remove" in request.form
                    else integer(request.form.get("qty", "0"), 0, 99)
                )
                if qty:
                    items[idx]["qty"] = qty
                else:
                    items.pop(idx)
            session["cart"] = items
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("public.cart"))
    try:
        lines = priced_cart()
    except ValueError as e:
        flash(str(e))
        lines = []
    return render_template(
        "cart.html", lines=lines, total=sum(l["total"] for l in lines)
    )


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    site = settings()
    if "order_token" not in session:
        session["order_token"] = secrets.token_urlsafe(32)
    if request.method == "POST" and secrets.compare_digest(
        request.form.get("order_token", "").encode(), session["order_token"].encode()
    ):
        existing = (
            db()
            .execute(
                "SELECT reference FROM orders WHERE token=?", (session["order_token"],)
            )
            .fetchone()
        )
        if existing:
            session["last_order"] = existing["reference"]
            return redirect(url_for("public.confirmation", ref=existing["reference"]))
    try:
        lines = priced_cart()
        if not lines:
            raise ValueError("Your bag is empty.")
        if request.method == "POST":
            token = request.form.get("order_token", "")
            if not secrets.compare_digest(
                token.encode(), session["order_token"].encode()
            ):
                abort(400)
            existing = (
                db()
                .execute("SELECT reference FROM orders WHERE token=?", (token,))
                .fetchone()
            )
            if existing:
                return redirect(
                    url_for("public.confirmation", ref=existing["reference"])
                )
            if site["ordering"] != "1":
                raise ValueError("Ordering is currently closed.")
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            method = request.form.get("fulfillment", "")
            address = request.form.get("address", "").strip()
            notes = request.form.get("notes", "").strip()
            requested = request.form.get("requested_time", "").strip()
            if (
                not 2 <= len(name) <= 100
                or not 6 <= len(phone) <= 30
                or any(c not in "+0123456789 ()-." for c in phone)
            ):
                raise ValueError("Enter your name and a valid phone number.")
            if method not in ("pickup", "delivery") or site[method] != "1":
                raise ValueError("Select an available fulfillment method.")
            if method == "delivery" and not 10 <= len(address) <= 500:
                raise ValueError("Enter a complete delivery address.")
            if len(notes) > 1000 or len(address) > 500 or len(requested) > 80:
                raise ValueError("Text is too long.")
            if site["pickup_time"] != "1":
                requested = ""
            conn = db()
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    "SELECT reference FROM orders WHERE token=?", (token,)
                ).fetchone()
                if existing:
                    conn.rollback()
                    session["last_order"] = existing["reference"]
                    session["cart"] = []
                    return redirect(
                        url_for("public.confirmation", ref=existing["reference"])
                    )
                lines = (
                    priced_cart()
                )  # Recheck prices and inventory under the write lock.
                subtotal = sum(l["total"] for l in lines)
                if subtotal < cents(site["minimum"]):
                    raise ValueError("Your order is below the minimum.")
                delivery = cents(site["delivery_fee"]) if method == "delivery" else 0
                for l in lines:
                    changed = conn.execute(
                        "UPDATE variants SET stock=stock-? WHERE id=? AND stock IS NOT NULL AND stock>=?",
                        (l["qty"], l["variant"], l["qty"]),
                    )
                    stock = conn.execute(
                        "SELECT stock FROM variants WHERE id=?", (l["variant"],)
                    ).fetchone()["stock"]
                    if stock is not None and changed.rowcount != 1:
                        raise ValueError("Insufficient stock. Please update your bag.")
                ref = "LUX-" + secrets.token_hex(6).upper()
                conn.execute(
                    "INSERT INTO orders(reference,token,name,phone,address,notes,requested_time,fulfillment,currency,subtotal,delivery,total,items) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        ref,
                        token,
                        name,
                        phone,
                        address,
                        notes,
                        requested,
                        method,
                        site["currency"],
                        subtotal,
                        delivery,
                        subtotal + delivery,
                        json.dumps(lines),
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            session["last_order"] = ref
            session["cart"] = []
            return redirect(url_for("public.confirmation", ref=ref))
        # A new bag after a successful checkout needs its own idempotency token.
        if (
            db()
            .execute("SELECT 1 FROM orders WHERE token=?", (session["order_token"],))
            .fetchone()
        ):
            session["order_token"] = secrets.token_urlsafe(32)
        return render_template(
            "checkout.html",
            lines=lines,
            total=sum(l["total"] for l in lines),
            order_token=session["order_token"],
        )
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("public.cart"))


@bp.get("/order/<ref>")
def confirmation(ref):
    if session.get("last_order") != ref:
        abort(404)
    order = db().execute("SELECT * FROM orders WHERE reference=?", (ref,)).fetchone()
    if not order:
        abort(404)
    return render_template(
        "confirmation.html", order=order, items=json.loads(order["items"])
    )


@bp.get("/page/<name>")
def page(name):
    if name not in ("about", "location", "contact", "privacy", "terms"):
        abort(404)
    return render_template("page.html", name=name)


@bp.post("/language")
def language():
    session["lang"] = "ar" if request.form.get("lang") == "ar" else "en"
    return redirect(url_for("public.home"))


@bp.get("/media/<filename>")
def media(filename):
    if not db().execute("SELECT 1 FROM media WHERE filename=?", (filename,)).fetchone():
        abort(404)
    return send_from_directory(current_app.config["DATA_DIR"] + "/uploads", filename)


@bp.get("/healthz")
def health():
    db().execute("SELECT key FROM settings LIMIT 1").fetchone()
    return {"application": "cafe-lux", "status": "ok", "pid": os.getpid()}


def menu_categories(kind=None):
    sql = """SELECT c.*,count(p.id) product_count FROM categories c JOIN products p ON p.category_id=c.id AND p.active=1"""
    args = []
    if kind:
        sql += " WHERE p.kind=?"
        args.append(kind)
    return (
        db().execute(sql + " GROUP BY c.id ORDER BY c.position,c.name", args).fetchall()
    )
