# Architecture and security

Python 3.12, Flask 3.1, SQLite, Pillow and Waitress. Server-rendered Jinja templates, local CSS/JS and optimized generated editorial images. No Node build, CDN scripts, payment SDK or external database is required. No analytics/tracking scripts or third-party fonts load. Maps/social destinations load only when configured by an administrator.

- `cafe/__init__.py`: app factory, CSRF, cookies, Host allowlist, response headers, proxy scheme configuration.
- `cafe/db.py`: schema v1 and additive migration v2 (session revocation version), settings, audit logging. Initialization is repeatable. Back up before upgrades.
- `cafe/public.py`: catalog, variants, signed-session cart, locked checkout, confirmation access and public media.
- `cafe/admin.py`: protected management, persistent login limiter, uploads, reports, retention and backups.
- `cafe/commands.py`: first admin, drafts, database initialization, backup/restore.
- `run.py`: dedicated listener and occupied-port guard.
- `scripts/`: Windows setup/process ownership controls, browser acceptance and source ZIP packaging.

## Security controls

Passwords use Werkzeug's salted scrypt hashes. A random unusable dummy hash is checked for unknown usernames to reduce timing differences; it is never an account credential. Server-side user lookups and session versions revoke disabled/reset accounts. Session IDs, CSRF values, checkout idempotency tokens, media filenames and references use cryptographic randomness. A persistent per-install key signs HttpOnly sessions. Production cookies are Secure and SameSite=Lax; no secret is committed. The signed client cookie contains catalog IDs, selected options and quantities, never customer contact details or trusted prices.

Every POST (including login/logout/language) requires a session CSRF token. Admin URLs check current active authorization on every request. Jinja autoescaping renders content as text. SQL values are parameterized; dynamic columns and tables are selected only from internal allowlists. HTTPS links and Google embed origins are validated. Host headers are restricted; only the scheme from one explicitly trusted local proxy can be accepted.

Checkout ignores submitted prices/totals. Under `BEGIN IMMEDIATE`, it re-reads product/variant/add-on prices, checks availability/stock, decrements tracked inventory, stores line snapshots and totals, and commits before showing confirmation. A unique token protects repeat submission from the same session. Tokens rotate for a new checkout. Invalid data rolls back; stock cannot go negative through concurrent checkout. Duplicate browser requests return the original order. Cart quantity, selection count, text length, upload bytes/pixels and prices are bounded.

Upload filenames are random, originals never executed, metadata removed, dimensions reduced, and image contents re-encoded. Only database-listed files are served through a dedicated route. Database, keys, logs and backups live outside the repository and public static directory. A restrictive CSP, anti-framing and MIME-sniff prevention headers apply. Administrative/customer-specific pages use `Cache-Control: no-store`. Audit events omit passwords and customer addresses. Application exception logs are access-restricted operational data.

## Boundaries

All admins have one full-management role; there is no staff-level role or two-factor login in v1. The limiter deliberately uses the direct proxy address rather than trusting forwarded IP claims. There is no distributed denial-of-service protection. IIS must enforce HTTPS, overwriting forwarded scheme headers, network exposure, and operational access restrictions. No penetration-test certification is claimed.

SQLite fits a small single-instance café workload. Use one app instance against a local persistent disk, regular backups and managed Windows permissions. Do not share the SQLite file over a network drive. Retention is an explicit admin action; offline backup expiry is an operator responsibility. This release does not implement online payments, customer accounts, tax rules, delivery-zone calculation, stock by raw bean gram, email/SMS automation or automated IIS deployment.
