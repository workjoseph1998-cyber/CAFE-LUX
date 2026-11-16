# First administrator — Windows 1.1

After setup.bat succeeds, in the app folder:

```powershell
.\.venv\Scripts\python.exe manage.py init-admin
```

Enter a new username and a unique password of at least 12 characters twice. Interactive password input is hidden. No password is hardcoded or written to deployment JSON/logs.

The saved installation config is loaded independently of the caller's working directory. An absolute invocation from elsewhere is also supported:

```powershell
& "C:\path with spaces\Cafe LUX\.venv\Scripts\python.exe" "C:\path with spaces\Cafe LUX\manage.py" init-admin
```

Existing usernames are rejected without overwriting them. Reset users through an authenticated admin; if all access is lost, a trusted operator can create a new username. The original Flask create-admin command remains available. Version 1.1 fixes its audit event to work outside a web request.

Start with start.bat and sign in at /admin through your HTTPS IIS URL. See WINDOWS.md for local HTTP cookie testing and ADMIN.md for all website/catalog/order controls.
