import json
import secrets
import re
import hashlib
import time
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo
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
    sql = "SELECT p.*, (SELECT min(v.price) FROM variants v WHERE v.product_id=p.id AND v.active=1 AND (v.stock IS NULL OR v.stock>0)) starting_price, c.name category FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.active=1 AND (c.id IS NULL OR c.active=1)"
    args = []
    if kind:
        sql += " AND p.kind=?"
        args.append(kind)
    return db().execute(sql + " ORDER BY c.position,p.position,p.id", args).fetchall()


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
        category_disabled = (
            v
            and v["category_id"]
            and db()
            .execute(
                "SELECT 1 FROM categories WHERE id=? AND active=0", (v["category_id"],)
            )
            .fetchone()
        )
        if (
            not v
            or not v["active"]
            or not v["product_active"]
            or v["price"] is None
            or category_disabled
        ):
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
                    "SELECT * FROM addons WHERE id=? AND active=1 AND price_pending=0 AND product_id=?",
                    (aid, v["product_id"]),
                )
                .fetchone()
            )
            if not a:
                raise ValueError("An add-on is unavailable. Please rebuild your cart.")
            addons.append(dict(a))
        for key, allowed in [
            ("grind", v["allowed_grinds"] or v["grinds"]),
            (
                "temperature",
                v["allowed_temperatures"]
                or ("hot,cold" if v["temperature"] == "both" else v["temperature"]),
            ),
        ]:
            if (
                (key == "grind" or v["kind"] == "drink")
                and allowed
                and item.get(key, "") not in allowed.split(",")
            ):
                raise ValueError(
                    "This combination is unavailable. Please choose product options again."
                )
        groups = [a["option_group"] for a in addons if a["option_group"]]
        if len(groups) != len(set(groups)):
            raise ValueError("Choose only one option in each extras group.")
        unit = v["price"] + sum(a["price"] for a in addons)
        lines.append(
            dict(
                variant=v["id"],
                grams=v["grams"],
                sku=v["sku"],
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
        drinks=[p for p in catalog("drink") if p["featured"]][:4],
        ground=[p for p in catalog("ground") if p["featured"]][:4],
    )


@bp.get("/drinks")
@bp.get("/coffee")
@bp.get("/shop")
def shop():
    kind = (
        "drink"
        if request.path == "/drinks"
        else "ground" if request.path == "/coffee" else request.args.get("kind") or None
    )
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
    return render_template(
        "shop.html",
        products=products,
        kind=kind,
        categories=db()
        .execute(
            "SELECT DISTINCT c.* FROM categories c JOIN products p ON p.category_id=c.id WHERE c.active=1 AND p.active=1 AND (? IS NULL OR p.kind=?) ORDER BY c.position,c.name",
            (kind, kind),
        )
        .fetchall(),
        search=search,
    )


@bp.get("/product/<int:pid>")
def product(pid):
    p = (
        db()
        .execute(
            "SELECT * FROM products WHERE id=? AND active=1 AND (category_id IS NULL OR category_id IN (SELECT id FROM categories WHERE active=1))",
            (pid,),
        )
        .fetchone()
    )
    if not p:
        abort(404)
    return render_template(
        "product.html",
        p=p,
        variants=db()
        .execute(
            "SELECT * FROM variants WHERE product_id=? AND active=1 ORDER BY position,id",
            (pid,),
        )
        .fetchall(),
        addons=db()
        .execute(
            "SELECT * FROM addons WHERE product_id=? AND active=1 AND price_pending=0",
            (pid,),
        )
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


def receiver(area=None):
    conn = db()
    if area and area["whatsapp_id"]:
        row = conn.execute(
            "SELECT * FROM whatsapp_numbers WHERE id=? AND active=1",
            (area["whatsapp_id"],),
        ).fetchone()
        if row:
            return row
    return conn.execute(
        "SELECT * FROM whatsapp_numbers WHERE active=1 AND is_default=1 ORDER BY id LIMIT 1"
    ).fetchone()


def store_open(site):
    now = datetime.now(ZoneInfo("Asia/Beirut"))
    clock = now.strftime("%H:%M")
    start, end = site["opening"], site["closing"]
    hours = start <= clock <= end if start <= end else clock >= start or clock <= end
    return (
        site["ordering"] == "1"
        and site["paused"] != "1"
        and now.strftime("%Y-%m-%d") not in site["closures"].split()
        and hours
    )


def whatsapp_message(order):
    parts = [
        "CAFÉ LUX — NEW ORDER",
        "Order: " + order["reference"],
        "Customer: " + order["name"],
        "Phone: " + order["phone"],
        "Delivery area: " + order["area"],
        "Address: " + order["address"],
        "Schedule: " + (order["requested_time"] or "As soon as available"),
        "ITEMS",
    ]
    for line in json.loads(order["items"]):
        parts.append(
            f"{line['qty']} × {line['name']} — {line['label']} "
            + line.get("grind", "")
            + " "
            + line.get("temperature", "")
            + "".join(" / " + a["name"] for a in line["addons"])
            + f"\nLine total: {order['currency']} {line['total']/100:.2f}"
        )
    parts += [
        f"Subtotal: {order['currency']} {order['subtotal']/100:.2f}",
        (
            f"Delivery: {order['delivery']/100:.2f}"
            if order["fee_known"]
            else "Delivery: To Be Confirmed"
        ),
        (
            f"Total: {order['currency']} {order['total']/100:.2f}"
            if order["fee_known"]
            else "Final total to be confirmed"
        ),
        "Payment: Cash on Delivery",
        "Notes: " + order["notes"],
    ]
    return "\n\n".join(parts)


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    site = settings()
    session.setdefault("order_token", secrets.token_urlsafe(32))
    existing = (
        db()
        .execute(
            "SELECT reference FROM orders WHERE token=?", (session["order_token"],)
        )
        .fetchone()
    )
    if request.method == "POST" and existing:
        session["last_order"] = existing["reference"]
        return redirect(url_for("public.confirmation", ref=existing["reference"]))
    if request.method == "GET" and existing:
        session["order_token"] = secrets.token_urlsafe(32)
    areas = db().execute("SELECT * FROM delivery_areas WHERE active=1").fetchall()
    slots = db().execute("SELECT * FROM schedule_slots WHERE active=1").fetchall()
    try:
        lines = priced_cart()
        if not lines:
            raise ValueError("Your bag is empty.")
        total = sum(l["total"] for l in lines)
        if request.method == "POST":
            if not secrets.compare_digest(
                request.form.get("order_token", "").encode(),
                session["order_token"].encode(),
            ):
                abort(400)
            details = {
                k: request.form.get(k, "").strip()
                for k in [
                    "name",
                    "phone",
                    "address",
                    "building",
                    "floor",
                    "notes",
                    "area",
                    "slot",
                ]
            }
            if (
                not 2 <= len(details["name"]) <= 100
                or not re.fullmatch(r"\+?[0-9 ()-]{8,25}", details["phone"])
                or not 8 <= len(re.sub(r"\D", "", details["phone"])) <= 15
            ):
                raise ValueError("Enter your full name and a valid phone number.")
            digits = re.sub(r"\D", "", details["phone"])
            if len(digits) == 8 and not details["phone"].startswith("+"):
                digits = "961" + digits.lstrip("0")
            if not re.fullmatch(r"[1-9][0-9]{7,14}", digits):
                raise ValueError(
                    "Enter a valid international or Lebanese phone number."
                )
            details["phone"] = "+" + digits
            if (
                not 5 <= len(details["address"]) <= 350
                or not 2 <= len(details["building"]) <= 100
                or len(details["floor"]) > 50
                or len(details["notes"]) > 1000
            ):
                raise ValueError("Enter your street and building or landmark details.")
            area = next((a for a in areas if str(a["id"]) == details["area"]), None)
            if not area:
                raise ValueError("Choose an available delivery area.")
            number = receiver(area)
            if not number:
                raise ValueError(
                    "WhatsApp ordering is not configured yet. Please check back soon."
                )
            slot = next((s for s in slots if str(s["id"]) == details["slot"]), None)
            if details["slot"] and (not slot or site["scheduled"] != "1"):
                raise ValueError("Choose an available schedule.")
            if (
                site["paused"] == "1"
                or site["ordering"] != "1"
                or (not store_open(site) and not slot)
            ):
                raise ValueError(
                    "We are closed for immediate orders. Choose an available scheduled slot when offered."
                )
            if total < max(area["minimum"], cents(site["minimum"])):
                raise ValueError("Your order is below the delivery area's minimum.")
            delivery = area["fee"] or 0
            review = dict(
                details,
                area_name=area["name"],
                schedule=slot["label"] if slot else "",
                delivery=delivery,
                fee_known=area["fee"] is not None,
            )
            digest = hashlib.sha256(
                json.dumps([lines, review, number["phone"]], sort_keys=True).encode()
            ).hexdigest()
            if (
                request.form.get("confirm") != "1"
                or session.get("review_digest") != digest
            ):
                session["review_digest"] = digest
                return render_template(
                    "review.html",
                    details=review,
                    lines=lines,
                    total=total,
                    order_token=session["order_token"],
                )
            conn = db()
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    "SELECT reference FROM orders WHERE token=?",
                    (session["order_token"],),
                ).fetchone()
                if existing:
                    conn.rollback()
                    session["last_order"] = existing["reference"]
                    session["cart"] = []
                    return redirect(
                        url_for("public.confirmation", ref=existing["reference"])
                    )
                ip = request.remote_addr or "unknown"
                now = time.time()
                limit = conn.execute(
                    "SELECT * FROM checkout_limits WHERE ip=?", (ip,)
                ).fetchone()
                attempts = (
                    limit["attempts"] if limit and now - limit["started"] < 600 else 0
                )
                if attempts >= 20:
                    raise ValueError(
                        "Too many submissions. Please try again in a few minutes."
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO checkout_limits VALUES (?,?,?)",
                    (ip, attempts + 1, limit["started"] if attempts else now),
                )
                lines = priced_cart()
                if (
                    hashlib.sha256(
                        json.dumps(
                            [lines, review, number["phone"]], sort_keys=True
                        ).encode()
                    ).hexdigest()
                    != digest
                ):
                    raise ValueError("Prices changed. Review your order again.")
                counts = {}
                for line in lines:
                    counts[line["variant"]] = (
                        counts.get(line["variant"], 0) + line["qty"]
                    )
                for vid, qty in counts.items():
                    stock = conn.execute(
                        "SELECT stock FROM variants WHERE id=?", (vid,)
                    ).fetchone()[0]
                    if stock is not None and stock < qty:
                        raise ValueError("Insufficient stock. Update your cart.")
                total = sum(l["total"] for l in lines)
                ref = "LUX-" + secrets.token_hex(6).upper()
                conn.execute(
                    "INSERT INTO orders(reference,token,status,name,phone,address,notes,requested_time,fulfillment,currency,subtotal,delivery,total,items,receiving_phone,area,fee_known,stock_deducted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                    (
                        ref,
                        session["order_token"],
                        "Pending WhatsApp Submission",
                        details["name"],
                        details["phone"],
                        " / ".join(
                            filter(
                                None,
                                [
                                    details["address"],
                                    details["building"],
                                    details["floor"],
                                ],
                            )
                        ),
                        details["notes"],
                        review["schedule"],
                        "delivery",
                        site["currency"],
                        total,
                        delivery,
                        total + delivery,
                        json.dumps(lines),
                        number["phone"],
                        area["name"],
                        int(review["fee_known"]),
                    ),
                )
                oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute(
                    "INSERT INTO order_history(order_id,status,username) VALUES (?,?,?)",
                    (oid, "Pending WhatsApp Submission", "Customer"),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            session["last_order"] = ref
            session["cart"] = []
            return redirect(url_for("public.confirmation", ref=ref))
        return render_template(
            "checkout.html",
            lines=lines,
            total=total,
            order_token=session["order_token"],
            areas=areas,
            slots=slots,
            available=bool(receiver()),
            is_open=store_open(site),
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
    link = (
        "https://wa.me/"
        + order["receiving_phone"].lstrip("+")
        + "?text="
        + quote(whatsapp_message(order), safe="")
        if order["receiving_phone"]
        else ""
    )
    return render_template(
        "confirmation.html",
        order=order,
        items=json.loads(order["items"]),
        whatsapp_link=link,
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
