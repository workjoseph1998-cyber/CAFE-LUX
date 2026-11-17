# Version 2.0 validation — 2026-11-17

Development platform: Linux, Python 3.12, Flask 3.1.2, SQLite, headless Chromium. All orders, phone numbers and test offers are fictional fixtures in temporary external data directories. No live database or VM was accessed. No WhatsApp message was sent.

## Automated application tests

79 tests passed with `python -m pytest -q`. Coverage includes:

- Public/admin routes, CSRF, login rate limiting, password reset/session revocation, operator permissions, private order access, safe uploads and media usage protection.
- Independent configured weights and prices, sizes, extras, mixed carts, quantity edits, out-of-stock checks, exclusive extras and per-variant grind constraints.
- Final review before storage, price changes requiring another review, server-priced delivery fees and minimums, disabled areas, unknown delivery fees.
- Store closed/paused behavior, active and invalid scheduled slots.
- Pending WhatsApp orders and correctly encoded server-generated messages, routing and disabled-receiver fallback, absent receivers disabling checkout.
- Sequential/concurrent duplicate submissions, concurrent pending orders and stock confirmation under a write lock, one-time cancellation restoration, status history, manual notification links.
- Backup/restore, additive legacy database migration retaining products/orders, repeated initialization and persistence, malicious backup paths, WSGI factory compatibility, diagnostic import and writable directories; actual management entry point and initial-admin command.
- Occupied-port guard, invalid prices/hosts/session keys, external data isolation and protected storage.

## Browser acceptance

`python scripts/capture_screenshots.py` uses a disposable synthetic database and local loopback server. The actual generated screenshots are in `screenshots/`; the machine-readable browser report is `screenshots/browser-report.json`.

Checked desktop and mobile homepage, both catalogs, product choices/live totals, quantity/extras, cart, guest delivery details, explicit review, pending submission/WhatsApp URL, admin login/orders, status updates, catalog/content/media/operations pages, Arabic RTL and reduced-motion behavior. Viewport sweep: 320, 375, 390, 768, 1024 and 1440 pixels. No horizontal overflow or JavaScript runtime errors were found.

## Release verification

Python source compilation, Git whitespace checks and ZIP integrity checks run before packaging. The release excludes databases, session keys, customer data, environments, logs and secrets. Existing generated illustrative assets are retained; actual packaging photography must be uploaded by the operator.

## Not tested here

Windows Server 2022, PowerShell process management, fresh/repeated installation on Windows, NTFS permissions, your existing IIS/ARR configuration, iOS Safari, Android Chrome, actual WhatsApp handoff/send/delivery and PythonAnywhere hosting were not exercised. Browser viewport checks are Chromium emulation, not real-device certification. Windows scripts were inspected and underlying Python checks run on Linux; use the VM checklist in WINDOWS.md before use. No public deployment was performed.

Schedule slots are administrator-maintained labels with enabled/disabled availability, not capacity-managed calendar bookings. Receiving phone validity is syntactic; the operator must verify the number actually has WhatsApp. No test claims messages were sent or received.
