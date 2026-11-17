# Café LUX — Version 2.0

Mobile-first, cream-and-espresso coffee storefront and protected administration. Python 3.11+, Flask, SQLite, Pillow and Waitress; no frontend build or paid messaging service.

## Windows Server 2022: local VM first

1. Extract `Cafe-LUX-Version-2.0-Windows.zip` into a new folder under `C:\Users\Administrator\Desktop\CafeLUX`. Do not overwrite your previous release.
2. Install Python 3.11+ with the Python launcher.
3. Open PowerShell in the extracted application folder. Run:

```powershell
.\setup.bat
.\check-install.bat
.\.venv\Scripts\python.exe manage.py init-admin
.\start.bat
```

4. Visit `http://127.0.0.1:8000`, then `/admin`.
5. Add real product images, publish products with individually priced variants, configure WhatsApp receivers and delivery areas, set store hours, then enable ordering.
6. Configure your existing IIS hostname in `C:\CafeLuxData\runtime.json` and restart. See [Windows guide](docs/WINDOWS.md).

`stop.bat` stops only the recorded Café LUX process. It does not modify IIS, Cirrus Workplace, or other Python processes. No public deployment is performed.

## Persistent data

Windows defaults to `C:\CafeLuxData`; override with `CAFE_LUX_DATA_DIR`. SQLite, uploads, logs, backups, runtime configuration and session keys stay outside source. Setup applies additive migrations and never seeds business data or resets records. Back up before any upgrade. No default password exists.

## Ordering

Browse `/drinks` or `/coffee` → configure products → mixed cart → delivery details → final review → save pending submission → open WhatsApp → manually tap **Send**. Cash on delivery only. Pending orders do not count as sales or deduct stock. Staff explicitly confirm receipt and status. Stock is deducted under a database lock on confirmation and restored once on cancellation.

Each delivery area uses its assigned active receiver, falling back to the active default. No receiver or configured delivery area means checkout is unavailable. Unknown delivery fees never produce a claimed final payable total. Admin customer-notification links also require a manual WhatsApp Send.

Admins manage products, independent weights, size-specific temperature/grind restrictions, exclusive extra groups, stock, images, content, delivery fees, time slots, closures and contact visibility. Operators have order-only management access. Prepared links are not proof of message receipt.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
export CAFE_LUX_DATA_DIR=/tmp/cafe-lux-local
export CAFE_LUX_INSECURE_LOCAL=1
.venv/bin/python manage.py init-admin
.venv/bin/python run.py
```

Use a dedicated absolute data directory outside the checkout. The listener is always `127.0.0.1:8000`; debug is disabled. Tests: `.venv/bin/python -m pytest -q`. Browser checks and screenshots: `.venv/bin/python scripts/capture_screenshots.py` (Chromium at `/usr/bin/chromium`, disposable fixtures only).

See [administration](docs/ADMIN.md), [architecture](docs/ARCHITECTURE.md), [backups](docs/BACKUPS.md), [migration and rollback](docs/MIGRATION.md), [test report](docs/TEST-REPORT.md), and [asset notes](docs/ASSETS.md).
