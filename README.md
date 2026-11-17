# Café LUX — Version 3.0

**Espresso Editorial Luxury:** a complete customer and operations interface redesign over the existing Flask/SQLite coffee-ordering application.

The new experience includes a full-bleed editorial homepage, immersive drinks/coffee catalogs, redesigned customization, a live server-backed bag drawer, streamlined delivery/review/WhatsApp pages, a data-driven Coffee Finder, recently viewed products and a distinct compact admin workspace.

Source branch: **`feature/cafe-lux-v3-redesign`**, based on latest fetched `main` (`cb4e56c`). No automatic merge or deployment.

## Existing installation: preserve your business data

Follow [V3 upgrade instructions](docs/V3-UPGRADE.md). Back up/stop the old application, extract the new complete ZIP into a separate folder and reuse the same `CAFE_LUX_DATA_DIR`. Existing administrator accounts, catalog/photos/prices, orders, inventory, delivery areas, WhatsApp receivers and website settings remain. **Do not reseed or reprice your catalog just to install the redesign.** Schema v4 is unchanged.

On Windows, with your actual existing data path:

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\setup.bat
.\check-install.bat
.\.venv\Scripts\python.exe manage.py migration-status
.\start.bat
```

Only a fresh installation needs `.\.venv\Scripts\python.exe manage.py init-admin`. Existing IIS/ARR configuration and Waitress `127.0.0.1:8000` remain untouched. Keep your existing allowlist, including `172.18.69.59` where appropriate. [Windows guide](docs/WINDOWS.md).

## New customer features

- `/drinks` and `/coffee`: separate product collections with real categories, search, availability and independently configured prices/options.
- `/finder`: published-catalog filtering by drink/packaged type, actual hot/cold settings and configured roasts. No invented tasting or origin claims.
- Product details: galleries, valid options/exclusive extras, quantity controls and live display totals.
- Bag drawer: real server cart, live quantities/removal/counts/totals and persistent checkout access. `/cart` remains the complete fallback page.
- Checkout: actual area-fee display, clear unknown fees, final review, idempotent pending order and encoded WhatsApp click-to-chat link. Customers still must manually tap Send; opening a link is not confirmation.
- Recently viewed: six product IDs stored in the browser, with current server-side visibility/price lookup. No customer/order data in localStorage.
- Responsive navigation, keyboard focus, Arabic RTL and reduced-motion support.

## Operations workspace

Independent compact design with sidebar/density preferences, searchable product/order tables, full editors, live permission checks, order inspector/status history, stock-on-confirmation, media, content and availability controls. Revenue remains delivered product sales only. User/business values are not changed by the UI upgrade.

The previously requested explicit starter seed/sample-image/sample-price tools remain available under Catalog tools. They do not run during setup, migration or startup. See [catalog tools](docs/CATALOG-PREVIEW.md) only if you deliberately want test data.

## Development and verification

Python 3.11/3.12 recommended. No Node/frontend build or external font/API is required.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
export CAFE_LUX_DATA_DIR=/tmp/cafe-lux-v3-local
export CAFE_LUX_INSECURE_LOCAL=1
.venv/bin/python manage.py migrate
.venv/bin/python manage.py init-admin
.venv/bin/python run.py
```

Application checks: `.venv/bin/python -m pytest -q`.
Browser acceptance/screenshots: `.venv/bin/python scripts/capture_screenshots.py` (headless Chromium at `/usr/bin/chromium`, temporary synthetic data only).
Release ZIP: `.venv/bin/python scripts/build_release.py` after staging source; runtime data, venvs, secrets and logs are excluded.

See [design system](docs/V3-DESIGN-SYSTEM.md), [test report](docs/TEST-REPORT.md), [upgrade/rollback](docs/V3-UPGRADE.md), [admin guide](docs/ADMIN.md), [backups](docs/BACKUPS.md) and [PythonAnywhere guide](PYTHONANYWHERE_DEPLOYMENT.md).
