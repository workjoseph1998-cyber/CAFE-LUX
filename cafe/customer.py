"""Optional customer identity. Guest orders are never linked by phone."""

import json
import re
import secrets
import time
from functools import wraps
from flask import (
    Blueprint,
    request,
    session,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import db

bp = Blueprint("customer", __name__)
DUMMY = generate_password_hash("not-a-customer-password")


def current_customer():
    row = (
        db()
        .execute(
            "SELECT * FROM customers WHERE id=? AND active=1",
            (session.get("customer_id"),),
        )
        .fetchone()
    )
    if (
        row
        and row["session_version"] == session.get("customer_version")
        and time.time() - session.get("customer_time", 0) < 86400
    ):
        return row
    return None


def required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_customer():
            return redirect(url_for("customer.login"))
        return fn(*args, **kwargs)

    return wrapped


def throttle(scope):
    key = scope + ":" + (request.remote_addr or "unknown")
    now = time.time()
    conn = db()
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute("SELECT * FROM customer_limits WHERE key=?", (key,)).fetchone()
    count = row["attempts"] if row and now - row["started"] < 900 else 0
    if count >= 10:
        conn.rollback()
        abort(429)
    conn.execute(
        "INSERT OR REPLACE INTO customer_limits VALUES(?,?,?)",
        (key, count + 1, row["started"] if count else now),
    )
    conn.commit()


def recovery_codes(cid):
    codes = [secrets.token_hex(12) for _ in range(3)]
    db().execute("DELETE FROM customer_recovery WHERE customer_id=?", (cid,))
    db().executemany(
        "INSERT INTO customer_recovery(customer_id,hash) VALUES(?,?)",
        [(cid, generate_password_hash(c)) for c in codes],
    )
    return codes


def sign_in(row):
    session["customer_id"] = row["id"]
    session["customer_version"] = row["session_version"]
    session["customer_time"] = time.time()
    session["lang"] = row["language"]
    session["csrf"] = secrets.token_urlsafe(32)
    for pid in session.pop("favorites", [])[:100]:
        db().execute("INSERT OR IGNORE INTO favorites VALUES(?,?)", (row["id"], pid))
    db().commit()


@bp.route("/account/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        throttle("register")
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if (
            not re.fullmatch(r"[a-z0-9_.-]{3,60}", username)
            or not 12 <= len(password) <= 128
        ):
            flash(
                "Use a username of 3–60 letters/numbers and a password of 12–128 characters."
            )
        else:
            conn = db()
            try:
                cid = conn.execute(
                    "INSERT INTO customers(username,password) VALUES(?,?)",
                    (username, generate_password_hash(password)),
                ).lastrowid
                codes = recovery_codes(cid)
                conn.commit()
                sign_in(
                    conn.execute(
                        "SELECT * FROM customers WHERE id=?", (cid,)
                    ).fetchone()
                )
                return render_template("account.html", mode="codes", codes=codes)
            except __import__("sqlite3").IntegrityError:
                conn.rollback()
                flash(
                    "Unable to create this account. Choose another username or sign in."
                )
    return render_template("account.html", mode="register")


@bp.route("/account/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        throttle("login")
        row = (
            db()
            .execute(
                "SELECT * FROM customers WHERE username=? COLLATE NOCASE AND active=1",
                (request.form.get("username", "")[:60],),
            )
            .fetchone()
        )
        good = check_password_hash(
            row["password"] if row else DUMMY, request.form.get("password", "")[:128]
        )
        if good and row:
            sign_in(row)
            return redirect(url_for("customer.account"))
        flash("Unable to sign in with these details.")
    return render_template("account.html", mode="login")


@bp.route("/account/recover", methods=["GET", "POST"])
def recover():
    if request.method == "POST":
        throttle("recovery")
        conn = db()
        row = conn.execute(
            "SELECT * FROM customers WHERE username=? COLLATE NOCASE AND active=1",
            (request.form.get("username", "")[:60],),
        ).fetchone()
        codes = conn.execute(
            "SELECT * FROM customer_recovery WHERE customer_id=? AND used=0",
            (row["id"] if row else -1,),
        ).fetchall()
        matches = []
        supplied = request.form.get("recovery", "")[:128]
        # Equal hash work for unknown accounts and partly consumed code sets.
        for index in range(3):
            code = codes[index] if index < len(codes) else None
            good = check_password_hash(code["hash"] if code else DUMMY, supplied)
            if code and good:
                matches.append(code)
        password = request.form.get("password", "")
        if matches and 12 <= len(password) <= 128:
            conn.execute("BEGIN IMMEDIATE")
            used = conn.execute(
                "UPDATE customer_recovery SET used=1 WHERE id=? AND used=0",
                (matches[0]["id"],),
            ).rowcount
            if used:
                conn.execute(
                    "UPDATE customers SET password=?,session_version=session_version+1 WHERE id=?",
                    (generate_password_hash(password), row["id"]),
                )
            conn.commit()
            if used:
                flash("Password changed. Sign in with your new password.")
                return redirect(url_for("customer.login"))
        flash("Unable to recover this account with these details.")
    return render_template("account.html", mode="recover")


@bp.post("/account/logout")
def logout():
    for key in ("customer_id", "customer_version", "customer_time"):
        session.pop(key, None)
    session["csrf"] = secrets.token_urlsafe(32)
    return redirect("/")


@bp.route("/account", methods=["GET", "POST"])
@required
def account():
    c = current_customer()
    conn = db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "profile":
            email = request.form.get("email", "").strip()[:254]
            if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                flash("Enter a valid email address.")
                return redirect("/account")
            language = "ar" if request.form.get("language") == "ar" else "en"
            conn.execute(
                "UPDATE customers SET name=?,phone=?,email=?,language=?,preferences=? WHERE id=?",
                tuple(
                    request.form.get(k, "").strip()[:n]
                    for k, n in [("name", 100), ("phone", 25)]
                )
                + (
                    email,
                    language,
                    request.form.get("preferences", "")[:1000],
                    c["id"],
                ),
            )
            conn.commit()
            session["lang"] = language
        elif action == "address":
            area = conn.execute(
                "SELECT id FROM delivery_areas WHERE id=? AND active=1",
                (request.form.get("area"),),
            ).fetchone()
            if (
                not area
                or len(request.form.get("address", "").strip()) < 5
                or len(request.form.get("building", "").strip()) < 2
            ):
                flash("Choose an area and enter a street and building.")
            elif (
                conn.execute(
                    "SELECT count(*) FROM customer_addresses WHERE customer_id=?",
                    (c["id"],),
                ).fetchone()[0]
                < 20
            ):
                conn.execute(
                    "INSERT INTO customer_addresses(customer_id,label,area_id,address,building,floor,instructions) VALUES(?,?,?,?,?,?,?)",
                    (
                        c["id"],
                        request.form.get("label", "Home")[:60],
                        area["id"],
                        request.form["address"][:350],
                        request.form["building"][:100],
                        request.form.get("floor", "")[:50],
                        request.form.get("instructions", "")[:1000],
                    ),
                )
                conn.commit()
        elif action == "delete_address":
            conn.execute(
                "DELETE FROM customer_addresses WHERE id=? AND customer_id=?",
                (request.form.get("id"), c["id"]),
            )
            conn.commit()
        elif action == "opt_out":
            conn.execute(
                "UPDATE orders SET whatsapp_opt_in=0 WHERE customer_id=?", (c["id"],)
            )
            conn.execute(
                "UPDATE whatsapp_jobs SET state='cancelled',error='Customer opted out' WHERE order_id IN (SELECT id FROM orders WHERE customer_id=?) AND state IN ('queued','retry','blocked')",
                (c["id"],),
            )
            conn.commit()
        elif action == "codes":
            throttle("sensitive")
            if check_password_hash(
                c["password"], request.form.get("password", "")[:128]
            ):
                codes = recovery_codes(c["id"])
                conn.commit()
                return render_template("account.html", mode="codes", codes=codes)
            flash("Unable to regenerate codes.")
        return redirect("/account")
    return render_template(
        "account.html",
        mode="profile",
        customer=c,
        addresses=conn.execute(
            "SELECT * FROM customer_addresses WHERE customer_id=?", (c["id"],)
        ).fetchall(),
        areas=conn.execute("SELECT * FROM delivery_areas WHERE active=1").fetchall(),
        orders=conn.execute(
            "SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 100",
            (c["id"],),
        ).fetchall(),
    )


@bp.post("/account/reorder/<int:oid>")
@required
def reorder(oid):
    from .public import priced_cart

    order = (
        db()
        .execute(
            "SELECT * FROM orders WHERE id=? AND customer_id=?",
            (oid, current_customer()["id"]),
        )
        .fetchone()
    )
    if not order:
        abort(404)
    previous = session.get("cart", [])
    try:
        cart = []
        for line in json.loads(order["items"]):
            if line.get("bundle"):
                cart.append({"bundle": line["bundle"], "qty": line["qty"]})
            else:
                cart.append(
                    {
                        k: line.get(k, "")
                        for k in ("variant", "qty", "grind", "temperature")
                    }
                    | {"addons": [a["id"] for a in line["addons"]]}
                )
        session["cart"] = cart[:30]
        priced_cart()
        flash(
            "Your order is in the bag at current prices. Review all options and availability."
        )
    except (ValueError, KeyError):
        session["cart"] = previous
        flash("Some items or options are no longer available. Please choose again.")
    return redirect("/cart")


@bp.route("/favorites", methods=["GET"])
def favorites():
    from .public import catalog

    return render_template(
        "favorites.html", products=[p for p in catalog() if p["id"] in favorite_ids()]
    )


def favorite_ids():
    c = current_customer()
    return (
        [
            r[0]
            for r in db().execute(
                "SELECT product_id FROM favorites WHERE customer_id=?", (c["id"],)
            )
        ]
        if c
        else session.get("favorites", [])
    )


@bp.post("/favorites/<int:pid>")
def favorite(pid):
    from .public import catalog

    if pid not in {p["id"] for p in catalog()}:
        abort(404)
    c = current_customer()
    ids = favorite_ids()
    if c:
        if pid in ids:
            db().execute(
                "DELETE FROM favorites WHERE customer_id=? AND product_id=?",
                (c["id"], pid),
            )
        elif len(ids) < 100:
            db().execute("INSERT OR IGNORE INTO favorites VALUES(?,?)", (c["id"], pid))
        db().commit()
    else:
        session["favorites"] = (
            [i for i in ids if i != pid] if pid in ids else (ids + [pid])[-100:]
        )
    return redirect("/favorites")
