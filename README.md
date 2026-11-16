# Café LUX — Premium Coffee 1.0

A Flask / SQLite storefront with a black-and-gold editorial design, English and Arabic RTL, guest cash ordering, and an authenticated management studio at `/admin`.

This application belongs exclusively to **workjoseph1998-cyber/CAFE-LUX**. It does not access, import, configure, stop or deploy Cirrus Workplace or another repository.

## Start here

- [Windows Server 2022 installation, startup and rollback](docs/WINDOWS.md)
- [Administrator guide](docs/ADMIN.md)
- [Backup and restore](docs/BACKUPS.md)
- [Architecture and security](docs/ARCHITECTURE.md)
- [Test results and limitations](docs/TEST-REPORT.md)
- [Visual assets](docs/ASSETS.md)
- [Change log](CHANGELOG.md)
- [Actual application screenshots](screenshots/)

**No default administrator, published products, invented selling prices, address or phone number.** Ordering is disabled initially. Supply your business details, upload your artwork, create products with individually priced variants, then enable ordering. Draft example products are optional: `python -m flask --app cafe:create_app demo`. They are unpriced and unpublished.

## Development (Python 3.12)

Use the existing checkout; cloud tasks are already isolated. No Git worktree is necessary.

```bash
python3 -m venv /workspace/cafe-lux-venv
/workspace/cafe-lux-venv/bin/python -m pip install -r requirements-dev.txt
export CAFE_LUX_DATA_DIR=/workspace/cafe-lux-data
export CAFE_LUX_INSECURE_LOCAL=1 # HTTP localhost development ONLY
/workspace/cafe-lux-venv/bin/python -m flask --app cafe:create_app init-db
/workspace/cafe-lux-venv/bin/python -m flask --app cafe:create_app create-admin
/workspace/cafe-lux-venv/bin/python run.py
```

The listener is always `127.0.0.1:8000`. Use HTTPS in production. `CAFE_LUX_INSECURE_LOCAL=1` disables Secure cookies for local HTTP; Windows startup explicitly removes it. Set `CAFE_LUX_ALLOWED_HOSTS` to comma-separated public hostnames plus `127.0.0.1` in production. No schemes or ports. Default: `localhost,127.0.0.1`.

## Validate

```bash
/workspace/cafe-lux-venv/bin/python -m pytest -q
/workspace/cafe-lux-venv/bin/python scripts/capture_screenshots.py
```

The screenshot script uses installed Chromium at `/usr/bin/chromium`, a temporary database and a random temporary admin password. All example prices and customer details are explicitly **synthetic test fixtures**, never real offers. The script checks mobile layouts, checkout and admin flows before taking screenshots. No runtime database, customer data or credentials belong in the release.

## Release

`python scripts/build_release.py` packages the tracked application, documentation, tests and screenshots as `dist/Cafe-LUX-Version-1.0.zip`, with a SHA-256 checksum alongside it. Runtime data, Git metadata, virtual environments and secrets are excluded. The ZIP is a source release, not a preinstalled Windows virtual environment.

**No deployment is automatic.** Review the Windows guide and verify IIS HTTPS on your own server before enabling public orders.
