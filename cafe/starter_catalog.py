"""One-time, additive coffee-shop catalog. No invented selling prices or stock."""

MARKER = "starter_catalog_v12"

# Category, Arabic category, type, products (English, Arabic, neutral description).
CATALOG = [
    (
        "Espresso Classics",
        "كلاسيكيات الإسبريسو",
        "drink",
        [
            (
                "Espresso",
                "إسبريسو",
                "A small, concentrated coffee served in a classic espresso cup.",
            ),
            ("Double Espresso", "إسبريسو مزدوج", "A double serving of espresso."),
            ("Americano", "أمريكانو", "Espresso with hot water."),
            (
                "Cappuccino",
                "كابتشينو",
                "Espresso with steamed milk and a layer of milk foam.",
            ),
        ],
    ),
    (
        "Lattes & Chocolate",
        "اللاتيه والشوكولاتة",
        "drink",
        [
            ("Café Latte", "كافيه لاتيه", "Espresso with steamed milk."),
            ("Caramel Latte", "لاتيه كراميل", "Espresso, milk and caramel flavor."),
            ("Vanilla Latte", "لاتيه فانيليا", "Espresso, milk and vanilla flavor."),
            ("Café Mocha", "كافيه موكا", "Espresso with milk and chocolate."),
            ("Hot Chocolate", "شوكولاتة ساخنة", "A warm chocolate drink with milk."),
        ],
    ),
    (
        "Iced Coffee",
        "القهوة المثلجة",
        "drink",
        [
            ("Iced Americano", "أمريكانو مثلج", "Espresso and water, served over ice."),
            ("Iced Latte", "لاتيه مثلج", "Espresso and milk, served over ice."),
            (
                "Iced Caramel Latte",
                "لاتيه كراميل مثلج",
                "Espresso, milk and caramel flavor over ice.",
            ),
            (
                "Cold Brew",
                "كولد برو",
                "Coffee prepared by cold extraction, served chilled.",
            ),
        ],
    ),
    (
        "Arabic & Turkish",
        "القهوة العربية والتركية",
        "drink",
        [
            (
                "Arabic Coffee",
                "قهوة عربية",
                "A traditional-style coffee. Ask the café about preparation and ingredients.",
            ),
            (
                "Turkish Coffee",
                "قهوة تركية",
                "Finely ground coffee prepared in a traditional-style pot.",
            ),
        ],
    ),
    (
        "Ground Coffee",
        "القهوة المطحونة",
        "ground",
        [
            (
                "House Blend",
                "خلطة الدار",
                "Packaged coffee for your home ritual. Choose an available weight and grind.",
            ),
            (
                "Espresso Blend",
                "خلطة الإسبريسو",
                "Packaged coffee for espresso preparation. Choose a weight and grind.",
            ),
            (
                "Arabic Coffee Blend",
                "خلطة القهوة العربية",
                "Packaged coffee for Arabic-style preparation. Choose a weight and grind.",
            ),
            (
                "Turkish Coffee Blend",
                "خلطة القهوة التركية",
                "Packaged coffee for Turkish-style preparation. Choose a weight and grind.",
            ),
        ],
    ),
]


def seed_catalog(conn):
    """Caller owns the transaction. The marker preserves later edits, archives and deletions."""
    if conn.execute("SELECT 1 FROM settings WHERE key=?", (MARKER,)).fetchone():
        return
    for position, (category, arabic, kind, products) in enumerate(CATALOG):
        row = conn.execute(
            "SELECT id FROM categories WHERE name=? ORDER BY id LIMIT 1", (category,)
        ).fetchone()
        category_id = (
            row["id"]
            if row
            else conn.execute(
                "INSERT INTO categories(name,name_ar,position) VALUES (?,?,?)",
                (category, arabic, position),
            ).lastrowid
        )
        for index, (name, name_ar, description) in enumerate(products):
            if conn.execute(
                "SELECT 1 FROM products WHERE name=? AND kind=?", (name, kind)
            ).fetchone():
                continue  # Never replace an existing product, description, price or availability.
            temperature = "cold" if category == "Iced Coffee" else "hot"
            product_id = conn.execute(
                """INSERT INTO products(name,name_ar,description,description_ar,kind,category_id,
                temperature,grinds,active,featured,position) VALUES (?,?,?,?,?,?,?,?,1,?,?)""",
                (
                    name,
                    name_ar,
                    description,
                    "وصف مبدئي — راجع المكونات والتفاصيل مع المقهى.",
                    kind,
                    category_id,
                    temperature,
                    "Whole beans,Fine,Medium" if kind == "ground" else "",
                    int(
                        (kind == "ground")
                        or name
                        in ("Espresso", "Café Latte", "Cappuccino", "Iced Latte")
                    ),
                    position * 10 + index,
                ),
            ).lastrowid
            variants = (
                [
                    (f"{weight} g", f"{weight} غ", weight)
                    for weight in (100, 200, 250, 500, 1000)
                ]
                if kind == "ground"
                else (
                    [("Cup", "فنجان", None)]
                    if category in ("Arabic & Turkish", "Espresso Classics")
                    and name != "Cappuccino"
                    else [("Regular", "عادي", None), ("Large", "كبير", None)]
                )
            )
            for label, label_ar, grams in variants:
                conn.execute(
                    "INSERT INTO variants(product_id,label,label_ar,grams,price) VALUES (?,?,?,?,NULL)",
                    (product_id, label, label_ar, grams),
                )
    conn.execute(
        "INSERT INTO settings(key,value) VALUES (?,?)",
        (MARKER, "Added once; admin edits and removals are retained."),
    )
