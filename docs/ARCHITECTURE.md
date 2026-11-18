# Architecture and security — 4.0

Flask, SQLite, Pillow and Waitress remain. No browser build pipeline or remote font/script dependency. `public.py` validates cart/options/prices/review/idempotent pending orders; `commerce.py` handles integer-cents offers, bundle expansion and aggregate stock; `customer.py` holds optional customer identity; `workspace.py` adds admin management/reporting; `whatsapp.py` provides official Graph transport, signed webhook and durable worker. `v4_schema.py` is the additive schema-5 migration.

Runtime data lives outside source: SQLite, uploads, backups, logs and session key. Setup does not seed or reprice products. `database_snapshot` uses SQLite online backup and verifies the reopened result. Full backup ZIPs include registered media and DB, exclude secrets. Preserve all external data before upgrades/restores.

## Identity and data boundaries

Separate customer/staff tables, scrypt password hashes, CSRF-protected writes, HttpOnly/SameSite cookies, HTTPS-secure cookies by default, current server session-version checks and bounded identity lifetime. Customer registration/login/recovery rate limits persist per client IP in SQLite. Profile email is optional and not treated as verified ownership. Recovery uses random one-use codes hashed at rest, displayed once; successful reset revokes all customer sessions. There is no configured email/SMS recovery provider and no fabricated email-delivery claim.

Order reads, reorder and saved-address selection use authenticated customer IDs. Only orders created while signed in carry that identity; phone equality grants no access. Guest order access retains the existing signed session's last-order reference. Favorites merge only published valid product IDs. Staff roles remain admin/operator; operators retain order workflows, while customer profiles, integration settings, catalog, costs and backups require admin. Account profile removal is audited, revokes sessions and preserves active-order fulfillment records. Backup retention must be managed separately.

All prices, promotions, bundle components and stock are revalidated server-side. Promotion usage is checked under the final checkout lock; pending submissions reserve capacity for 30 minutes, staff confirmation checks again, and cancellations release capacity. A changed offer blocks confirmation rather than silently changing an agreed total. Stock is deducted once at fulfillment confirmation, recorded by variant and reversed once on cancellation. Bundle stock expands to actual component quantities; reporting allocates the bundle price proportionally using integer cents. Historical gross sales remain delivered subtotal, with discounts/net separate and currencies partitioned. Cost/profit is shown only when every needed snapshot cost exists; add-ons without reliable costs suppress profit.

## Integration boundary

The exact webhook POST is the sole CSRF exemption and requires raw-body HMAC-SHA256 before parsing. Matching also verifies sender, selected receiver, reference and plausible time. Deduplicated IDs and short SQLite transactions prevent replay side effects. The job table constrains automatic types to the two authorized statuses and unique order/type. Tokens are read from env only, never echoed into UI/logs. HTTPS requests disable redirects to prevent credential forwarding. Tests use an injected adapter or explicit mock outcomes, never real messages.

A send may succeed while its HTTP response is lost; exactly-once delivery cannot be promised. Durable send-boundary/lease records classify that as uncertain for staff reconciliation instead of unsafe blind retries. Signed provider status callbacks advance confirmed delivery state; API acceptance alone is submitted. See [WhatsApp](WHATSAPP.md).

## Concurrency and deployment limits

SQLite remains appropriate for modest single-host activity with a local persistent disk, a 15-second busy timeout and short transactions. Web checkout/status changes and worker leasing use `BEGIN IMMEDIATE`; network I/O happens after commit. Default rollback journal remains for compatibility with existing offline restore tooling. Stop all processes for migration/restore. Run one supervised notification worker. Monitor write latency/lock errors and queue delay under real load; use a planned shared DB/queue migration before multi-host scaling. PythonAnywhere free automation limitations are documented, not bypassed.

CSP limits scripts/styles/images to local assets, trusted hosts are explicit, proxy trust is opt-in for scheme only, uploads are decoded/re-encoded with size/pixel caps, internal errors are generic and private endpoints use no-store. Application IP limits assume direct/local reverse proxy addressing; no untrusted forwarded address is accepted. At higher traffic use a trusted reverse proxy rate limiter configured by the host. No live penetration/load test or external Meta delivery was performed in this development environment.
