import sqlite3
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_ar TEXT DEFAULT '', position INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_ar TEXT DEFAULT '', description TEXT DEFAULT '', description_ar TEXT DEFAULT '', kind TEXT NOT NULL CHECK(kind IN ('drink','ground')), category_id INTEGER REFERENCES categories(id), image TEXT DEFAULT '', gallery TEXT DEFAULT '[]', roast TEXT DEFAULT '', origin TEXT DEFAULT '', bean TEXT DEFAULT '', notes TEXT DEFAULT '', grinds TEXT DEFAULT '', temperature TEXT DEFAULT 'hot', preparation TEXT DEFAULT '', active INTEGER DEFAULT 0, featured INTEGER DEFAULT 0, position INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS variants(id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id), label TEXT NOT NULL, label_ar TEXT DEFAULT '', grams INTEGER, price INTEGER CHECK(price>=0), stock INTEGER CHECK(stock IS NULL OR stock>=0), active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS addons(id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id), name TEXT NOT NULL, name_ar TEXT DEFAULT '', price INTEGER NOT NULL CHECK(price>=0), active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, reference TEXT UNIQUE NOT NULL, token TEXT UNIQUE NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL DEFAULT 'New', name TEXT NOT NULL, phone TEXT NOT NULL, address TEXT DEFAULT '', notes TEXT DEFAULT '', requested_time TEXT DEFAULT '', fulfillment TEXT NOT NULL, currency TEXT NOT NULL, subtotal INTEGER NOT NULL, delivery INTEGER NOT NULL, total INTEGER NOT NULL, items TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS media(id INTEGER PRIMARY KEY, filename TEXT UNIQUE NOT NULL, title TEXT NOT NULL, alt TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, username TEXT NOT NULL, action TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT PRIMARY KEY, attempts INTEGER DEFAULT 0, until REAL DEFAULT 0);
"""
LATEST_SCHEMA = 5

DEFAULTS = {
    **{
        "visible_" + key: "1"
        for key in (
            "instagram",
            "facebook",
            "whatsapp",
            "email",
            "phone",
            "address",
            "maps",
            "hours",
            "map_embed",
        )
    },
    "show_choices": "1",
    "show_how": "1",
    "hero_eyebrow": "THE ART OF A GOOD COFFEE",
    "choices_title": "How do you take your LUX?",
    "drinks_title": "Your next favorite, freshly made.",
    "coffee_title": "A better brew begins with the bean.",
    "story_title": "A little luxury. An everyday ritual.",
    "how_title": "Your ritual, delivered.",
    "choice_drink_image": "",
    "choice_coffee_image": "",
    "brand": "Café LUX",
    "currency": "USD",
    "headline": "A little luxury. Every day.",
    "headline_ar": "الفخامة في كل رشفة.",
    "slogan": "Rich Aroma. Superior Taste.",
    "slogan_ar": "عبق غني. مذاق استثنائي.",
    "description": "Exceptional coffee, crafted to your taste. From your first morning sip to your favorite at-home brew, make every day a little LUX.",
    "description_ar": "اكتشف طقوس قهوتك اليومية. تُحضّر على ذوقك وتُستمتع بها على مهل.",
    "about": "We believe a great cup of coffee turns an ordinary moment into something special. Café LUX brings that feeling to your daily ritual — thoughtfully prepared drinks and coffee to make your own.",
    "about_ar": "قصتنا قيد الإعداد. زورونا قريباً لاكتشاف كافيه لوكس.",
    "address": "",
    "phone": "",
    "email": "",
    "whatsapp": "",
    "hours": "",
    "maps": "",
    "map_embed": "",
    "instagram": "",
    "facebook": "",
    "tiktok": "",
    "youtube": "",
    "footer": "Crafted for the finest moments.",
    "banner": "",
    "logo": "",
    "hero_image": "",
    "story_image": "",
    "cafe_image": "",
    "paused": "0",
    "scheduled": "0",
    "opening": "00:00",
    "closing": "23:59",
    "closures": "",
    "ordering": "0",
    "pickup": "1",
    "delivery": "0",
    "delivery_fee": "0.00",
    "minimum": "0.00",
    "pickup_time": "0",
    "show_drinks": "1",
    "show_ground": "1",
    "show_story": "1",
    "show_location": "1",
    "retention_days": "365",
    "privacy": "",
    "privacy_ar": "",
    "terms": "",
    "terms_ar": "",
}


def db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def init_db():
    conn = db()
    existing = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if (
        not existing
        and conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()
    ):
        raise RuntimeError(
            "Unrecognized database. Check the intended Café LUX data directory; no changes applied."
        )
    version = (
        conn.execute("SELECT coalesce(max(version),0) FROM schema_version").fetchone()[
            0
        ]
        if existing
        else 0
    )
    if version > LATEST_SCHEMA:
        raise RuntimeError(
            "This database needs a newer Café LUX release. Refusing to downgrade."
        )
    if version and version < LATEST_SCHEMA:
        from .maintenance import database_snapshot

        snapshot = database_snapshot(conn, f"pre-migration-v{version}")
        current_app.logger.info("Verified migration snapshot: %s", snapshot)
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR IGNORE INTO schema_version VALUES (1)")
    if not conn.execute("SELECT 1 FROM schema_version WHERE version=2").fetchone():
        conn.execute(
            "ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1"
        )
        conn.execute("INSERT INTO schema_version VALUES (2)")
    if not conn.execute("SELECT 1 FROM schema_version WHERE version=3").fetchone():
        conn.executescript(
            """
        BEGIN IMMEDIATE;
        ALTER TABLE variants ADD COLUMN allowed_grinds TEXT DEFAULT '';
        ALTER TABLE variants ADD COLUMN allowed_temperatures TEXT DEFAULT '';
        ALTER TABLE addons ADD COLUMN option_group TEXT DEFAULT '';
        CREATE TABLE whatsapp_numbers(id INTEGER PRIMARY KEY, label TEXT NOT NULL, phone TEXT NOT NULL, active INTEGER DEFAULT 1, is_default INTEGER DEFAULT 0);
        CREATE TABLE delivery_areas(id INTEGER PRIMARY KEY, name TEXT NOT NULL, active INTEGER DEFAULT 1, fee INTEGER, minimum INTEGER DEFAULT 0, estimate TEXT DEFAULT '', whatsapp_id INTEGER REFERENCES whatsapp_numbers(id));
        CREATE TABLE schedule_slots(id INTEGER PRIMARY KEY, label TEXT NOT NULL, active INTEGER DEFAULT 1);
        CREATE TABLE order_history(id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), created TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL, username TEXT NOT NULL);
        ALTER TABLE orders ADD COLUMN receiving_phone TEXT DEFAULT '';
        ALTER TABLE orders ADD COLUMN area TEXT DEFAULT '';
        ALTER TABLE orders ADD COLUMN fee_known INTEGER DEFAULT 1;
        ALTER TABLE orders ADD COLUMN stock_deducted INTEGER DEFAULT 1;
        ALTER TABLE orders ADD COLUMN stock_changes TEXT;
        ALTER TABLE categories ADD COLUMN active INTEGER DEFAULT 1;
        ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin';
        CREATE TABLE checkout_limits(ip TEXT PRIMARY KEY, attempts INTEGER DEFAULT 0, started REAL NOT NULL);
        UPDATE orders SET status='Delivered' WHERE status='Completed';
        UPDATE orders SET status='Ready' WHERE status='Ready for Pickup';
        UPDATE orders SET status='Received' WHERE status='New';
        INSERT INTO schema_version VALUES (3);
        COMMIT;
        """
        )
    if not conn.execute("SELECT 1 FROM schema_version WHERE version=4").fetchone():
        conn.executescript(
            """
        BEGIN IMMEDIATE;
        ALTER TABLE categories ADD COLUMN starter_key TEXT;
        ALTER TABLE products ADD COLUMN starter_key TEXT;
        ALTER TABLE variants ADD COLUMN starter_key TEXT;
        ALTER TABLE variants ADD COLUMN sku TEXT DEFAULT '';
        ALTER TABLE variants ADD COLUMN position INTEGER DEFAULT 0;
        ALTER TABLE addons ADD COLUMN starter_key TEXT;
        ALTER TABLE addons ADD COLUMN price_pending INTEGER NOT NULL DEFAULT 0;
        CREATE UNIQUE INDEX categories_starter_key ON categories(starter_key) WHERE starter_key IS NOT NULL;
        CREATE UNIQUE INDEX products_starter_key ON products(starter_key) WHERE starter_key IS NOT NULL;
        CREATE UNIQUE INDEX variants_starter_key ON variants(starter_key) WHERE starter_key IS NOT NULL;
        CREATE UNIQUE INDEX addons_starter_key ON addons(starter_key) WHERE starter_key IS NOT NULL;
        CREATE INDEX products_catalog_order ON products(kind,active,category_id,position,id);
        CREATE INDEX orders_created_status ON orders(status,created);
        CREATE TABLE catalog_seed_log(starter_key TEXT PRIMARY KEY, product_id INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO schema_version VALUES (4);
        COMMIT;
        """
        )
    if not conn.execute("SELECT 1 FROM schema_version WHERE version=5").fetchone():
        from .v4_schema import SQL

        conn.executescript(SQL)
    from .v4_schema import DEFAULTS as V4_DEFAULTS

    for key, value in {**DEFAULTS, **V4_DEFAULTS}.items():
        conn.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (key, value))
    conn.commit()


def settings():
    return {r["key"]: r["value"] for r in db().execute("SELECT * FROM settings")}


def audit(action):
    from flask import session, has_request_context

    db().execute(
        "INSERT INTO audit(username,action) VALUES (?,?)",
        (session.get("username", "CLI") if has_request_context() else "CLI", action),
    )


def close_db(error=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()
