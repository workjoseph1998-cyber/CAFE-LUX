# Café LUX — Version 2.1

The existing luxury cream-and-brown mobile storefront, with an approved **draft-only starter catalog**, compact laptop administration and portable Flask WSGI hosting. Same Python/Flask/SQLite source on Windows Server and PythonAnywhere. No public deployment is performed.

## Existing Windows Server: safe upgrade first

Back up and stop Version 2.0, then extract Version 2.1 into a separate new folder. Keep the same dedicated `CAFE_LUX_DATA_DIR`; never replace its database/uploads or recreate your existing admin account. Follow [migration and rollback](docs/MIGRATION.md).

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\setup.bat
.\check-install.bat
.\.venv\Scripts\python.exe manage.py migration-status
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed-starter-catalog --dry-run
.\.venv\Scripts\python.exe manage.py seed-starter-catalog --confirm-data-dir "$env:CAFE_LUX_DATA_DIR"
.\start.bat
```

Only on a **fresh installation** without an administrator, run `.\.venv\Scripts\python.exe manage.py init-admin` before starting. No default credentials exist.

Waitress remains at `127.0.0.1:8000`; existing IIS/ARR and the `172.18.69.59:80` binding are unchanged. Include `localhost,127.0.0.1,172.18.69.59` in your existing allowed-host setting. Scripts preserve runtime.json and stop only the recorded Café LUX process. See [Windows instructions](docs/WINDOWS.md).

## Approved starter catalog

- Four drink categories with **18 draft drinks**.
- **Four draft coffees:** LUX Lebanese Blend, LUX Signature Blend, LUX Espresso Roast and LUX Golden Roast.
- Independent **200 g, 500 g and 1 kg** whole-bean/ground/preparation combinations.
- Appropriate serving sizes, editable milk, sugar, strength and syrup options.

Seeding is explicit, repeatable and never runs at startup/setup. New products have no selling prices, stock or assigned photos and remain unpublished. Extras remain disabled with a pending-price marker until reviewed. Stable identities preserve admin edits/removals; similar names are reported, never silently merged. Each actual seed run creates a verified safety snapshot. See [catalog rules and publishing](docs/STARTER-CATALOG.md).

## Compact business administration

Separate Drinks and Beans & Ground Coffee tables; draft/published/search/category filters, sorting, pagination, thumbnails and missing-data indicators. Collapsible sidebar and density preferences persist in your browser. The editor includes per-variant prices/stock/SKU/order, real-photo upload, customization, persistent Save/Publish controls and unsaved-change warnings. Publication checks apply to editor, quick and bulk actions alike. Orders use a compact table and optional detail panel; permissions remain enforced server-side.

The public storefront design is unchanged. Draft products remain private. Mixed carts, server-side pricing, final delivery review, WhatsApp routing, availability and stock-on-confirmation behavior remain intact. Opening WhatsApp never proves submission or receipt; customers and staff must manually tap Send.

## PythonAnywhere, later

Follow [PYTHONANYWHERE_DEPLOYMENT.md](PYTHONANYWHERE_DEPLOYMENT.md) after approving/merging the code. Root `wsgi.py` exports the actual Flask application; it does not start Waitress. Production configuration examples are in `config/`. Windows and Linux have separate persistent data directories. No customer-data synchronization, paid messaging API, background worker or scheduled task is required.

## Development and verification

Python 3.11 or 3.12 recommended; no Node build is required.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
export CAFE_LUX_DATA_DIR=/tmp/cafe-lux-local
export CAFE_LUX_INSECURE_LOCAL=1
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed-starter-catalog --dry-run
.venv/bin/python manage.py seed-starter-catalog --confirm-data-dir "$CAFE_LUX_DATA_DIR"
.venv/bin/python manage.py init-admin
.venv/bin/python run.py
```

Tests: `.venv/bin/python -m pytest -q`. Browser checks/screenshots: `.venv/bin/python scripts/capture_screenshots.py` with Chromium at `/usr/bin/chromium`. All browser fixtures are temporary synthetic data. Build the complete source release using `.venv/bin/python scripts/build_release.py` after staging source; generated ZIPs remain outside tracked source under `dist/`.

See [admin guide](docs/ADMIN.md), [architecture](docs/ARCHITECTURE.md), [backups](docs/BACKUPS.md), [test report](docs/TEST-REPORT.md) and [asset notes](docs/ASSETS.md). No Windows VM, IIS or PythonAnywhere execution is claimed by Linux checks.
