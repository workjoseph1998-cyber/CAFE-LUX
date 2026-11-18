# V4 installation, migration and rollback

V4 source is reviewed on `feature/cafe-lux-v4`. Do not deploy the live site until approved. Existing V3 source is preserved at commit `4aaa7fde15bcb41c1e0d90446fe53aa70aeae4af`; main's verified V3 merge is `de65594d21df274f1e7e29b6fd1e6184c772ebd7`. A complete pre-V4 Git bundle was verified separately. Git backup is not a production-data backup.

## Existing installation

1. Identify the actual external `CAFE_LUX_DATA_DIR` and verify products, orders, uploads and administrator account before changing anything. Never point setup at an ambiguous/other application's directory. Preserve session.key and runtime.json privately.
2. Disable ordering, pause staff edits/uploads, drain requests and stop only Café LUX web/worker processes. Leave IIS and unrelated applications alone. Run the **old release's** `python manage.py backup`; preserve the ZIP and original source/virtualenv. Verify the ZIP checksum/CRC and reopened SQLite `PRAGMA integrity_check`. Back up hosting/service environment configuration separately, without committing secrets.
3. Extract `Cafe-LUX-Version-4.0-Quiet-Ritual.zip` into a new source directory. Keep the persistent directory outside both source folders. Retain the original production data and backup; test the upgrade on a separate restored copy first.
4. Create a fresh virtualenv and install requirements (Windows `setup.bat` handles this). Export the same `CAFE_LUX_DATA_DIR`, trusted hosts/proxy settings. Inspect `python manage.py migration-status` before `python manage.py migrate`. Setup also initializes/migrates. Do not run initialization concurrently with web/worker processes.
5. Schema 5 is additive over schema 4: separate customers/recovery/addresses/favorites, promotions/bundles, inventory movements, website drafts, WhatsApp inbox/jobs/events, and order consent/account/discount fields. Existing product IDs, media references, prices, staff hashes, receivers, area rules, settings and order snapshots remain. Existing customers start empty; no guest-order ownership is inferred. Existing orders have no WhatsApp consent and generate no retroactive jobs.
6. Migration automatically takes a unique verified **database-only** snapshot before upgrading an existing schema. It does not replace the full data/media backup. A failed new schema transaction rolls back; a newer/unrecognized database is rejected.
7. Run `check-install.bat` or CLI diagnostics, inspect catalog/images, admin sign-in, ordering availability and a local test review. Do not send real WhatsApp messages during verification. Retain currency/stock/receiver settings; no starter tools run automatically.
8. Resume only the selected release. Hard refresh CSS/JS. Enable live WhatsApp separately only after the Meta/hosting checklist is satisfied. Never run two release versions against the same SQLite database or two listeners on port 8000.

Windows preserves Waitress `127.0.0.1:8000`, existing IIS/ARR and host allowlist (including `172.18.69.59` if used). PythonAnywhere retains `wsgi.py`, `/static` mapping and external media. See deployment-specific guides.

## New installation

Use a new, dedicated external directory, install dependencies, run `manage.py migrate` and `manage.py init-admin`. Configure real catalog/area/receiver/hours through admin. Ordering and automation are off until configured. Sample catalog/content/prices require separate explicit actions and are not business facts.

## Rollback

V3 deliberately refuses schema 5. **Do not point V3 at the upgraded database or drop V4 columns/tables.** Pause/drain and stop V4 web and worker. Make a full V4 backup first, including orders/accounts received after upgrade. Restore the verified pre-upgrade database/media into a separate external directory, restore the matching V3 source/virtualenv and session/runtime settings, and verify counts, images and authentication before switching the configured data path. Use the matching release's restore command, while stopped.

Restoring an old snapshot discards subsequent writes from that restored view. Reconcile new orders, stock movements and account changes offline before reopening; never silently discard them. Keep both backups and directories until reconciliation is approved. The V4 `restore --confirm` command accepts trusted schema 2/3/4/5 backups, takes a safety backup, and requires restarting/migrating before serving. Do not restore over a running worker or website.
