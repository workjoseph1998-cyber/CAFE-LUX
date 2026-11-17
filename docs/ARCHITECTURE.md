# Architecture and security — 3.0

Python 3.11/3.12, Flask, SQLite, Pillow, tzdata and Windows Waitress. Server-rendered Jinja and small local CSS/JS; no Node build, paid API, task scheduler or background worker. `run.py` is the Windows/local loopback entry; root `wsgi.py` is the managed-host entry and never starts a server.

- `cafe/db.py`: original schema, versioned additive migrations through v4, settings/audit. Existing databases are verified/snapshotted before schema changes; newer or unrecognized databases are refused. No table drop/rebuild or business-data reset.
- `maintenance.py`: online SQLite snapshot, reopen/in-memory restore verification and integrity checks before migration/seed writes.
- `starter_catalog.py`: owner-approved descriptions, stable keys, conservative name conflicts and a seed ledger. Explicit CLI only; seed skips existing seeded products wholesale, preserving edited/removed options.
- `catalog.py`: shared server-side publication rules for full editor, quick and atomic bulk actions. Pending extra surcharges are never exposed as free sales.
- `public.py`: existing catalog, signed cart, server-side variant/extra/delivery validation, final review digest, idempotent pending orders, private confirmation and registered media.
- `admin.py`: live role/session checks, compact paginated catalog/orders, validated edits, uploads, operations, backup/retention and notification shortcuts.
- `commands.py` / `manage.py`: existing-admin-safe management, migration status, migrate, explicit seed, verified backup/restore and prepare-update. Backup/status/update preparation do not automatically migrate data.
- `admin.css` / `admin.js`: separate compact admin assets; local sidebar/density preferences, accessible dialog inspector, dirty-form warnings and image preview. Public V3 templates and assets form a separate Espresso Editorial design system.

Passwords use salted Werkzeug scrypt; unknown logins evaluate a dummy hash. Session versions revoke disabled/reset accounts; request-time roles restrict operators to order work. Every mutation requires CSRF; SQL data is parameterized, SQL sort/table names use internal allowlists, and Jinja autoescapes content. Media is byte/pixel limited, EXIF-oriented, resized/re-encoded to randomly named optimized JPEGs and served only when registered. Existing uploads are never rewritten by migration/seed.

Order confirmation uses `BEGIN IMMEDIATE`, unique tokens and revalidated server prices; contacts stay server-side and only a review digest enters the signed cookie. Private order details require the owner session or protected admin access; references alone expose no contacts. Stock is deducted on admin confirmation, not abandoned pending links. Selected option/price snapshots remain immutable when products change.

HTTPS secure HttpOnly SameSite cookies are default; Windows setup intentionally supports internal HTTP testing. Exact Host allowlists, CSP, anti-framing, MIME and private-page no-store headers apply. PythonAnywhere/IIS scheme trust is explicit and never trusts forwarded hosts or client IPs. The conservative direct-IP limiter can therefore be shared behind a proxy; no spoofable forwarded IP is accepted.

SQLite runs against one local persistent disk/instance, not a network share. Data, accounts, orders, prices, uploads, keys, backups and runtime settings stay outside Git. Windows and Linux data are independent. WSGI uses normal Flask logging to hosting-managed error logs; Windows additionally rotates its app logfile. Operators handle off-host encrypted backups, retention, quota, maintenance windows and manual reloads. No automatic deployment or private-data synchronization is implemented.


V3 adds read-only `/finder` and `/recently-viewed` routes. The Finder filters published/category-active records by configured product attributes. Recently viewed accepts at most six IDs and rebuilds cards from current visibility. The browser stores only IDs, not price/product copies or customer information. The cart drawer consumes the same protected server forms; no pricing, order creation, stock mutation or route authorization is moved into JavaScript. New availability labels are derived read-only from the existing configuration. Schema remains v4 and the WSGI/Windows entry points are unchanged.
