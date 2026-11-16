# Windows Server 2022 — installation and rollback

## Isolation and prerequisites

Install Python **3.12 x64** including the `py` launcher. Use a dedicated Windows service/operator identity. Extract the release to a new, versioned directory, for example `D:\CafeLUX\releases\1.0`. Use separate persistent storage such as `D:\CafeLUXData` containing the database, uploads, logs, backups and session key. Do not place it in the release folder, IIS web root, another application's directory or a shared data directory.

The scripts never modify IIS or kill an existing application. Python rejects source-contained data, directories containing `Cirrus`, and any overlap with explicitly protected directories. Windows scripts perform the same checks. List every other application's real storage/app path in `CAFE_LUX_PROTECTED_DIRS` (semicolon-separated). Junctions should not be used for application/data directories. Python resolves actual filesystem paths before allowing storage.

In PowerShell, replace the hostname and protected paths with your actual values:

```powershell
$env:CAFE_LUX_DATA_DIR = 'D:\CafeLUXData'
$env:CAFE_LUX_ALLOWED_HOSTS = 'your-real-domain.example,127.0.0.1'
$env:CAFE_LUX_PROTECTED_DIRS = 'D:\ActualPreviousApplication;D:\ActualPreviousData'
cd D:\CafeLUX\releases\1.0
.\setup.bat
.\.venv\Scripts\python.exe -m flask --app cafe:create_app create-admin
```

Enter the administrator username and a unique password (12+ characters) interactively; no default credentials exist. Do not paste passwords into scripts. Re-running setup preserves the database and applies additive schema migrations (v1 → v2). Use the same environment variables for every setup, backup, start and stop invocation; persist them for the dedicated operator account using Windows environment settings if desired.

Restrict NTFS access on the data directory and release directory to the dedicated operator/service account and trusted administrators. Remove inherited access for unrelated users after reviewing the ACL with your Windows administrator. In particular protect `session.key`, backups and database files. The web server must not serve the data directory directly.

## IIS contract (manual review only)

Use your existing reverse proxy to `http://127.0.0.1:8000`. Leave its bindings and existing application installations intact. Confirm:

- Public HTTPS certificate and binding are correct; redirect public HTTP to HTTPS in IIS.
- Preserve the original Host header, and include that hostname in `CAFE_LUX_ALLOWED_HOSTS`.
- IIS **overwrites**, rather than appends or trusts, `X-Forwarded-Proto` with the original connection scheme. `start.bat` enables trust of exactly one forwarded scheme indication.
- Do not expose port 8000 externally. Waitress binds loopback only.
- Forwarded client-IP headers are deliberately **not trusted**. The persistent login limiter uses the loopback proxy IP, so five failed logins can temporarily limit admin login for all users. It cannot be bypassed by submitting fake `X-Forwarded-For` headers.
- Secure, HttpOnly, SameSite=Lax cookies use the distinct name `cafe_lux_session`.
- IIS request size/time limits permit up to 8 MB uploads. The application also enforces its own size limit.

No automatic ARR, URL Rewrite, firewall, certificate or IIS installation is attempted.

## Start

Stop your previous application yourself. Then, in the configured PowerShell session:

```powershell
.\start.bat
```

Startup refuses an occupied port, missing initialized data/session key, missing allowed host configuration or an existing process record. It records the exact new process identity and checks the homepage. If it fails, inspect `D:\CafeLUXData\logs\stderr.log` and `application.log`.

Visit your real **HTTPS** hostname, sign in at `/admin`, configure business content and test a synthetic cash order before accepting public orders. No card payments are taken. A successful order page means stored, not accepted by staff; confirm in the orders dashboard.

For boot automation, create a Windows Scheduled Task under the dedicated identity with the same environment and working directory. Scheduling/service installation is a manual operator step; this release does not install a service or assume processes survive reboot.

## Stop safely

1. Disable order acceptance in `/admin` → Website & settings.
2. Drain public requests using your existing IIS maintenance procedure. Wait for active requests and admin writes/uploads to finish.
3. Run `stop.bat` from the same release with the same data directory.

The script checks PID, start timestamp, executable, application root and command line before stopping the recorded process. It never stops a process by port or name. On Windows, `Stop-Process` is a forced process exit, **not a graceful Waitress drain**; the manual drain is essential. SQLite transactions protect against partial orders. Back up before maintenance. If a record is stale and identity checks fail, inspect it and remove `server-process.json` manually only after verifying the recorded process is no longer this server.

## Upgrade and rollback

1. Disable orders, drain requests, stop only Café LUX.
2. Back up the database and media; retain the previous release and its dependencies.
3. Extract the new release to a separate versioned directory. Use the same dedicated data directory, run setup, start, then verify HTTPS/login/products/order flow.
4. If validation fails, stop the new release. Restore the matching pre-upgrade data backup using the old release's restore command, then start the old release.
5. To return to your former non-Café-LUX application, stop Café LUX and start that application using its own existing procedure. Neither its files nor its database were changed.

Do not run two applications on port 8000. Do not copy one application's database or session key over another application's storage. No automatic deployment or rollback is performed.

## Validation boundary

Linux cloud checks validate application behavior and the Python port conflict guard. PowerShell execution, Windows process identity inspection, NTFS ACLs, reboot behavior and your actual IIS headers/TLS must be validated on Windows before production. No Windows execution or IIS deployment is claimed by this release.
