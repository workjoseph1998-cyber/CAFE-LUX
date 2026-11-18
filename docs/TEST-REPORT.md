# Café LUX 4.0 validation — 2026-11-18

All application tests run on isolated temporary SQLite databases/uploads, with synthetic accounts/orders/prices. No production database, live hosting, real customer record or actual WhatsApp send is used.

## Automated application coverage

**144 pytest tests pass**: retained catalog, publication, upload, variant/customization, stock, checkout idempotency, CSRF, staff permissions, backup/restore, legacy migration, WSGI and Windows source-contract regressions, plus 38 new V4 cases.

V4 coverage includes optional account creation/login, one-use recovery and session revocation, account/order/address isolation (including logout/shared-browser ownership), no historical phone linking, favorites merge/visibility, reordering at current prices/stock, server-calculated discounts, usage limits/cancellation and a concurrent last-use promotion race, bundle aggregate inventory and exact cancellation reversal, inventory movements, draft-versus-published website content, currency-separated reports and missing-cost suppression, customer privacy management and complete schema-5 customer-data backup/CLI restore.

Integration tests validate webhook challenge/HMAC rejection, exact incoming sender/reference/time/receiver binding, unmatched/ambiguous review and duplicate-message handling; only the two authorized trigger types; no consent/no queue; mock outcomes never sent; approved template requirements; safe bounded retry and unknown-outcome handling; lost-worker leases; consent withdrawal; provider callback receiver binding, monotonic delivery state and late-callback isolation across manually retried attempts. Test configuration forbids real Graph HTTP, using only injected transport contracts or explicit mock state. No claim of externally verified Meta delivery.

## Browser coverage

Run `scripts/capture_screenshots.py` for retained ordering/admin acceptance and `scripts/check_v4_browser.py` for new persistent features, using Chromium/Playwright Linux headless. Reports/screenshots live under `screenshots/v4/`.

Retained acceptance covers draft visibility, admin tables at 1366/1440/1920, sidebar/density, secure media upload, validated publication, real product options/live pricing, cart drawer editing, full-page/no-JavaScript fallback, delivery/review/manual WhatsApp semantics, Finder, recently viewed and English/Arabic layouts. Customer page overflow checks cover widths 320/360/390/430/768/1024.

V4 acceptance exercises guest favorites → registration → saved profile/email/address → quick add and bundle → applied discount → saved-address checkout and opt-in → review → pending manual-Send confirmation → private history/reorder → staff confirmation and mock durable worker. New account/favorites/bundle/admin screens are checked at 320/390/768/1366, and new Arabic RTL screens are verified. Browser console errors must be empty. The external WhatsApp Send link is deliberately not clicked.

## Packaging and limits

`pip check` reports no broken requirements. Source ZIP uses tracked files only, excludes databases/runtime directories/secrets/virtualenv/logs and carries a separate SHA-256 checksum. Upgrade/restore tests verify integrity and foreign-key consistency. Git recovery bundle was verified before V4 edits.

Linux application/browser checks do not constitute actual Windows Server/IIS or PythonAnywhere deployment, a production load/penetration test, or real Meta business onboarding/template approval/delivery verification. The host must provide HTTPS, protected service environments, allowed outbound Graph networking and a supervised worker before live automation. PythonAnywhere free limits can prevent that. GitHub API access is network-blocked here, so releases/default-branch settings/branch protection remain externally unverified. Merge, final release and destructive cleanup await the brief's required review/approval.
