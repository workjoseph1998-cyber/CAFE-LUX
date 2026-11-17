-- Exact schema from the shipped Version 2.0 commit 3cd9d1e. Synthetic tests only.

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

ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1;
INSERT INTO schema_version VALUES (1);
INSERT INTO schema_version VALUES (2);

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
