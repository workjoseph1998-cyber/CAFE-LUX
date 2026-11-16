# Database and media backups

Use Admin → Overview → Download database & media backup, or:

```powershell
.\.venv\Scripts\python.exe -m flask --app cafe:create_app backup
```

Set `CAFE_LUX_DATA_DIR` to the correct dedicated directory first. Backups are written below its `backups` folder. SQLite's online backup API produces the database snapshot; JPEG uploads are included. The archive contains customer information and password hashes: restrict access, encrypt off-machine copies, and never commit or publish it. Session keys and logs are intentionally excluded.

For a consistent database-plus-media backup, pause catalog/media edits while creating the archive. Customer order writes are safe with SQLite's online backup. Keep multiple dated copies and test restoration regularly. The app does not upload backups to an external provider or automatically expire them.

## Restore (server stopped)

Disable orders, drain, stop Café LUX, then:

```powershell
.\.venv\Scripts\python.exe -m flask --app cafe:create_app restore D:\SecureBackups\CafeLUX-example.zip --confirm
```

The command validates the paths, total expanded size (max 2 GB), database integrity and schema version. It makes a safety backup before replacing the database, then copies the archived media. Only restore trusted archives produced by this application. Additional old uploads may remain on disk but are not served unless referenced by a restored media record. No files outside the dedicated storage are restored. Restore is an offline operation: do not let the web process access the database during it.

Retain your current `session.key` for ordinary restores, or remove it **while the server is stopped** to create a fresh key on the next initialization and invalidate all existing sessions. The restored database includes its administrative users, settings and audit history. Reinitialize before startup if the key was removed, and verify login, gallery images and an order after restoration.

Backup media integrity is bounded by the upload checks; a ZIP CRC check is performed by Python during extraction, and SQLite integrity is checked before replacement. This is not cryptographic proof of authenticity. Copy archives only over trusted, access-controlled channels.
