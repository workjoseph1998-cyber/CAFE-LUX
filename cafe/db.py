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
DEFAULTS = {
    "brand": "Café LUX",
    "currency": "USD",
    "headline": "Luxury in Every Sip.",
    "headline_ar": "الفخامة في كل رشفة.",
    "slogan": "Rich Aroma. Superior Taste.",
    "slogan_ar": "عبق غني. مذاق استثنائي.",
    "description": "Discover your daily coffee ritual. Prepared to your taste, enjoyed at your pace.",
    "description_ar": "اكتشف طقوس قهوتك اليومية. تُحضّر على ذوقك وتُستمتع بها على مهل.",
    "about": "Our story is being prepared. Visit again soon to discover Café LUX.",
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
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR IGNORE INTO schema_version VALUES (1)")
    if not conn.execute("SELECT 1 FROM schema_version WHERE version=2").fetchone():
        conn.execute(
            "ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1"
        )
        conn.execute("INSERT INTO schema_version VALUES (2)")
    for key, value in DEFAULTS.items():
        conn.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (key, value))
    if not current_app.testing or current_app.config.get("SEED_STARTER_CATALOG", False):
        from .starter_catalog import seed_catalog

        seed_catalog(conn)
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
