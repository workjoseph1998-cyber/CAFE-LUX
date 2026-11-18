"""V4 administration: persistent operations and read-only business reports."""

import json
import re
import time
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, flash, session, abort
from .admin import protected
from .db import db, settings, audit, DEFAULTS
from .public import integer, cents
from .commerce import movement

bp = Blueprint("workspace", __name__, url_prefix="/admin")
WEBSITE_KEYS = {
    "headline",
    "headline_ar",
    "slogan",
    "slogan_ar",
    "description",
    "description_ar",
    "about",
    "about_ar",
    "banner",
    "banner_ar",
    "hero_eyebrow",
    "hero_eyebrow_ar",
    "story_title",
    "story_title_ar",
    "hero_image",
    "story_image",
    "choice_drink_image",
    "choice_coffee_image",
    "home_sections",
    "show_drinks",
    "show_ground",
    "show_story",
    "show_choices",
    "show_how",
    "drinks_title",
    "coffee_title",
    "choices_title",
    "how_title",
    "footer",
}


def view(title, **kw):
    return render_template("admin_v4.html", title=title, **kw)


@bp.route("/inventory", methods=["GET", "POST"])
@protected
def inventory():
    if request.method == "POST":
        conn = db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            vid = integer(request.form.get("id"), 1)
            v = conn.execute("SELECT * FROM variants WHERE id=?", (vid,)).fetchone()
            if not v:
                abort(404)
            reason = request.form.get("reason", "").strip()[:300]
            if not reason:
                raise ValueError("Record a reason for this inventory change.")
            value = request.form.get("stock", "").strip()
            stock = integer(value) if value else None
            threshold = integer(request.form.get("low_threshold", "5"))
            cost = (
                cents(request.form["unit_cost"])
                if request.form.get("unit_cost", "").strip()
                else None
            )
            restock = request.form.get("restock_date", "")
            if restock:
                datetime.strptime(restock, "%Y-%m-%d")
            conn.execute(
                "UPDATE variants SET stock=?,low_threshold=?,unit_cost=?,restock_notes=?,restock_date=? WHERE id=?",
                (
                    stock,
                    threshold,
                    cost,
                    request.form.get("restock_notes", "")[:500],
                    restock,
                    vid,
                ),
            )
            movement(vid, v["stock"], stock, reason, actor=session["username"])
            audit("Inventory adjustment variant " + str(vid) + ": " + reason)
            conn.commit()
        except ValueError as e:
            conn.rollback()
            flash(str(e))
        return redirect("/admin/inventory")
    return view(
        "Inventory",
        variants=db()
        .execute(
            "SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id ORDER BY p.name,v.position,v.id"
        )
        .fetchall(),
        movements=db()
        .execute(
            "SELECT m.*,p.name,v.label FROM inventory_movements m JOIN variants v ON v.id=m.variant_id JOIN products p ON p.id=v.product_id ORDER BY m.id DESC LIMIT 200"
        )
        .fetchall(),
    )


@bp.route("/promotions", methods=["GET", "POST"])
@protected
def promotions():
    if request.method == "POST":
        try:
            code = request.form.get("code", "").strip().upper()
            if not re.fullmatch(r"[A-Z0-9_-]{2,40}", code):
                raise ValueError(
                    "Use a promotion code of 2–40 letters, numbers, underscores or hyphens."
                )
            kind = request.form.get("kind")
            if kind not in ("percent", "fixed"):
                raise ValueError("Choose a promotion type.")
            value = (
                integer(request.form.get("value"), 1, 100)
                if kind == "percent"
                else cents(request.form.get("value"))
            )
            if value <= 0:
                raise ValueError("Discount must be greater than zero.")
            dates = []
            for key in ("starts", "ends"):
                d = request.form.get(key, "").strip()
                dates.append(
                    datetime.fromisoformat(d).strftime("%Y-%m-%d %H:%M:%S") if d else ""
                )
            if all(dates) and dates[0] >= dates[1]:
                raise ValueError("Promotion end must follow start (UTC).")
            fields = (
                code,
                kind,
                value,
                cents(request.form.get("minimum", "0")),
                (
                    cents(request.form["maximum_discount"])
                    if request.form.get("maximum_discount")
                    else None
                ),
                *dates,
                (
                    integer(request.form["usage_limit"], 1)
                    if request.form.get("usage_limit")
                    else None
                ),
                int(request.form.get("active") == "1"),
            )
            pid = request.form.get("id")
            if pid:
                db().execute(
                    "UPDATE promotions SET code=?,kind=?,value=?,minimum=?,maximum_discount=?,starts=?,ends=?,usage_limit=?,active=? WHERE id=?",
                    fields + (integer(pid, 1),),
                )
            else:
                db().execute(
                    "INSERT INTO promotions(code,kind,value,minimum,maximum_discount,starts,ends,usage_limit,active) VALUES(?,?,?,?,?,?,?,?,?)",
                    fields,
                )
            audit("Saved promotion " + code)
            db().commit()
        except (ValueError, __import__("sqlite3").IntegrityError) as e:
            db().rollback()
            flash(
                str(e)
                if isinstance(e, ValueError)
                else "This promotion code already exists."
            )
        return redirect("/admin/promotions")
    return view(
        "Promotions",
        promotions=db().execute("SELECT * FROM promotions ORDER BY id DESC").fetchall(),
    )


@bp.route("/bundles", methods=["GET", "POST"])
@protected
def bundles():
    if request.method == "POST":
        conn = db()
        try:
            name = request.form.get("name", "").strip()[:150]
            if not name:
                raise ValueError("Enter a bundle name.")
            raw = json.loads(request.form.get("components", "[]"))
            if not isinstance(raw, list) or not 1 <= len(raw) <= 12:
                raise ValueError("A bundle needs 1–12 components.")
            components = []
            from .public import price_single

            for c in raw:
                item = {
                    "variant": integer(c.get("variant"), 1),
                    "qty": integer(c.get("qty", 1), 1, 20),
                    "grind": str(c.get("grind", ""))[:100],
                    "temperature": str(c.get("temperature", ""))[:30],
                    "addons": [integer(a, 1) for a in c.get("addons", [])],
                }
                if len(set(item["addons"])) != len(item["addons"]):
                    raise ValueError("Duplicate bundle extras.")
                price_single(item)
                components.append(item)
            fields = (
                name,
                request.form.get("name_ar", "")[:150],
                request.form.get("description", "")[:3000],
                request.form.get("description_ar", "")[:3000],
                cents(request.form.get("price")),
                int(request.form.get("active") == "1"),
            )
            conn.execute("BEGIN IMMEDIATE")
            bid = integer(request.form["id"], 1) if request.form.get("id") else None
            if bid:
                conn.execute(
                    "UPDATE bundles SET name=?,name_ar=?,description=?,description_ar=?,price=?,active=? WHERE id=?",
                    fields + (bid,),
                )
                conn.execute("DELETE FROM bundle_items WHERE bundle_id=?", (bid,))
            else:
                bid = conn.execute(
                    "INSERT INTO bundles(name,name_ar,description,description_ar,price,active) VALUES(?,?,?,?,?,?)",
                    fields,
                ).lastrowid
            conn.executemany(
                "INSERT INTO bundle_items(bundle_id,variant_id,qty,grind,temperature,addons) VALUES(?,?,?,?,?,?)",
                [
                    (
                        bid,
                        c["variant"],
                        c["qty"],
                        c["grind"],
                        c["temperature"],
                        json.dumps(c["addons"]),
                    )
                    for c in components
                ],
            )
            audit("Saved bundle " + name)
            conn.commit()
        except (ValueError, TypeError, KeyError) as e:
            conn.rollback()
            flash(str(e))
        return redirect("/admin/bundles")
    bundles = []
    for b in db().execute("SELECT * FROM bundles ORDER BY id"):
        record = dict(b)
        record["components"] = json.dumps(
            [
                {
                    "variant": r["variant_id"],
                    "qty": r["qty"],
                    "grind": r["grind"],
                    "temperature": r["temperature"],
                    "addons": json.loads(r["addons"]),
                }
                for r in db().execute(
                    "SELECT * FROM bundle_items WHERE bundle_id=?", (b["id"],)
                )
            ]
        )
        bundles.append(record)
    return view(
        "Bundles",
        bundles=bundles,
        variants=db()
        .execute(
            "SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id ORDER BY p.name"
        )
        .fetchall(),
    )


@bp.get("/customers")
@protected
def customers():
    return view(
        "Customers",
        customers=db()
        .execute(
            "SELECT c.id,c.username,c.name,c.phone,c.created,c.active,count(o.id) orders FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.id DESC LIMIT 200"
        )
        .fetchall(),
        guest_orders=db()
        .execute("SELECT count(*) FROM orders WHERE customer_id IS NULL")
        .fetchone()[0],
    )


@bp.get("/reports")
@protected
def reports():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    for d in (start, end):
        if d:
            try:
                datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                abort(400)
    currency = request.args.get("currency", settings()["currency"])[:10]
    rows = (
        db()
        .execute(
            "SELECT * FROM orders WHERE currency=? AND (?='' OR date(created)>=?) AND (?='' OR date(created)<=?) ORDER BY created",
            (currency, start, start, end, end),
        )
        .fetchall()
    )
    delivered = [o for o in rows if o["status"] == "Delivered"]
    groups = {key: {} for key in ("day", "month", "product", "type", "area", "status")}
    costs = 0
    units = {}
    reliable = bool(delivered)
    for o in rows:
        groups["status"][o["status"]] = groups["status"].get(o["status"], 0) + 1
    for o in delivered:
        for key, value in [
            ("day", o["created"][:10]),
            ("month", o["created"][:7]),
            ("area", o["area"] or "Unspecified"),
        ]:
            groups[key][value] = groups[key].get(value, 0) + o["subtotal"]
        for line in json.loads(o["items"]):
            for c in line.get("components", [line]):
                entry = units.setdefault(
                    c["product"], {"name": c["name"], "qty": 0, "total": 0}
                )
                entry["qty"] += c["qty"]
                entry["total"] += c["total"]
                name = c["name"]
                groups["product"][name] = groups["product"].get(name, 0) + c["total"]
                groups["type"][c["kind"]] = (
                    groups["type"].get(c["kind"], 0) + c["total"]
                )
                if c.get("unit_cost") is None:
                    reliable = False
                else:
                    costs += c["unit_cost"] * c["qty"]
    gross = sum(o["subtotal"] for o in delivered)
    discounts = sum(o["discount"] for o in delivered)
    return view(
        "Reports",
        bestselling=sorted(units.values(), key=lambda x: x["qty"], reverse=True),
        inventory_report=db()
        .execute(
            "SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id ORDER BY p.name,v.position,v.id"
        )
        .fetchall(),
        currency=currency,
        currencies=[
            r[0]
            for r in db().execute(
                "SELECT DISTINCT currency FROM orders UNION SELECT value FROM settings WHERE key='currency'"
            )
        ],
        groups=groups,
        gross=gross,
        discounts=discounts,
        profit=gross - discounts - costs if reliable else None,
        low=db()
        .execute(
            "SELECT count(*) FROM variants WHERE active=1 AND stock IS NOT NULL AND stock<=low_threshold"
        )
        .fetchone()[0],
        start=start,
        end=end,
    )


@bp.route("/website", methods=["GET", "POST"])
@protected
def website():
    conn = db()
    if request.method == "POST":
        try:
            payload = {k: request.form.get(k, "").strip()[:5000] for k in WEBSITE_KEYS}
            allowed = {
                "choices",
                "drinks",
                "ground",
                "bestsellers",
                "bundles",
                "story",
                "how",
            }
            sections = payload["home_sections"].split(",")
            if len(sections) != len(set(sections)) or not set(sections) <= allowed:
                raise ValueError("Use each supported homepage section at most once.")
            for key in (
                "hero_image",
                "story_image",
                "choice_drink_image",
                "choice_coffee_image",
            ):
                if (
                    payload[key]
                    and not conn.execute(
                        "SELECT 1 FROM media WHERE filename=?", (payload[key],)
                    ).fetchone()
                ):
                    raise ValueError("Choose registered media for " + key)
            conn.execute(
                "INSERT OR REPLACE INTO website_drafts(id,payload,actor) VALUES(1,?,?)",
                (json.dumps(payload), session["username"]),
            )
            if request.form.get("action") == "publish":
                conn.executemany(
                    "INSERT OR REPLACE INTO settings VALUES(?,?)", list(payload.items())
                )
                audit("Published website draft")
            else:
                audit("Saved website draft")
            conn.commit()
            flash(
                "Published."
                if request.form.get("action") == "publish"
                else "Draft saved. The public website has not changed."
            )
        except ValueError as e:
            conn.rollback()
            flash(str(e))
        return redirect("/admin/website")
    draft = conn.execute("SELECT * FROM website_drafts WHERE id=1").fetchone()
    values = json.loads(draft["payload"]) if draft else settings()
    return view(
        "Website Manager",
        values=values,
        keys=sorted(WEBSITE_KEYS),
        media=conn.execute("SELECT * FROM media ORDER BY id DESC").fetchall(),
    )


@bp.get("/website/preview")
@protected
def website_preview():
    from .public import catalog, bestsellers

    draft = db().execute("SELECT * FROM website_drafts WHERE id=1").fetchone()
    site = settings() | (json.loads(draft["payload"]) if draft else {})
    return render_template(
        "home.html",
        site=site,
        preview=True,
        drinks=[p for p in catalog("drink") if p["featured"]][:4],
        ground=[p for p in catalog("ground") if p["featured"]][:4],
        bestsellers=bestsellers(),
        bundles=db().execute("SELECT * FROM bundles WHERE active=1").fetchall(),
    )


@bp.route("/whatsapp", methods=["GET", "POST"])
@protected
def whatsapp():
    from .whatsapp import health, graph, DeliveryError

    conn = db()
    if request.method == "POST":
        try:
            action = request.form.get("action")
            if action == "settings":
                for key in (
                    "wa_confirmed_en",
                    "wa_confirmed_ar",
                    "wa_out_en",
                    "wa_out_ar",
                ):
                    value = request.form.get(key, "").strip()
                    if value and not re.fullmatch("[a-z0-9_]{1,512}", value):
                        raise ValueError(
                            "Template names must match Meta template names."
                        )
                    conn.execute(
                        "INSERT OR REPLACE INTO settings VALUES(?,?)", (key, value)
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO settings VALUES('wa_automation',?)",
                    ("1" if request.form.get("wa_automation") == "1" else "0",),
                )
                for n in conn.execute("SELECT id FROM whatsapp_numbers"):
                    value = request.form.get("phone_" + str(n["id"]), "").strip()
                    if value and not re.fullmatch("[0-9]+", value):
                        raise ValueError("Cloud phone IDs contain digits only.")
                    conn.execute(
                        "UPDATE whatsapp_numbers SET cloud_phone_id=? WHERE id=?",
                        (value, n["id"]),
                    )
                audit("Updated WhatsApp automation configuration")
                conn.commit()
            elif action == "connection":
                import os

                phone = os.environ.get("META_PHONE_NUMBER_ID", "")
                waba = os.environ.get("META_WABA_ID", "")
                if not phone.isdigit() or not waba.isdigit():
                    raise ValueError("Configure META_PHONE_NUMBER_ID and META_WABA_ID.")
                identity = graph(
                    phone + "?fields=id,display_phone_number,verified_name"
                )
                templates = graph(
                    waba + "/message_templates?fields=name,status,language&limit=100"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO settings VALUES('wa_health_checked',?)",
                    (str(time.time()),),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO settings VALUES('wa_template_health',?)",
                    (
                        json.dumps(
                            [
                                {
                                    "name": t.get("name"),
                                    "status": t.get("status"),
                                    "language": t.get("language"),
                                }
                                for t in templates.get("data", [])
                            ]
                        ),
                    ),
                )
                conn.commit()
                flash(
                    "Meta connection succeeded. Template statuses below are actual provider responses (first 100 templates)."
                )
            elif action == "retry":
                job = conn.execute(
                    "SELECT * FROM whatsapp_jobs WHERE id=?", (request.form.get("id"),)
                ).fetchone()
                if not job or job["state"] not in ("blocked", "failed", "uncertain"):
                    raise ValueError("This job cannot be retried.")
                if (
                    job["state"] == "uncertain"
                    and request.form.get("reconciled") != "1"
                ):
                    raise ValueError(
                        "Reconcile uncertain delivery in Meta before acknowledging duplicate risk and retrying."
                    )
                import secrets

                conn.execute("BEGIN IMMEDIATE")
                # Preserve the prior attempt identity: late callbacks must not
                # describe a newly retried send as delivered.
                fresh = conn.execute(
                    "SELECT * FROM whatsapp_jobs WHERE id=?", (job["id"],)
                ).fetchone()
                if fresh["state"] != job["state"]:
                    raise ValueError("Job changed. Reload before retrying.")
                conn.execute(
                    "INSERT INTO whatsapp_attempts(job_id,attempt_key,message_id,state,error) VALUES(?,?,?,?,?)",
                    (
                        job["id"],
                        job["job_key"],
                        job["message_id"],
                        job["state"],
                        job["error"],
                    ),
                )
                conn.execute(
                    "UPDATE whatsapp_jobs SET job_key=?,state='queued',due=0,request_started=0,error='',attempts=0,message_id=NULL WHERE id=?",
                    (secrets.token_hex(16), job["id"]),
                )
                audit("Manually retried WhatsApp job " + str(job["id"]))
                conn.commit()
            elif action == "match":
                incoming = conn.execute(
                    "SELECT * FROM whatsapp_incoming WHERE id=? AND state='manual_review'",
                    (request.form.get("id"),),
                ).fetchone()
                order = conn.execute(
                    "SELECT * FROM orders WHERE reference=?",
                    (request.form.get("reference", "").upper(),),
                ).fetchone()
                reason = request.form.get("reason", "").strip()[:300]
                if not incoming or not order or not reason:
                    raise ValueError(
                        "Choose an incoming message and order, and record your verification reason."
                    )
                conn.execute(
                    "UPDATE whatsapp_incoming SET order_id=?,state='staff_matched' WHERE id=?",
                    (order["id"], incoming["id"]),
                )
                if order["status"] == "Pending WhatsApp Submission":
                    conn.execute(
                        "UPDATE orders SET status='Received',incoming_message_id=? WHERE id=?",
                        (incoming["message_id"], order["id"]),
                    )
                    conn.execute(
                        "INSERT INTO order_history(order_id,status,username) VALUES(?,?,?)",
                        (order["id"], "Received", session["username"]),
                    )
                audit(
                    "Manually matched incoming "
                    + str(incoming["id"])
                    + " to "
                    + order["reference"]
                    + ": "
                    + reason
                )
                conn.commit()
        except (ValueError, DeliveryError) as e:
            conn.rollback()
            flash(e.code if isinstance(e, DeliveryError) else str(e))
        return redirect("/admin/whatsapp")
    return view(
        "WhatsApp Automation",
        health=health(),
        numbers=conn.execute("SELECT * FROM whatsapp_numbers").fetchall(),
        attempts=conn.execute(
            "SELECT a.*,o.reference,j.kind FROM whatsapp_attempts a JOIN whatsapp_jobs j ON j.id=a.job_id JOIN orders o ON o.id=j.order_id ORDER BY a.id DESC LIMIT 200"
        ).fetchall(),
        jobs=conn.execute(
            "SELECT j.*,o.reference FROM whatsapp_jobs j JOIN orders o ON o.id=j.order_id ORDER BY j.id DESC LIMIT 200"
        ).fetchall(),
        incoming=conn.execute(
            "SELECT * FROM whatsapp_incoming ORDER BY id DESC LIMIT 100"
        ).fetchall(),
        template_health=json.loads(settings().get("wa_template_health", "[]")),
    )


@bp.post("/orders/<int:oid>/note")
@protected
def note(oid):
    if not db().execute("SELECT 1 FROM orders WHERE id=?", (oid,)).fetchone():
        abort(404)
    note = request.form.get("note", "").strip()[:2000]
    if note:
        db().execute(
            "INSERT INTO order_notes(order_id,actor,note) VALUES(?,?,?)",
            (oid, session["username"], note),
        )
        audit("Added internal note to order " + str(oid))
        db().commit()
    return redirect("/admin/orders/" + str(oid))


@bp.route("/customers/<int:cid>", methods=["GET", "POST"])
@protected
def customer_detail(cid):
    conn = db()
    c = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    if not c:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "access":
            conn.execute(
                "UPDATE customers SET active=?,session_version=session_version+1 WHERE id=?",
                (int(request.form.get("active") == "1"), cid),
            )
            audit("Changed customer account access #" + str(cid))
        elif action == "remove_address":
            conn.execute(
                "DELETE FROM customer_addresses WHERE id=? AND customer_id=?",
                (request.form.get("id"), cid),
            )
            audit("Removed customer address for account #" + str(cid))
        elif action == "erase":
            conn.execute(
                "UPDATE customers SET name='',phone='',email='',preferences='',active=0,password='',session_version=session_version+1 WHERE id=?",
                (cid,),
            )
            conn.execute("DELETE FROM customer_addresses WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM favorites WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM customer_recovery WHERE customer_id=?", (cid,))
            conn.execute(
                "UPDATE orders SET name='[removed]',phone='[removed]',address='',notes='',whatsapp_opt_in=0 WHERE customer_id=? AND status IN ('Delivered','Cancelled')",
                (cid,),
            )
            audit(
                "Removed profile and closed-order personal data for account #"
                + str(cid)
            )
        conn.commit()
        return redirect("/admin/customers/" + str(cid))
    return render_template(
        "admin_customer.html",
        customer=c,
        addresses=conn.execute(
            "SELECT a.*,d.name area FROM customer_addresses a LEFT JOIN delivery_areas d ON d.id=a.area_id WHERE customer_id=?",
            (cid,),
        ).fetchall(),
        orders=conn.execute(
            "SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 200",
            (cid,),
        ).fetchall(),
    )
