# V3.0 review and manual upgrade

V3 is on `feature/cafe-lux-v3-redesign`; `main` and the live website are not modified. Review the source/screenshots and approve merging separately. Windows/IIS and PythonAnywhere deployment remain manual.

## Data compatibility

The database remains at **schema v4**. V3 adds no schema migration, catalog seed, price replacement, credential reset or uploaded-image conversion. Existing users/orders/settings/stock/routing/areas/slots are retained. The only order snapshot addition is the current product-image reference used to render the bag; existing order records are never rewritten.

New `/finder` and `/recently-viewed` routes are read-only public catalog views. Availability labels derive from actual hours, order pause/configuration, active receivers/areas and slots. Checkout revalidates on the server exactly as before; the display does not authorize orders.

## Windows Server 2022

1. Using the running release's established data directory, pause orders/admin edits, drain requests and make a full backup (`manage.py backup` or `prepare-update`). Stop only Café LUX with its existing stop script.
2. Extract `Cafe-LUX-Version-3.0-Espresso-Editorial.zip` into a new installation directory. Keep `CAFE_LUX_DATA_DIR` pointed at the same dedicated directory and preserve runtime.json/session.key/uploads.
3. Run `setup.bat`, `check-install.bat`, and `manage.py migration-status` with the dedicated virtualenv. Do not create another admin or rerun catalog publication to install a redesign. Existing schema v4 needs no change; earlier schemas still use the existing verified additive migrations.
4. Run `start.bat` and test `http://127.0.0.1:8000`, then the unchanged existing IIS URL/allowed host. Waitress still binds loopback port 8000. No IIS/ARR bindings or unrelated applications are changed.
5. Verify real products/images/prices, product choices, the drawer and full cart, real area fees, review/WhatsApp pending submission, login, order status/stock and media editing. Hard-refresh CSS/JS after an upgrade to clear old browser assets.

## PythonAnywhere

The real `wsgi.py` factory entry point and production dependencies are unchanged. Follow `PYTHONANYWHERE_DEPLOYMENT.md` after approval. Back up, update the approved source/dependencies, check migration status, reload manually and verify. `/static/` still maps to `cafe/static`; registered uploads remain served from the separate data directory through `/media/`. The drawer and discovery features use same-origin requests and need no outbound API or worker.

## Rollback

Pause/drain and stop the new release. Since V3 retains schema v4, the previous final release can use the same data after normal backups and compatibility verification. If restoring any pre-upgrade backup, retain the current data first and reconcile orders created since the snapshot; a backup restore discards later writes. Do not replace business data with fixtures. Never run two releases on port 8000 or against the same data simultaneously.

Linux tests do not certify your Windows process manager, IIS headers/permissions, actual mobile devices or PythonAnywhere account. Validate those environments before live use. No hosting deployment was performed.
