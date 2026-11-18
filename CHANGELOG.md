# Changelog

## 4.0.0 — 2026-11-18

- Quiet Ritual storefront and forest operations workspace; optional customer accounts/recovery, private addresses/history/reorder and favorites.
- Persistent bundles/promotions, inventory movements/thresholds/cost snapshots, website drafts/publishing and currency-separated reports.
- Official signed Meta webhook, safe incoming matching, consent records, exactly two automatic notification types and durable worker with honest uncertainty handling.
- Additive verified schema-5 migration; Windows/PythonAnywhere contracts retained, live deployment and Meta activation remain separate.
- Area-assigned WhatsApp receivers now enable checkout without requiring a global default.
- New migration/security/integration/browser regression coverage and V4 source package.


## 3.0.0 — 2026-11-17

- Rebuilt the customer design system around Espresso Editorial Luxury: full-bleed imagery, oversized typography, asymmetric collection scenes, new product cards, navigation, footer and brand-story layouts.
- Redesigned product customization, galleries and quantity controls; added a server-backed accessible bag drawer with live edits and a dedicated checkout footer. Full-page/no-JavaScript cart remains available.
- Rebuilt checkout, final review and pending WhatsApp screens with live real delivery totals, mobile item disclosure, accurate submission language and existing duplicate protection.
- Added a published-data Coffee Finder, browser-local recently viewed product IDs with server visibility revalidation, actual ordering-status labels, expanded RTL translations and reduced-motion-safe microinteractions.
- Replaced the admin visual system with a separate compact operations workspace, redesigned metrics/activity panels, sidebar/header, catalog/order tables, editor/forms, statuses and inspector. Existing role checks and business actions remain.
- Kept schema v4, Windows scripts/port, WSGI entry point, dependencies, business data, uploads, prices, stock logic and WhatsApp routing. No automatic merge or deployment.

## Final catalog — 2.1.2

- Added the owner-requested explicit action to fill missing illustrations, descriptions and editable sample prices, then publish starter products on the actual customer storefront.
- Enabled untouched, newly priced starter options and example surcharges; preserved existing prices, availability edits, stock, accounts and order history. No store hours, delivery or WhatsApp configuration is invented.
- Added featured starter drinks/coffee on first publication and current customer-perspective screenshots. All sample prices remain editable.
- Retained verified full backups before catalog changes.

## 2.1.1 — 2026-11-17

- Bundled 22 original sample illustrations at 480 × 400 px (236,346 bytes total; largest 11,379 bytes). No external image downloads.
- Added private storefront-style catalog previews showing all approved draft products and their full descriptions.
- Added one-click sample preparation and `prepare-catalog-preview` CLI, with a verified full backup and missing-fields-only updates. Existing images, edited descriptions, accounts, orders, prices and publication states are preserved.
- Kept schema v4 and the existing Windows/WSGI deployment model; no automatic publishing, fabricated prices or deployment.

## 2.1.0 — 2026-11-17

- Added an explicit, verified-backup-first, idempotent approved starter-catalog seed: 18 drinks, four coffees, independent 200 g / 500 g / 1 kg preparations and targeted draft customization. All start unpublished, with prices/stock unset and no assigned photography.
- Added stable catalog identities, conservative name-conflict reports and a seed ledger preserving administrator edits and intentional removals.
- Added additive schema v4, verified pre-migration SQLite snapshots, read-only migration status and a manual update-preparation backup command. No existing accounts, orders, settings or uploads are replaced.
- Rebuilt administration as a compact laptop workspace with collapsible remembered sidebar, density preferences, dashboard summary, paginated/searchable product and order tables, order inspector, concise settings tables and editor sections.
- Added shared publication checks, validated bulk/quick actions, per-variant SKU/order, direct product-photo upload and unsaved-change warnings. Pending extra surcharges are excluded from public ordering.
- Added the real Flask WSGI entry point, environment examples and complete manual PythonAnywhere free-plan guide. Windows scripts/IIS contract/port 8000 remain intact; no hosting deployment or customer-data synchronization occurs.
- Retained the existing public storefront design and all V2.0 cart, review, WhatsApp, delivery, permissions and stock behaviors.

## 2.0.0

Preserved as commit `3cd9d1e` and in repository history. Mobile storefront, WhatsApp ordering, delivery/admin operations and dedicated Windows data storage.
