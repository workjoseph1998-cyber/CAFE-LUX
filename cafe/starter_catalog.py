"""Owner-approved draft catalog. Never called by startup, setup, or migrations."""

import re
import unicodedata
from difflib import SequenceMatcher
from .db import db, audit
from .maintenance import database_snapshot

DRINKS = [
    (
        "espresso-classics",
        "Espresso & Classics",
        [
            ("espresso", "Espresso", "Short, concentrated coffee.", "single", "hot"),
            (
                "double-espresso",
                "Double Espresso",
                "Two espresso shots.",
                "single",
                "hot",
            ),
            (
                "americano",
                "Americano",
                "Espresso combined with hot water.",
                "sizes",
                "hot",
            ),
            (
                "macchiato",
                "Macchiato",
                "Espresso with a small amount of milk foam.",
                "single",
                "hot",
            ),
            (
                "cortado",
                "Cortado",
                "Espresso with a balanced portion of steamed milk.",
                "single",
                "hot",
            ),
        ],
    ),
    (
        "milk-based",
        "Milk-Based Coffee",
        [
            (
                "cappuccino",
                "Cappuccino",
                "Espresso, steamed milk, and foam.",
                "sizes",
                "hot",
            ),
            (
                "caffe-latte",
                "Caffè Latte",
                "Espresso with steamed milk.",
                "sizes",
                "hot",
            ),
            (
                "flat-white",
                "Flat White",
                "Espresso with finely textured milk.",
                "single",
                "hot",
            ),
            ("mocha", "Mocha", "Espresso, milk, and chocolate.", "sizes", "hot"),
            (
                "spanish-latte",
                "Spanish Latte",
                "Espresso and milk with a sweet, creamy character.",
                "sizes",
                "hot",
            ),
        ],
    ),
    (
        "iced-coffee",
        "Iced Coffee",
        [
            (
                "iced-americano",
                "Iced Americano",
                "Espresso, chilled water, and ice.",
                "sizes",
                "cold",
            ),
            ("iced-latte", "Iced Latte", "Espresso, milk, and ice.", "sizes", "cold"),
            (
                "iced-spanish-latte",
                "Iced Spanish Latte",
                "Chilled espresso and milk with a sweet, creamy character.",
                "sizes",
                "cold",
            ),
            (
                "iced-mocha",
                "Iced Mocha",
                "Espresso, milk, chocolate, and ice.",
                "sizes",
                "cold",
            ),
            (
                "cold-brew",
                "Cold Brew",
                "Coffee brewed with cold water over an extended period.",
                "sizes",
                "cold",
            ),
        ],
    ),
    (
        "arabic-traditional",
        "Arabic & Traditional Coffee",
        [
            (
                "lebanese-coffee",
                "Lebanese Coffee",
                "Traditional finely ground coffee preparation.",
                "single",
                "hot",
            ),
            (
                "lebanese-cardamom",
                "Lebanese Coffee with Cardamom",
                "Traditional finely ground coffee with cardamom.",
                "single",
                "hot",
            ),
            (
                "turkish-coffee",
                "Turkish Coffee",
                "Traditional finely ground coffee preparation.",
                "single",
                "hot",
            ),
        ],
    ),
]
COFFEE = [
    (
        "traditional-coffee",
        "Traditional Coffee",
        "lux-lebanese",
        "LUX Lebanese Blend",
        "Discover the rich character of traditional Lebanese-style coffee, crafted for a familiar and comforting coffee ritual.",
        ["Plain ground coffee", "Ground coffee with cardamom"],
    ),
    (
        "signature-blends",
        "Signature Blends",
        "lux-signature",
        "LUX Signature Blend",
        "Our signature coffee experience, created for everyday moments worth enjoying.",
        ["Whole coffee beans", "Ground coffee"],
    ),
    (
        "espresso-blends",
        "Espresso Blends",
        "lux-espresso",
        "LUX Espresso Roast",
        "A bold coffee experience designed for those who enjoy a full-flavored espresso.",
        ["Whole coffee beans", "Espresso-ground coffee"],
    ),
    (
        "specialty-blends",
        "Specialty Blends",
        "lux-golden",
        "LUX Golden Roast",
        "A smooth, approachable coffee experience for customers who enjoy a balanced cup.",
        ["Whole coffee beans", "Ground coffee"],
    ),
]
MILK_DRINKS = {
    "cappuccino",
    "caffe-latte",
    "flat-white",
    "mocha",
    "spanish-latte",
    "iced-latte",
    "iced-spanish-latte",
    "iced-mocha",
}
SYRUP_DRINKS = {"caffe-latte", "iced-latte", "cold-brew"}
STRENGTH_DRINKS = {
    "americano",
    "cappuccino",
    "caffe-latte",
    "flat-white",
    "mocha",
    "spanish-latte",
    "iced-americano",
    "iced-latte",
    "iced-spanish-latte",
    "iced-mocha",
    "cortado",
}


def normalized(name):
    return "".join(
        c for c in unicodedata.normalize("NFKD", name).casefold() if c.isalnum()
    )


def conflict(conn, table, name):
    wanted = normalized(name)
    for row in conn.execute(f"SELECT id,name,starter_key FROM {table}"):
        other = normalized(row["name"])
        if not row["starter_key"] and (
            other == wanted or SequenceMatcher(None, other, wanted).ratio() >= 0.93
        ):
            return row
    return None


def seed_catalog(dry_run=False):
    conn = db()
    messages = []
    if not dry_run:
        snapshot = database_snapshot(conn, "pre-starter-catalog")
        messages.append(f"Verified, restorable SQLite safety snapshot: {snapshot}")
    conn.execute("BEGIN IMMEDIATE" if not dry_run else "BEGIN")
    created = {"categories": 0, "drink": 0, "ground": 0, "variants": 0, "addons": 0}
    try:

        def category(key, name, position):
            stable = "starter.v21.category." + key
            row = conn.execute(
                "SELECT id FROM categories WHERE starter_key=?", (stable,)
            ).fetchone()
            if row:
                return row["id"]
            if conn.execute(
                "SELECT 1 FROM catalog_seed_log WHERE starter_key=?", (stable,)
            ).fetchone():
                messages.append(f"SKIP removed seeded category: {name}")
                return None
            matched = conflict(conn, "categories", name)
            if matched:
                messages.append(
                    f'CONFLICT category "{name}" resembles existing #{matched["id"]} "{matched["name"]}"; skipped for manual review.'
                )
                return None
            created["categories"] += 1
            if dry_run:
                return -1
            cid = conn.execute(
                "INSERT INTO categories(name,position,starter_key) VALUES (?,?,?)",
                (name, position, stable),
            ).lastrowid
            conn.execute(
                "INSERT INTO catalog_seed_log(starter_key) VALUES (?)", (stable,)
            )
            return cid

        def product(
            key,
            name,
            description,
            kind,
            cid,
            position,
            temp="hot",
            types=None,
            sizes=None,
        ):
            stable = "starter.v21.product." + key
            if (
                conn.execute(
                    "SELECT 1 FROM products WHERE starter_key=?", (stable,)
                ).fetchone()
                or conn.execute(
                    "SELECT 1 FROM catalog_seed_log WHERE starter_key=?", (stable,)
                ).fetchone()
            ):
                messages.append(f"UNCHANGED previously seeded: {name}")
                return
            matched = conflict(conn, "products", name)
            if matched:
                messages.append(
                    f'CONFLICT product "{name}" resembles existing #{matched["id"]} "{matched["name"]}"; skipped for manual review.'
                )
                return
            if cid is None:
                messages.append(f"SKIP {name}: category needs manual review.")
                return
            created[kind] += 1
            options = []
            if kind == "drink":
                options = [(label, None, "", temp) for label in sizes]
            else:
                options = [
                    (f"{preparation} · {label}", grams, preparation, "")
                    for preparation in types
                    for label, grams in [("200 g", 200), ("500 g", 500), ("1 kg", 1000)]
                ]
            extras = (
                {"Sugar": ["No sugar", "Less sugar", "Regular sugar", "Extra sugar"]}
                if kind == "drink"
                else {}
            )
            if key in MILK_DRINKS:
                extras["Milk"] = ["Regular milk", "Oat milk", "Almond milk"]
            if key in STRENGTH_DRINKS:
                extras["Espresso strength"] = ["Standard", "Extra shot"]
            if key in SYRUP_DRINKS:
                extras["Syrup"] = ["No syrup", "Vanilla", "Caramel", "Hazelnut"]
            created["variants"] += len(options)
            created["addons"] += sum(len(v) for v in extras.values())
            messages.append(
                ("PLAN" if dry_run else "CREATE")
                + f" draft: {name} ({len(options)} unpriced variants)"
            )
            if dry_run:
                return
            pid = conn.execute(
                "INSERT INTO products(name,description,kind,category_id,temperature,grinds,position,starter_key,active,featured) VALUES (?,?,?,?,?,?,?,?,0,0)",
                (
                    name,
                    description,
                    kind,
                    cid,
                    temp,
                    ",".join(types or []),
                    position,
                    stable,
                ),
            ).lastrowid
            conn.execute(
                "INSERT INTO catalog_seed_log(starter_key,product_id) VALUES (?,?)",
                (stable, pid),
            )
            for index, (label, grams, grind, temperature) in enumerate(options):
                conn.execute(
                    "INSERT INTO variants(product_id,label,grams,price,stock,active,allowed_grinds,allowed_temperatures,position,starter_key) VALUES (?,?,?,NULL,NULL,0,?,?,?,?)",
                    (
                        pid,
                        label,
                        grams,
                        grind,
                        temperature,
                        index,
                        stable + f".variant.{index}",
                    ),
                )
            for group, names in extras.items():
                for label in names:
                    # V2's non-null price column is retained. Pending flag + inactive
                    # prevents the storage sentinel from ever becoming a sale price.
                    aid = (
                        stable + ".extra." + normalized(group) + "." + normalized(label)
                    )
                    conn.execute(
                        "INSERT INTO addons(product_id,name,option_group,price,active,price_pending,starter_key) VALUES (?,?,?,0,0,1,?)",
                        (pid, label, group, aid),
                    )

        for position, (key, name, items) in enumerate(DRINKS):
            cid = category(key, name, position * 10)
            for order, (slug, title, description, sizing, temp) in enumerate(items):
                product(
                    slug,
                    title,
                    description,
                    "drink",
                    cid,
                    order,
                    temp,
                    sizes=(
                        ["Single serving"]
                        if sizing == "single"
                        else ["Small", "Regular", "Large"]
                    ),
                )
        for position, (key, category_name, slug, name, description, types) in enumerate(
            COFFEE
        ):
            cid = category(key, category_name, 40 + position * 10)
            product(slug, name, description, "ground", cid, position, types=types)
        if dry_run:
            conn.rollback()
        else:
            audit("Starter catalog seed: " + str(created))
            conn.commit()
        messages.append(
            ("Dry-run plan" if dry_run else "Created")
            + ": "
            + ", ".join(f"{value} {key}" for key, value in created.items())
        )
        messages.append(
            "All new products remain drafts. Prices and stock are unset; extras require price review and activation. Existing edits were not overwritten."
        )
        return messages
    except Exception:
        conn.rollback()
        raise
