# Café LUX 3.0 validation — 2026-11-17

Environment: Linux, Python 3.12, Flask 3.1.2, SQLite, headless Chromium. Data is disposable synthetic accounts/orders/products, never the Windows VM or a live hosted database. No WhatsApp message was sent.

## Application verification

**106 tests pass** with `.venv/bin/python -m pytest -q`.

The complete retained regression suite covers authentication/roles/session revocation, CSRF, validated uploads, backup/restore and migration compatibility, draft privacy, independent weights/prices/extras, mixed carts, server totals, delivery minimums/unknown fees, store pauses/closures/scheduling, idempotent/concurrent pending submissions, receiver routing, stock deduction/restoration and historical order snapshots. The existing sample preparation/publication commands remain explicit and preserve owner edits.

New V3 cases verify:

- Coffee Finder filters current published products using their actual type/temperature/roast fields, excludes drafts and does not invent metadata. Invalid filter values are rejected and empty matches work.
- Recently viewed fragments preserve requested product order, deduplicate IDs, sanitize malformed input and exclude newly hidden products/categories. Only public catalog metadata is returned.
- Drawer markup uses the real server cart/CSRF forms; totals and counts reflect posted changes. Loading a bag does not create orders or deduct stock, and unprotected mutations still fail.
- New pages retain Arabic RTL and privacy behavior.
- Public ordering labels derive from configured business state without changing that state or creating orders.

Source compilation, dependency consistency and Git whitespace checks run before packaging. The complete source ZIP is integrity-tested and excludes private data, keys, logs and virtual environments.

## Chromium acceptance and actual screenshots

Run `.venv/bin/python scripts/capture_screenshots.py`. Current captures/report are in **`screenshots/v3/`**. The runner uses a temporary database and local ephemeral-port server and discards all synthetic data afterward.

Verified:

- New editorial homepage, separate drinks/coffee catalogs, real featured products and polished draft-only empty states.
- New admin overview, drinks/coffee tables, editor and orders at **1366×768, 1440×900 and 1920×1080**; collapse/expand, tooltips and remembered density; search/filter/bulk edits, photo upload, valid publication, order inspection/status change and operations screens.
- Actual signed-out customer views after explicit synthetic catalog publication. No live offers are inferred from screenshots.
- Product quantity buttons, exclusive extra choice and live display totals; mixed drink/coffee cart; drawer add/update counts/totals; standalone cart and native no-JavaScript fallback.
- Real area-fee display: synthetic $20.00 subtotal + $2.50 delivery = $22.50, followed by explicit review and pending WhatsApp order. The URL/message is generated but never opened/sent to an actual business.
- Mobile bag drawer has an independent scrolling item area and visible checkout footer. Mobile checkout item disclosure works; final review remains complete.
- No document-level horizontal overflow at **320, 360, 390, 430, 768 and 1024px** across home, both catalogs, product, cart, checkout and Finder; laptop sizes also pass.
- Coffee Finder returns the five configured cold drinks; recently viewed stores public numeric IDs only and reuses current server data. Mobile menu, Arabic RTL and reduced-motion mode work.
- No JavaScript runtime errors reported.

At 1366×768 the compact admin tables show eight drink rows and nine order rows; all four packaged coffees fit. Tables scroll for larger/narrow inventories and do not remove columns. At 1440×900 the checks show 11/12 drink/order rows; at 1920×1080, 15/15 rows.

## Limits

These results do not claim execution on Windows Server 2022/IIS, PythonAnywhere, iOS Safari or Android Chrome. Browser widths are Chromium emulation. Verify the actual deployment/proxy/cookie/NTFS behavior and real devices before live use. WhatsApp Send, receipt and delivery were not tested or claimed. No hosting deployment or main-branch merge was performed.

V3 preserves schema v4 and actual business settings/accounts/orders/uploads/catalog/prices. UI tests publish only temporary fixtures; installing V3 does not seed/reprice/publish business data. System fonts can differ slightly by operating system. Cross-document view transitions are progressive enhancement; unsupported browsers retain normal navigation, and reduced-motion disables animation. Admin translations remain English; public missing copy translations fall back to English.
