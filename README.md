# Café LUX — Version 4.0

**Quiet Ritual** is the current development release: a mobile-first porcelain/forest storefront and matching operations workspace, built on the existing Flask/SQLite application.

Optional customer accounts, favorites, saved profiles/addresses, private order history, reordering, bundles, promotion codes, inventory movements, website drafts/publishing and reports are persistent features. Guest checkout and cash on delivery remain available. Official Meta WhatsApp integration uses signed incoming webhooks and a durable worker; only **Confirmed** and **Out for Delivery** can generate automatic notification jobs.

**Review branch:** `feature/cafe-lux-v4`, based on verified V3 merged into `main` at `de65594`. Live deployment, final merge/release and destructive remote cleanup are separate approval steps. No production database or hosting configuration is modified by this source release.

## Install or upgrade

Read [installation, migration and rollback](docs/V4-UPGRADE.md) before running setup against existing data. Schema **5** adds tables/columns; verified SQLite snapshots precede existing-database migrations. Reuse the actual external `CAFE_LUX_DATA_DIR`, uploads and existing accounts. Never seed, publish samples, reset prices or recreate administrators to upgrade.

Windows (use your real existing persistent directory):

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\setup.bat
.\check-install.bat
.\.venv\Scripts\python.exe manage.py migration-status
.\start.bat
```

Fresh installations only: `.\.venv\Scripts\python.exe manage.py init-admin`. Waitress remains bound to `127.0.0.1:8000`; preserve your existing IIS/ARR configuration and host allowlist. See [Windows](docs/WINDOWS.md) and [PythonAnywhere](PYTHONANYWHERE_DEPLOYMENT.md).

## WhatsApp setup

Automation starts **disabled**. See [Meta setup, templates, worker and hosting requirements](docs/WHATSAPP.md) and [environment example](config/v4.env.example). Tokens live only in environment variables. No `.env` file is loaded automatically.

Customers manually tap **Send** in WhatsApp. A correctly signed incoming webhook must also match order reference, sender, receiving business phone and timestamp before marking an order Received. Staff still confirm orders. Invalid/ambiguous matches enter manual review. Official approved English/Arabic templates and explicit per-order consent are required for automatic updates. Mock jobs are labeled `mocked`, never sent/delivered.

PythonAnywhere free hosting can run the manual click-to-chat flow, but reliable live automation needs permitted Meta outbound HTTPS and a continuously running worker. No live credentials, template approval, business-phone onboarding or external message-delivery verification is included in the local test results.

## Operations and privacy

[Admin guide](docs/ADMIN.md), [architecture/security](docs/ARCHITECTURE.md), [backups](docs/BACKUPS.md), [testing](docs/TEST-REPORT.md), [design](docs/V4-DESIGN-SYSTEM.md), [GitHub inventory](docs/GITHUB-V4.md).

Customers use separate identities from staff. Recovery uses three one-use codes shown once at registration; there is no pretend email-delivery service. Guest orders are never attached to accounts by phone. Customers can withdraw WhatsApp consent. Admins can manage account access and remove saved private information.

Delivered **gross product sales** retain their historical definition (subtotal, excluding delivery). Reports show discounts/net separately and never combine currencies. Gross profit is unavailable whenever any required historical cost is missing.

Catalog seed/sample-image/sample-price tools remain explicit optional actions under Catalog Tools; they never run during setup or migration. [Catalog tools](docs/CATALOG-PREVIEW.md).

## Development

Python 3.11/3.12 recommended. No frontend build, external fonts or third-party browser scripts.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
export CAFE_LUX_DATA_DIR=/tmp/cafe-lux-v4-local
export CAFE_LUX_INSECURE_LOCAL=1
.venv/bin/python manage.py migrate
.venv/bin/python manage.py init-admin
.venv/bin/python run.py
```

Run `.venv/bin/python -m pytest -q`, then `.venv/bin/python scripts/capture_screenshots.py` and `.venv/bin/python scripts/check_v4_browser.py` with Chromium/Playwright available. All tests use disposable data and forbid real Meta sends. Build the complete tracked source ZIP using `.venv/bin/python scripts/build_release.py` after staging release files. ZIPs and SHA-256 checksums appear under `dist/`; runtime data and secrets are excluded.
