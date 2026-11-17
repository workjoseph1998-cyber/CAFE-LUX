# Café LUX 2.1 validation — 2026-11-17

Linux development environment, Python 3.12, Flask 3.1.2, SQLite, headless Chromium. All accounts, orders, photos and prices used for checks are synthetic fixtures in temporary external directories. No business database, Windows VM or PythonAnywhere account was accessed. No WhatsApp message was sent.

## Automated application checks

94 tests pass with `.venv/bin/python -m pytest -q`, including the retained V2.0 regression suite and new V2.1 cases:

- Approved catalog: exactly four drink categories/18 drinks and four coffee categories/four packaged coffees on an empty database; 62 total independently configured variants with 200 g/500 g/1 kg package combinations. Appropriate single servings/sizes and hot/cold separation.
- All seeded products unpublished/unfeatured; no selling prices, stock, assigned photos or fabricated origin/composition/roast/tasting facts. Extras remain pending and disabled, with explicit zero distinguished from an unreviewed numeric storage sentinel.
- Seed reruns create no duplicate categories/products/variants/extras; admin edits and intentional deletions survive. Existing accounts/hashes, orders/history, settings, photos and pre-existing product/options rows remain unchanged. Dry runs and conservative name-conflict reports do not merge unrelated records.
- Draft privacy on home/catalog/search/direct product URLs and crafted cart submissions. Shared editor/quick/bulk publication checks, atomic bulk behavior, explicit image upload, independent variant prices/SKU/order and invalid live-option changes.
- A real mixed checkout of reviewed seeded drinks and packaged coffee: milk, extra shot, syrup, sugar, preparation/weight, quantities and independent prices survive cart calculations, saved snapshots and the encoded WhatsApp message. Later catalog edits do not alter historical orders.
- Existing cart, server-side totals/availability, delivery area/minimum/unknown fee, store closure/pause/schedule, idempotent and concurrent submission, receiver routing/fallback, confirmation stock deduction and one-time cancellation restoration.
- Authentication/CSRF/host allowlist, operator restrictions including private order inspection, session revocation, login limiter, safe upload checks, backup traversal protection and private order access.
- Actual shipped V2.0 schema fixture migrates additively to v4, retaining every tested record. Pre-migration/pre-seed snapshots reopen cleanly, survive restore/integrity checks, and repeated initialization creates no duplicate migration or data. Unsupported newer/unrecognized databases are refused.
- CLI initial-admin entry, explicit seed-directory confirmation, read-only pre-migration status and full update-preparation backup. WSGI import exports the real Flask factory without starting Waitress, retains HTTPS cookies, validates an exact synthetic PythonAnywhere hostname and rejects others.
- Windows batch/script contract and occupied-port guard inspected/tested where platform-independent. Source compilation, dependency consistency, Git whitespace checks and release ZIP integrity checked before delivery.

## Actual Chromium checks and screenshots

`python scripts/capture_screenshots.py` uses an ephemeral synthetic catalog and loopback server. Report: `screenshots/v2.1/browser-report.json`. Screenshots include dashboard, drinks/coffee tables, full editor and order table at every requested laptop size, plus sidebar collapse, operations, order inspector and mobile navigation.

| Viewport | Fully visible drink rows | Fully visible order rows |
|---|---:|---:|
| 1366 × 768 | 8 | 9 |
| 1440 × 900 | 11 | 12 |
| 1920 × 1080 | 15 | 16 |

All four coffee rows fit at each size. Table containers support scrolling for larger inventories/narrow screens, with sticky headers; no columns are removed by responsive CSS. The checks verify no document-level horizontal overflow and all column elements remain accessible.

Browser flow verifies default Compact density, remembered Comfortable/Compact changes, sidebar collapse/expand and icon tooltips across reload, product search/filter/selection/bulk drafting, dirty-form state, real upload flow using a synthetic image, variant pricing/enabling, valid publish, public product/cart integration, private side-panel details, full-page status update, settings pages and 390px navigation. Public home/Drinks/Coffee retain the original V2.0 design and polished empty state while starter products remain drafts. No JavaScript runtime errors were reported.

## Verification boundaries

These are Linux/Chromium results, not execution on Windows Server 2022, IIS/ARR, PythonAnywhere, iOS Safari or Android Chrome. Windows setup repetition, process ownership/stop behavior, NTFS permissions, the actual 172.18.69.59 binding and real PythonAnywhere Web-tab/proxy settings must be checked manually on their respective environments. WSGI smoke tests do not claim a hosted deployment. Actual WhatsApp handoff, Send, receipt and delivery were not tested or claimed.

Scheduled slots remain administrator-maintained enabled labels, not automatic calendar/capacity management. Name-conflict detection is deliberately conservative. Starter descriptions/recipes and photo authenticity need owner review; software validation cannot verify ingredient truth or image ownership. Public availability begins only after explicit administrator publication.
