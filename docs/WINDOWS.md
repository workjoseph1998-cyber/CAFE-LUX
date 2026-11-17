# Windows Server 2022 — local installation

Use Python 3.11 or newer. Extract to a new directory, including paths with spaces or nested folders. Every batch launcher uses `%~dp0`; PowerShell scripts discover their parent directory. There is no hardcoded previous release path.

Run `setup.bat`, `check-install.bat`, `.\.venv\Scripts\python.exe manage.py init-admin`, then `start.bat`. Setup detects a supported Python interpreter, creates `.venv`, installs requirements and applies schema migrations. Repeated setup preserves all records and uploads. Admin setup prompts for a unique password of at least 12 characters; none is bundled.

## Dedicated storage

The default is `C:\CafeLuxData`. Set `CAFE_LUX_DATA_DIR` before setup to use a different absolute directory. Use the same value on every later invocation. Never use Cirrus Workplace storage, a source subdirectory, or a network share. Protect this directory and the source directory with NTFS permissions limited to the dedicated operator and trusted administrators. `CAFE_LUX_PROTECTED_DIRS` can additionally list unrelated applications (semicolon-separated).

Setup creates `runtime.json` under the data directory. It defaults to allowed hosts `localhost,127.0.0.1` and `CAFE_LUX_INSECURE_LOCAL=1`, allowing cookies on the requested local HTTP test URL. The scripts read these values on each invocation; process environment variables take precedence. Python management commands use the Windows data default or `CAFE_LUX_DATA_DIR`.

## Existing IIS / ARR

Waitress always listens at `127.0.0.1:8000`. Existing IIS reverse proxy configuration is left untouched. Add your actual IIS hostname to the comma-separated `CAFE_LUX_ALLOWED_HOSTS` value in runtime.json and restart before testing through that hostname. IIS must preserve the Host header. No firewall, binding, certificate or other application is changed.

For any later HTTPS use, set `CAFE_LUX_INSECURE_LOCAL` to `0`, keep HTTPS end to end at the browser, and configure IIS to overwrite `X-Forwarded-Proto` with the actual scheme. Start enables trust of one scheme proxy only. Forwarded client IP headers are not trusted. The login/checkout limiter therefore shares the proxy IP across visitors; this conservative choice avoids spoofable headers.

## Diagnostic behavior

`check-install.bat` checks Python, venv, pip dependency consistency, application import, SQLite integrity, schema version, configuration and writable upload/log/backup directories. It reports port 8000 as available or occupied. Port occupancy is informational in diagnostics because a healthy running Café LUX also owns it. `start.bat` refuses any occupied port, missing initialized data, missing venv, or existing process record; it never kills the owner. Inspect data/logs on failure. The Python entry point independently checks the port.

The process record contains PID, creation timestamp, interpreter and installation root. `stop.bat` verifies these and the command line before stopping that process. It never stops by process name or port and never stops IIS. For stale records inspect the actual process and remove the record manually only after verifying it is stale.

Disable ordering and drain active IIS requests before stopping. Windows Stop-Process is forced termination, not a graceful Waitress drain. Back up before maintenance. Restart/scheduled-task registration is deliberately manual.

## VM acceptance checklist

Run setup twice; run diagnostics; create admin; start; verify local homepage, both catalogs, configured extras/weights, mixed cart, delivery review and pending WhatsApp message. Test admin stock confirmation and image upload, stop/restart and persistence. Verify the existing IIS URL after adding its hostname. Check occupied-port refusal and that stop affects only Café LUX. No Windows VM execution is claimed from Linux development checks.
