# Version 2.0 → 2.1: safe migration, updates and rollback

The shipped V2.0 base is commit `3cd9d1e`, retained in Git history. The final catalog source is published on `main`; earlier work remains in Git history while old version branches are removed as requested. No hosting reload or Windows remote deployment is performed.

## Windows upgrade

1. In your current Version 2.0 installation, disable ordering, pause admin edits/uploads, drain requests through your existing IIS procedure and run `stop.bat`. Do not stop IIS or unrelated applications.
2. Confirm the actual persistent Café LUX data path, usually `C:\CafeLuxData`. Use the old release to make a full database/media backup:

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\.venv\Scripts\python.exe manage.py backup
```

Keep that backup securely off the VM as well. Preserve the old release folder, runtime configuration, session key and dependencies. Do not copy any Cirrus database or storage.

3. Extract `Cafe-LUX-Final-Catalog.zip` to a **new** directory under `C:\Users\Administrator\Desktop\CafeLUX`. Open PowerShell there and keep the same `CAFE_LUX_DATA_DIR` environment value. Existing accounts/passwords, settings, orders and images are reused, not reinitialized.

```powershell
.\setup.bat
.\check-install.bat
.\.venv\Scripts\python.exe manage.py migration-status
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed-starter-catalog --dry-run
.\.venv\Scripts\python.exe manage.py seed-starter-catalog --confirm-data-dir "$env:CAFE_LUX_DATA_DIR"
.\start.bat
```

Do **not** recreate the existing administrator. Setup applies additive migrations automatically, backed by a pre-migration snapshot; the explicit `migrate` command is safe to repeat and verifies readiness. Seeding is a separate deliberate step, never part of setup. Review any conflict report rather than overwriting records.

4. Visit `http://127.0.0.1:8000/admin`, then `http://172.18.69.59/admin` through the unchanged IIS binding. Verify 18 new draft drinks/four new draft coffees when there were no name conflicts, enabled route/host settings, persisted accounts/orders/photos, independent variant editing and mobile storefront empty states. Use real reviewed information before publishing.

The existing runtime.json is never replaced. Ensure its `CAFE_LUX_ALLOWED_HOSTS` includes `localhost,127.0.0.1,172.18.69.59`, or use your existing equivalent environment value. No wildcard is needed. Start stays at `127.0.0.1:8000`. `CAFE_LUX_INSECURE_LOCAL=1` is for the current internal HTTP VM test; future public HTTPS must use secure cookies.

## If your old database is inside an application folder

Do not delete or overwrite that folder. Stop the old application and inspect its actual configured SQLite path and upload directory. Create a consistent SQLite backup with the old application's backup command or Python's SQLite backup API; do not copy a live SQLite file without accounting for journals/WAL. Copy the backup and uploaded photos to a **new, separate** persistent directory, retaining filenames and the installation session key where available. Preserve the untouched old directory and a full backup first. Verify the copied database with `PRAGMA integrity_check` and confirm users/products/orders before pointing Version 2.1 at it. Never run new setup against an ambiguous or unrelated database.

If the new data directory already contains any business data, do not overwrite it during this relocation. Resolve which dataset is authoritative before combining anything; this release does not merge private databases automatically.

## Schema v4

The baseline v1 schema and v2/v3 migrations remain supported. Migration v4 adds nullable stable seed identifiers, variant SKU/order fields, a pending-extra-price flag, unique/indexed starter identities and a seed ledger. It does not drop/rebuild tables, reset prices/passwords, change order snapshots or delete uploads. Legacy v3 records receive only default/NULL values in new columns.

Before an existing database changes schema, the application verifies connectivity/integrity and writes a unique online SQLite snapshot below `data/backups/pre-migration-vN-*.sqlite3`. It reopens that snapshot, copies it into an in-memory database and checks integrity/table counts. Failure stops migration. Newer-than-supported database versions are refused. `migration-status` reads the current version without applying migrations. The starter seed similarly verifies a unique pre-seed database snapshot before writes.

Normal startup retains V2.0's additive initialization behavior; therefore an old database must be backed up before first launching new code, not merely before running a later CLI command. Automatic snapshots are additional protection. Full backup ZIPs include media; raw safety snapshots are database-only because migration/seeding never touch media.

## Future updates

Review feature branch → approve/merge to main → pause/drain → `manage.py prepare-update` (verified full backup) → manually update code/dependencies → `manage.py migration-status` → `manage.py migrate` → manual start/reload → verify. `prepare-update`, `backup` and `migration-status` do not automatically migrate existing data. Never install synthetic test fixtures over a business database. PythonAnywhere instructions are in `PYTHONANYWHERE_DEPLOYMENT.md`.

## Rollback

Drain and stop the new release. Preserve a current backup if any new business data was entered. Run the previous release with the matching **pre-upgrade** full database/media backup, restored using its own documented offline restore command. A pre-upgrade restore excludes new orders created since the snapshot; reconcile those before rollback. Do not downgrade schema in place or run old code against v4. Keep Git history intact; no force-push/reset of shared branches is needed.

For emergency database-only recovery from a verified raw snapshot, stop all app processes, preserve the current database separately, and copy the selected snapshot to the configured `cafe.sqlite3` path; media is unchanged by migration/seeding. Reopen and verify it with the matching release before resuming.


For an existing V2.1 installation, V2.1.1 keeps schema v4. Reuse the same data directory/account, update the source and run setup normally. Do not seed again just for images. Open Admin → Catalog preview → Add sample images & descriptions; see `CATALOG-PREVIEW.md`. This one-click action backs up first and fills only missing seeded content.
