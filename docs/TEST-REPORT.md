> Version 1.0 historical report. For the deployment fix and current test evidence, see [WINDOWS-FIX-TESTS.md](WINDOWS-FIX-TESTS.md).

# Version 1.0 validation report

Validated in the Linux cloud development environment on 2026-11-16 using Python 3.12, Flask 3.1, SQLite and Chromium. These are functional and regression checks, not penetration-test certification.

## Backend: 64 passed, 0 failed, 0 skipped

Command: `/workspace/cafe-lux-venv/bin/python -m pytest -q`.

Coverage includes public pages and navigation; product listing/details; English/Arabic RTL markup; standard and custom weights; independently configured prices; cart changes/removal; variant/add-on selection; server-side price revalidation; pickup/delivery validation and charges; ordering disabled; immutable order snapshots; session-private confirmation; sequential and concurrent idempotency; concurrent oversell prevention; stock cancellation restored once; protected admin endpoints; product creation/edit/archive; content updates and escaping; invalid external links; login throttling; account disable/reset session revocation; safe image upload, public media and reference-aware deletion; migration repeatability; live database/media backup and offline restore; malicious archive traversal refusal; retention and targeted customer anonymization; invalid currency/decimal inputs; CSRF including Unicode invalid tokens; Host checks; cookie/security headers; occupied port refusal; protected storage; missing data configuration and invalid session-key refusal.

## Browser: passed

Command: `/workspace/cafe-lux-venv/bin/python scripts/capture_screenshots.py`.

See [machine-readable results](../screenshots/browser-report.json). The runner starts a real Flask application on an ephemeral loopback port using a disposable synthetic database, then runs Chromium. It checks:

- Desktop homepage and mobile navigation.
- No horizontal overflow on public pages at 320, 375, 390, 768, 1024 and 1440 pixels; representative admin screens at 390 pixels.
- Live variant/add-on/quantity pricing and cart total.
- Guest checkout through stored order confirmation.
- Administrator login, all main management screens and order status updates.
- Arabic language switch, RTL and fallback text.
- Active pouring, steam, bean/grinding and sipping CSS/SVG animations, and disabling animation under reduced motion.
- No JavaScript page errors.

Twelve screenshots show the actual application: desktop/mobile home, drinks, ground coffee, details, cart, checkout, admin overview, catalog management, order management, confirmation and Arabic mobile. Every screenshot uses a prominent test-preview banner and synthetic catalog/customer fixtures. No real business prices or contact information were invented.

## Runtime and packaging

Waitress was started locally on `127.0.0.1:8000`; a homepage HTTP request returned 200. The CLI initialized schema v2 repeatedly without dropping data. Package dependency compatibility (`pip check`) and Python undefined/unused-name checks passed. Release ZIP integrity and runtime-file exclusions are verified during packaging. The ZIP includes source, guides, tests, assets and screenshots, not an installed Windows virtual environment or runtime database.

## Not run / operator acceptance

Windows Server 2022, PowerShell scripts, NTFS ACLs, actual IIS reverse-proxy scheme/Host handling, TLS certificate, boot scheduling and Windows process stop/rollback were not executable in this Linux environment. They require acceptance on your server. Windows scripts were reviewed; the Python occupied-port guard was executed. No IIS configuration or application deployment was performed.

## Known boundaries

- Original packaging image bytes were not available as a downloadable workspace file. Replace the generated default visuals with your original brand/product assets through admin.
- Ordering starts disabled with an empty catalog. Optional demo drafts are unpriced/unpublished; real prices, contact details and business copy must be entered by the owner.
- English and Arabic UI/RTL are supplied; missing product translations fall back to English. Free-text business and option fields need owner-provided Arabic/bilingual content.
- Motion is stylized SVG/CSS, not footage of a person sipping. Default images are generated illustrations, not actual product/location photography.
- Cash only. No payment gateway, automated customer messages, route/zone calculation, tax engine, newsletter service, staff subroles or two-factor login.
- Retention/anonymization and backup expiry are deliberate administrative/operator actions. Pause media edits during backups for a consistent database-plus-media set.
- IIS shares the persistent login rate-limit bucket across admin users; forwarded IP claims are deliberately not trusted.
- Windows shutdown requires manual request draining before the script's owned-process stop. A background process is not an automatically installed Windows service.
- SQLite is intended for one application instance on local disk; capacity/load testing was not performed.
