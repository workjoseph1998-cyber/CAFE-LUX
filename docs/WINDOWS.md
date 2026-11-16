# Cafe LUX 1.1 — Windows Server 2022

The website and schema v2 are unchanged. The original v1.0 remains on branch `feature/cafe-lux-v1`, commit `5720b71a867a0507e390ba4a5850e7ee635d9543`. The fix is on `fix/windows-setup-v1.1`. No IIS change or deployment is automatic.

## Run from an open PowerShell terminal

Extract the **complete** `Cafe-LUX-Version-1.1-Windows-Fix.zip` into the application folder, retaining the previous release for rollback. Your existing folder is supported:

```powershell
cd "C:\Users\Administrator\Desktop\CafeLUX\CAFE-LUX-feature-cafe-lux-v1\CAFE-LUX-feature-cafe-lux-v1"
.\setup.bat
.\.venv\Scripts\python.exe manage.py init-admin
.\start.bat
```

If extracted elsewhere, use that folder instead. In CMD, use `cd /d "path"`, then `setup.bat`. Scripts use their own location, not the caller's working directory. Paths with spaces, Unicode and nested folders are supported; Windows MAX_PATH policies can still impose limits.

Install 64-bit CPython **3.12** if missing; 3.11 and 3.13 are accepted too. The scripts discover the Windows `py` launcher or PATH executables. No Python installation path is hardcoded. `CAFE_LUX_PYTHON` can optionally specify a known executable. Unsupported/broken Python produces a meaningful error before modifying data.

Setup prints six steps: virtual environment, saved configuration/storage, pip/dependencies, compatibility, schema initialization/migration, application/database verification. Missing pip is bootstrapped through Python's bundled `ensurepip`. Repeated setup preserves database, accounts, orders, uploads and session key. Failures return nonzero; keep the terminal open to see the exact output.

## Data and persistent configuration

New installations default to `C:\CafeLuxData`. No environment variable is required for a new Windows setup. It contains `cafe.sqlite3`, `session.key`, `uploads`, `logs` and `backups`. The generated, non-secret `cafe-lux.local.json` beside `manage.py` remembers storage, host validation, proxy and cookie settings across terminals. It is excluded from Git/ZIPs.

For a custom path **before first setup**:

```powershell
$env:CAFE_LUX_DATA_DIR = 'D:\CafeLuxData'
.\setup.bat
```

For an existing installation, retain its original Café LUX data directory. Copy its local JSON when using a new release folder, or supply the existing data path before setup. A saved path conflicting with a shell variable causes setup to refuse a silent database switch. Process variables take precedence at runtime; clear stale overrides.

To deliberately select another path while stopped: `python manage.py configure --data-dir "absolute path"`. This does not move/overwrite data. Back up and migrate files separately if changing storage. No `CIRRUS_*` variables are used.

Optional `CAFE_LUX_PROTECTED_DIRS` lists other apps' real source/data directories, semicolon-separated. Setup refuses overlap with source/protected paths or paths containing Cirrus; Python resolves actual paths/junctions. Restrict NTFS access to the dedicated operator/service identity and trusted administrators. Keep runtime data/backups outside the IIS web root and SQLite on local disk.

## Administrator initialization

`.\.venv\Scripts\python.exe manage.py init-admin` prompts for a new username and a unique password of 12+ characters twice. There is no default password. Existing usernames are not overwritten. See [ADMIN-INITIALIZATION.md](ADMIN-INITIALIZATION.md). V1.1 fixes the original CLI audit logging bug that incorrectly required a web session.

## Existing IIS proxy and cookies

`start.bat` binds Waitress exclusively to `127.0.0.1:8000`, refuses occupied ports/duplicate records, and checks `/healthz` JSON against the owned serving PID. It never frees a port by killing another process.

Browse `http://127.0.0.1:8000` on the VM. For production admin/cart/checkout, use your existing **HTTPS IIS URL** because default cookies are Secure.

If IIS preserves the public Host header and you see **Invalid host**, configure the actual hostname/IP in the app (no scheme, port or path):

```powershell
.\stop.bat
.\.venv\Scripts\python.exe manage.py configure --host your-actual-hostname.example
.\start.bat
```

Repeat `--host` for multiple public names; loopback hosts remain allowed. This is application configuration; no IIS rewrite/binding change is normally needed. No IP/address from another app is silently copied.

The saved default trusts one forwarded scheme indication. IIS must overwrite `X-Forwarded-Proto` with the original scheme. Forwarded Host/client-IP claims are not trusted. No IIS edit is needed if the existing proxy already supplies the correct scheme.

For isolated **local HTTP testing only**, stop and run `manage.py configure --local-http`, then start. This disables Secure cookies for the installation; restore `--secure-cookies` before public use. An HTTP-only IIS URL is a real security compatibility decision: production sessions require HTTPS.

## Stop and rollback

Disable orders and drain active requests through your normal IIS maintenance procedure before `stop.bat`. The script verifies root, executable, command line, PID and creation timestamp for the venv launcher and serving interpreter child. Concurrent start/stop commands are locked. PID reuse/unknown ownership fails closed; no other Python process or IIS is stopped.

Windows process termination is not a graceful request drain, so drain first. A background process is not an installed Windows service. Boot scheduling/service installation remains a manual operator task.

For rollback, stop Café LUX, retain current data and back up database/media. Restore the previous source and its configuration (or supply its old data path for v1.0), then start only one app on 8000. Schema v2 is unchanged. Restore older business data only intentionally using [BACKUPS.md](BACKUPS.md). Other applications' files/data were never modified.

Follow [VM-CHECKLIST.md](VM-CHECKLIST.md) on your actual VM. CI/cloud results do not prove your IIS headers, certificate, permissions or installed Python work.
