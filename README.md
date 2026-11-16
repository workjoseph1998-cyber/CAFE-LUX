# Café LUX — Premium Coffee 1.3 · Explore

A Flask/SQLite coffee-shop menu and brand discovery website with English/Arabic RTL, a clear warm menu design and the Café LUX black-and-gold identity.

**This version has no public ordering process:** no cart, checkout, purchase buttons or order submissions. Visitors browse drinks and packaged coffee, select sizes/weights to compare prices, explore product details and find the café.

## Start here

- [Version 1.3 features, verification and safe upgrade](docs/VERSION-1.3.md)
- [Windows Server 2022 setup/start/stop](docs/WINDOWS.md)
- [Administrator guide](docs/ADMIN.md)
- [First admin creation](docs/ADMIN-INITIALIZATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Backup/restore](docs/BACKUPS.md)
- [Screenshots](screenshots/)

For a new Windows installation, open PowerShell in the extracted app folder and run setup.bat, then .\.venv\Scripts\python.exe manage.py init-admin, then start.bat. New data defaults to C:\CafeLuxData. For upgrades, stop the previous app from its original folder and retain its cafe-lux.local.json/data; do not create a replacement admin.

The 19-item starter catalog and five categories remain editable. Actual prices are not invented. Unconfigured items display “Price coming soon”; configure each size/weight through Admin → Products → Edit.

## Development

Python 3.12 is recommended. Use the existing isolated cloud checkout; no worktree is needed. Set CAFE_LUX_DATA_DIR to a dedicated absolute directory outside source, create a venv, install requirements-dev.txt and run python run.py. For local HTTP session testing only, CAFE_LUX_INSECURE_LOCAL=1 disables Secure cookies; production should use HTTPS through IIS. Bind remains 127.0.0.1:8000.

Run python -m pytest -q for backend checks. Run python scripts/capture_screenshots.py for actual explore-mode Chromium acceptance (installed Chromium at /usr/bin/chromium). It uses disposable fixtures and no real customer data. Production ordering endpoints remain blocked regardless of older order settings.

## Release

python scripts/build_release.py creates dist/Cafe-LUX-Version-1.3-Explore.zip plus SHA-256. The complete source ZIP includes application, assets, Windows scripts, tests, docs and screenshots. It excludes keys, databases, runtime media, logs, local deployment configuration and virtual environments.

No deployment or IIS modification is automatic. The app belongs only to workjoseph1998-cyber/CAFE-LUX; other repositories and Cirrus data are not modified.
