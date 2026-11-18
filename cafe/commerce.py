"""Integer-cents promotions, bundle expansion and inventory requirements."""

import json
from datetime import datetime, timezone
from flask import session
from .db import db


def promotion(subtotal, code=None, exclude_order=None):
    code = (session.get("promotion", "") if code is None else code).strip()[:60]
    if not code:
        return None, 0
    p = (
        db()
        .execute(
            "SELECT * FROM promotions WHERE code=? COLLATE NOCASE AND active=1", (code,)
        )
        .fetchone()
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if (
        not p
        or (p["starts"] and now < p["starts"])
        or (p["ends"] and now > p["ends"])
        or subtotal < p["minimum"]
    ):
        raise ValueError(
            "This promotion is unavailable or its minimum has not been met."
        )
    used = (
        db()
        .execute(
            "SELECT count(*) FROM orders WHERE promotion_id=? AND id!=? AND status!='Cancelled' AND (status!='Pending WhatsApp Submission' OR created>datetime('now','-30 minutes'))",
            (p["id"], exclude_order or -1),
        )
        .fetchone()[0]
    )
    if p["usage_limit"] is not None and used >= p["usage_limit"]:
        raise ValueError("This promotion has reached its usage limit.")
    amount = subtotal * p["value"] // 100 if p["kind"] == "percent" else p["value"]
    if p["maximum_discount"] is not None:
        amount = min(amount, p["maximum_discount"])
    return p, min(subtotal, amount)


def requirements(lines):
    counts = {}
    for line in lines:
        for component in line.get("components", [line]):
            counts[component["variant"]] = (
                counts.get(component["variant"], 0) + component["qty"]
            )
    return counts


def ensure_stock(lines):
    for vid, qty in requirements(lines).items():
        row = db().execute("SELECT stock FROM variants WHERE id=?", (vid,)).fetchone()
        if not row or (row["stock"] is not None and row["stock"] < qty):
            raise ValueError("Insufficient stock. Review your bag.")


def bundle_line(item, price_single):
    b = (
        db()
        .execute("SELECT * FROM bundles WHERE id=? AND active=1", (item["bundle"],))
        .fetchone()
    )
    rows = (
        db()
        .execute(
            "SELECT * FROM bundle_items WHERE bundle_id=? ORDER BY id",
            (item["bundle"],),
        )
        .fetchall()
    )
    if not b or not rows:
        raise ValueError("This bundle is unavailable.")
    components = []
    for r in rows:
        components.append(
            price_single(
                {
                    "variant": r["variant_id"],
                    "qty": r["qty"] * item["qty"],
                    "grind": r["grind"],
                    "temperature": r["temperature"],
                    "addons": json.loads(r["addons"]),
                }
            )
        )
    total = b["price"] * item["qty"]
    basis = sum(c["total"] for c in components)
    allocated = 0
    for c in components[:-1]:
        c["total"] = total * c["total"] // basis if basis else total // len(components)
        allocated += c["total"]
    components[-1]["total"] = total - allocated
    return dict(
        bundle=b["id"],
        name=b["name"],
        name_ar=b["name_ar"],
        label="Bundle",
        label_ar="مجموعة",
        image=components[0]["image"],
        image_kind=components[0]["kind"],
        product=components[0]["product"],
        variant=None,
        qty=item["qty"],
        unit=b["price"],
        total=total,
        addons=[],
        grind="",
        temperature="",
        kind="bundle",
        components=components,
    )


def movement(vid, before, after, reason, oid=None, actor="Admin"):
    if before == after:
        return
    db().execute(
        "INSERT INTO inventory_movements(variant_id,before_stock,after_stock,delta,reason,order_id,actor) VALUES(?,?,?,?,?,?,?)",
        (
            vid,
            before,
            after,
            None if before is None or after is None else after - before,
            reason,
            oid,
            actor,
        ),
    )
