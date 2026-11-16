# Windows troubleshooting

Run from an **already-open** PowerShell/CMD terminal. Check `$LASTEXITCODE` (PowerShell) or `%ERRORLEVEL%` (CMD). Each failure shows the numbered step, subprocess output and a summary. The summary is saved to the data `logs\deployment-error.log`, or source `setup-error.log` if storage is not yet initialized. Full pip output stays in the terminal. No transcript/environment dump, passwords, keys or customer data are logged.

| Problem | Action |
|---|---|
| No supported Python | Install 64-bit CPython 3.12 (3.11/3.13 accepted), enable launcher/PATH and reopen terminal. `py -0p` lists launcher installations. |
| Explicit Python invalid | Clear stale `CAFE_LUX_PYTHON` or select a working supported executable, not a Store stub. |
| Broken/unsupported .venv | Stop Café LUX, rename only .venv to .venv.old, rerun setup. Never delete the data directory. |
| pip/ensurepip failed | Repair CPython's standard library/venv/ensurepip components. Setup uses bundled ensurepip, not an unverified download script. |
| Dependencies failed | Read the preceding pip error. Check PyPI/proxy access, architecture, disk and permissions. Do not disable TLS verification. |
| Missing requirements/manage.py/scripts | Extract the entire release ZIP. Batch files alone are insufficient. |
| Access denied / path too long | Check NTFS rights and Windows long-path policy, or extract to a shorter dedicated Café LUX folder. No source path is hardcoded. |
| Missing local JSON | Run setup. For upgrades retain/copy the previous Café LUX config or supply its original data path first. |
| Data path conflicts | A stale shell variable disagrees with saved storage. Clear it or deliberately configure storage while stopped. Setup will not silently select another database. |
| Malformed JSON | Correct/restore local JSON; UTF-8/BOM supported. Hosts are a list, cookie/proxy switches are booleans. Setup refuses to overwrite malformed configuration. |
| Missing/invalid key or database | Restore the correct Café LUX data/config or initialize a genuinely new install. Never substitute another app's files. |
| Port 8000 occupied | Inspect `Get-NetTCPConnection -State Listen -LocalPort 8000`. Stop the owner using its own procedure. No arbitrary listener is terminated. |
| Process record exists | Run this installation's stop script. Remove a stale record manually only after verifying every recorded process is gone. |
| Process identity mismatch | Possible PID reuse or wrong release/config. Inspect ownership; do not edit the record to force a kill. |
| Waitress exited/readiness failed | Inspect configured `logs\stderr.log` and `application.log`. A timed-out recorded app is left for diagnosis; stop only via verified stop script. |
| IIS Invalid host | Stop; use `manage.py configure --host ACTUAL-NAME`; start. No scheme, path or port. |
| HTTP login/cart session lost | Secure cookies need HTTPS. Local testing can explicitly opt into --local-http; restore --secure-cookies for production. |
| Admin already exists | Accounts are preserved. Use another username or authenticated admin reset. No default-password backdoor exists. |

Share the failing step and sanitized error output. Do not send session.key, passwords, databases, backups, customer data or environment dumps.

## Confirmed v1.0 defects

Mandatory data variable before setup; no saved installation config; only py -3.12 detection; unnecessary pre-set hostname requirement; accented-text readiness; first-admin auditing outside a web request. Windows virtual-environment launchers can create a serving interpreter child, so v1.1 tracks both processes. CPython source reference: https://github.com/python/cpython/blob/3.12/PC/launcher.c (run_child / VENV_REDIRECT).

No original VM error log was supplied, so no single defect is claimed as the observed failure on your VM. The uploaded working-app ZIP was inspected read-only for script-relative paths, Python discovery and ensurepip recovery. No Cirrus configuration, hosts, variables or databases were copied or modified.
