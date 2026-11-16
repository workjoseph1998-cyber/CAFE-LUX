# Actual Windows Server 2022 VM acceptance

Cloud/CI results do not establish your local IIS/permissions. Perform these steps before calling the release VM-tested:

1. Stop the old application using its own procedure. Keep its files/backups. Confirm 8000 is free.
2. Extract the entire v1.1 ZIP and retain v1.0. Retain existing Café LUX data/config; a new install defaults to C:\CafeLuxData.
3. Open PowerShell in the source folder; run setup.bat. Expect six successful steps and exit 0.
4. Run `.\.venv\Scripts\python.exe manage.py init-admin`. Create a unique account interactively.
5. Run setup again; confirm accounts, content and uploads remain.
6. Run start.bat; expect PID-verified readiness. Browse http://127.0.0.1:8000 on the VM.
7. Browse your existing HTTPS IIS URL. Configure its actual hostname if Host validation rejects it. Confirm admin login persists.
8. Add a clearly labeled synthetic product/price through admin; verify variant/add-on cart pricing, cash checkout and the stored order. Cancel/anonymize synthetic customer details afterward.
9. Start again; expect refusal while the existing site stays available.
10. Disable orders, drain requests and stop. Confirm Café LUX releases 8000 and IIS/unrelated processes remain intact. Repeated stop is safe.
11. Restart, verify data/login, create a backup and review NTFS restrictions before public ordering.

Share the numbered failing step and sanitized error if anything fails. Never send passwords, keys, databases, backups or customer information. No remote access or automatic deployment to your VM has occurred.
