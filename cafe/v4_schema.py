"""Additive V4 migration. Never populate or publish business data on upgrade."""

SQL = """
BEGIN IMMEDIATE;
CREATE TABLE customers(id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE, password TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT 'en', preferences TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1, session_version INTEGER NOT NULL DEFAULT 1, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE customer_recovery(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), hash TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE customer_addresses(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), label TEXT NOT NULL, area_id INTEGER REFERENCES delivery_areas(id), address TEXT NOT NULL, building TEXT NOT NULL, floor TEXT NOT NULL DEFAULT '', instructions TEXT NOT NULL DEFAULT '');
CREATE TABLE favorites(customer_id INTEGER NOT NULL REFERENCES customers(id), product_id INTEGER NOT NULL REFERENCES products(id), PRIMARY KEY(customer_id,product_id));
CREATE TABLE customer_limits(key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, started REAL NOT NULL);
CREATE TABLE promotions(id INTEGER PRIMARY KEY, code TEXT NOT NULL COLLATE NOCASE UNIQUE, kind TEXT NOT NULL CHECK(kind IN ('percent','fixed')), value INTEGER NOT NULL CHECK(value>0), minimum INTEGER NOT NULL DEFAULT 0, maximum_discount INTEGER, starts TEXT NOT NULL DEFAULT '', ends TEXT NOT NULL DEFAULT '', usage_limit INTEGER, active INTEGER NOT NULL DEFAULT 0);
CREATE TABLE bundles(id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_ar TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', description_ar TEXT NOT NULL DEFAULT '', price INTEGER NOT NULL CHECK(price>=0), active INTEGER NOT NULL DEFAULT 0);
CREATE TABLE bundle_items(id INTEGER PRIMARY KEY, bundle_id INTEGER NOT NULL REFERENCES bundles(id), variant_id INTEGER NOT NULL REFERENCES variants(id), qty INTEGER NOT NULL CHECK(qty BETWEEN 1 AND 99), grind TEXT NOT NULL DEFAULT '', temperature TEXT NOT NULL DEFAULT '', addons TEXT NOT NULL DEFAULT '[]');
ALTER TABLE orders ADD COLUMN customer_id INTEGER REFERENCES customers(id);
ALTER TABLE orders ADD COLUMN promotion_id INTEGER REFERENCES promotions(id);
ALTER TABLE orders ADD COLUMN discount INTEGER NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN language TEXT NOT NULL DEFAULT 'en';
ALTER TABLE orders ADD COLUMN whatsapp_opt_in INTEGER NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN consent_at TEXT;
ALTER TABLE orders ADD COLUMN consent_text TEXT NOT NULL DEFAULT '';
ALTER TABLE orders ADD COLUMN incoming_message_id TEXT;
ALTER TABLE variants ADD COLUMN unit_cost INTEGER CHECK(unit_cost IS NULL OR unit_cost>=0);
ALTER TABLE variants ADD COLUMN low_threshold INTEGER NOT NULL DEFAULT 5 CHECK(low_threshold>=0);
ALTER TABLE variants ADD COLUMN restock_notes TEXT NOT NULL DEFAULT '';
ALTER TABLE variants ADD COLUMN restock_date TEXT NOT NULL DEFAULT '';
ALTER TABLE whatsapp_numbers ADD COLUMN cloud_phone_id TEXT NOT NULL DEFAULT '';
CREATE TABLE inventory_movements(id INTEGER PRIMARY KEY, variant_id INTEGER NOT NULL REFERENCES variants(id), created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, before_stock INTEGER, after_stock INTEGER, delta INTEGER, reason TEXT NOT NULL, order_id INTEGER REFERENCES orders(id), actor TEXT NOT NULL);
CREATE TABLE order_notes(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), created TEXT DEFAULT CURRENT_TIMESTAMP, actor TEXT NOT NULL, note TEXT NOT NULL);
CREATE TABLE website_drafts(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP, actor TEXT NOT NULL);
CREATE TABLE whatsapp_incoming(id INTEGER PRIMARY KEY, message_id TEXT NOT NULL UNIQUE, sender TEXT NOT NULL, phone_id TEXT NOT NULL, reference_text TEXT NOT NULL, order_id INTEGER REFERENCES orders(id), state TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE whatsapp_jobs(id INTEGER PRIMARY KEY, job_key TEXT NOT NULL UNIQUE, order_id INTEGER NOT NULL REFERENCES orders(id), kind TEXT NOT NULL CHECK(kind IN ('Confirmed','Out for Delivery')), state TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0, due REAL NOT NULL DEFAULT 0, lease_until REAL, request_started INTEGER NOT NULL DEFAULT 0, message_id TEXT UNIQUE, error TEXT NOT NULL DEFAULT '', created TEXT DEFAULT CURRENT_TIMESTAMP, updated TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(order_id,kind));
CREATE TABLE whatsapp_attempts(id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES whatsapp_jobs(id), attempt_key TEXT NOT NULL UNIQUE, message_id TEXT, state TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE whatsapp_events(id INTEGER PRIMARY KEY, event_key TEXT NOT NULL UNIQUE, message_id TEXT NOT NULL, status TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX customer_orders ON orders(customer_id,created);
CREATE INDEX whatsapp_due ON whatsapp_jobs(state,due);
CREATE INDEX inventory_variant ON inventory_movements(variant_id,id);
INSERT INTO schema_version VALUES(5);
COMMIT;
"""
DEFAULTS = {
    "wa_automation": "0",
    "wa_confirmed_en": "",
    "wa_confirmed_ar": "",
    "wa_out_en": "",
    "wa_out_ar": "",
    "home_sections": "choices,drinks,ground,bestsellers,bundles,story,how",
    "banner_ar": "",
    "hero_eyebrow_ar": "",
    "story_title_ar": "",
}
