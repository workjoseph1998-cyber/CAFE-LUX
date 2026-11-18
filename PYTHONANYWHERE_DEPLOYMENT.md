# Café LUX 4.0 — PythonAnywhere free-plan guide

Manual instructions only. Nothing is deployed by Codex or by these scripts. Windows and PythonAnywhere use the same Flask source but **separate private data directories**. Do not synchronize customer data automatically. Keep the Windows IIS/Waitress installation unchanged.

## 1. Prepare an approved checkout

Review the feature branch and merge approved changes into `main` first. In a PythonAnywhere Bash console, substitute your actual username in all commands:

```bash
cd ~
git clone https://github.com/workjoseph1998-cyber/CAFE-LUX.git
cd ~/CAFE-LUX
git checkout main
git pull --ff-only origin main
```

Use your own private Git authentication if required; never paste tokens into tracked files. Confirm the approved Version 4.0 commit with `git log -1 --oneline` and `cat VERSION`. Do not deploy an unreviewed branch accidentally.

## 2. Python and persistent configuration

Select Python **3.11 or 3.12** available on your PythonAnywhere account. Use that exact version for both the virtual environment and Web tab. Example for 3.11 (replace consistently with 3.12 if that is your available version):

```bash
python3.11 -m venv ~/.virtualenvs/cafe-lux
source ~/.virtualenvs/cafe-lux/bin/activate
cd ~/CAFE-LUX
pip install -r requirements.txt
mkdir -p ~/cafe-lux-data/{uploads,backups,logs}
chmod 700 ~/cafe-lux-data
cp config/pythonanywhere.env.example ~/cafe-lux-data/management.env
chmod 600 ~/cafe-lux-data/management.env
```

Edit `~/cafe-lux-data/management.env`, replacing `YOUR_USERNAME` with your real username and exact assigned hostname. Source it in each Bash management session:

```bash
source ~/cafe-lux-data/management.env
python manage.py migration-status
python manage.py migrate
python manage.py init-admin  # New installations only; retain an existing administrator
```

Admin setup prompts for your username and a unique password of at least 12 characters. No default credential exists. The data directory must stay outside `~/CAFE-LUX`; it holds SQLite accounts/orders/catalog/settings, images, backups and the session key. No source update replaces it. If you already have data, back it up before migration; automatic pre-migration snapshots are additional safeguards, not a substitute for the operator's full backup.

## 3. Add the approved drafts explicitly

Seeding is **not** part of migrations, setup or startup:

```bash
python manage.py seed-starter-catalog --dry-run
python manage.py seed-starter-catalog --confirm-data-dir "$CAFE_LUX_DATA_DIR"
```

This creates 18 draft drinks and four draft coffees on an empty catalog, plus 200 g / 500 g / 1 kg combinations. It does not publish offers or set prices/stock. Similar existing names are skipped and reported, not merged. Seeded edits remain untouched on reruns. See `docs/STARTER-CATALOG.md` before enabling variants or extras.

## 4. PythonAnywhere Web tab

1. Choose **Add a new web app**, your free `YOUR_USERNAME.pythonanywhere.com` domain, **Manual configuration**, and the same Python version used above.
2. Set the virtualenv path to `/home/YOUR_USERNAME/.virtualenvs/cafe-lux`.
3. Set source code and working directory to `/home/YOUR_USERNAME/CAFE-LUX`.
4. Open the WSGI file linked in the Web tab. Replace its sample contents using `config/pythonanywhere_wsgi.py.example` from this repository and substitute your actual username and paths.
5. The example imports `from wsgi import application`; root `wsgi.py` calls the real `cafe.create_app()` factory. It does **not** run `run.py`, Waitress, a second server, or port 8000.
6. Bash exports do not automatically reach hosted WSGI. Set data directory, exact allowed hostname, secure cookie mode and proxy scheme handling in the WSGI file as shown. Do not use wildcard hosts.

## 5. Static assets and uploaded media

Add one static mapping in the Web tab:

| URL | Directory |
|---|---|
| `/static/` | `/home/YOUR_USERNAME/CAFE-LUX/cafe/static` |

Uploaded photos continue through Flask's existing `/media/<filename>` route, which serves only registered images from `CAFE_LUX_DATA_DIR/uploads`. Do **not** map the whole data directory, database, backups, session key or uploads directory as public static storage. This keeps the existing validated media behavior identical to Windows.

## 6. Reload and verify manually

Click **Reload** in the Web tab, then visit the assigned **HTTPS** URL. Confirm:

- Home, `/drinks` and `/coffee` load with the new Quiet Ritual porcelain-and-forest design; drafts stay hidden.
- `/admin/login` accepts your created account; unauthorized admin access redirects to login.
- Cookies have Secure, HttpOnly and SameSite=Lax flags over HTTPS. The example trusts exactly one forwarded scheme header and no forwarded host/IP. Do not use insecure-local mode publicly.
- Upload a real photo, set actual prices/availability and final description, publish a reviewed product, and verify selections/cart/review/WhatsApp link.
- Configure only real delivery areas and receiving numbers. You must manually tap Send in WhatsApp; automatic messaging stays disabled until the separate Meta integration is configured.
- Check the Web tab error log after testing. Never include real customer data in shared screenshots.

The application sets no production debug server. Keep SQLite and private data on persistent local disk. The manual click-to-chat flow needs no background task. Official automatic notifications require a separate reliable always-on worker and permitted outbound Meta HTTPS; see docs/WHATSAPP.md. Free-plan limitations can prevent automation.

## 7. Future GitHub updates

Codex implements/tests a feature branch → you review/approve → merge to `main` → perform this manual update:

1. Pause ordering, stop admin edits/uploads and use your hosting maintenance procedure to drain requests. On a one-worker free app, arrange a maintenance window; this helper does not suspend WSGI automatically.
2. In Bash:

```bash
source ~/.virtualenvs/cafe-lux/bin/activate
source ~/cafe-lux-data/management.env
cd ~/CAFE-LUX
git status --short
git rev-parse HEAD  # record this rollback commit privately
python manage.py prepare-update
```

The helper verifies a database-plus-upload ZIP and prints its path; it neither pulls code nor reloads hosting. Copy it to secure off-host storage. Protect it because it contains password hashes and customer information. It refuses missing/invalid databases.

3. With the checkout clean and requests drained:

```bash
git pull --ff-only origin main
pip install -r requirements.txt
python manage.py migration-status
python manage.py migrate
python manage.py migration-status
```

Migrations are additive and versioned. Existing data is snapshotted and verified before a schema upgrade. Catalog seeding remains an explicit command and never overwrites administrator edits. Do not run development fixtures or replace SQLite with a release file.

4. Manually reload in the Web tab. Verify login, images, prices, cart, saved order history, checkout and the private logs before resuming orders.

## 8. Backups, recovery and rollback

```bash
python manage.py backup
# Only during an offline/drained maintenance window, restoring your own trusted backup:
python manage.py restore /home/YOUR_USERNAME/secure-backups/CafeLUX-YOUR_BACKUP.zip --confirm
```

Backups use SQLite's online backup API and include uploaded JPEGs; verification reads the saved database and tests archive CRCs. Media edits must remain paused for a coherent database/media snapshot. Session keys are excluded: retain the protected installation key, or rotate it offline to revoke sessions. Backups consume free-plan space; download securely and prune old copies manually. Never commit them.

For rollback after a schema change: keep the new data safely backed up, stop/drain requests, check out the recorded previous release commit (do not reset/force-push shared Git history), reinstall its requirements and restore the matching **pre-upgrade** backup using that release's restore instructions. Reload manually. A pre-upgrade backup will not contain orders placed later, so reconcile them before rollback. Do not run older code directly against a newer schema.

Raw `pre-migration-*` / `pre-starter-catalog-*` `.sqlite3` snapshots are local emergency database-only copies; media was never changed by migration/seeding. Restore only while stopped, after preserving the current database, by copying the chosen snapshot to `cafe.sqlite3`. Full ZIP restore is preferable. See `docs/MIGRATION.md` and `docs/BACKUPS.md`.

## 9. Free-plan limits and logs

Free account quotas and supported Python versions can change; verify them in your account. Plan for one app/worker, roughly 512 MiB storage, limited CPU/bandwidth, outbound-network restrictions, no new-account scheduled/always-on workers, and periodic web-app renewal. The application needs no outbound API access for ordering: the browser opens `wa.me` after server-side validation. Install production requirements only; do not install Playwright, the dev environment or screenshot files into your virtualenv.

Images are decoded, resized and stored as JPEGs. Keep uploads small and manually manage backups/log retention within your quota. Avoid copying a Windows virtualenv to Linux. Inspect **Web → Log files → Error log / Server log / Access log** for import, path, host and permission failures; logs may contain private operational details. A 400 invalid host usually means the WSGI hostname allowlist is wrong; a missing data-dir error means the WSGI environment was not set. Debug mode must remain disabled.

These instructions and WSGI smoke tests were prepared on Linux. No PythonAnywhere account was accessed or deployed, and no Windows VM/IIS execution is claimed.


## V4 upgrade and automation

Follow [V4-UPGRADE.md](docs/V4-UPGRADE.md) before touching existing data. V4 advances schema 4 to 5 additively after a verified snapshot. Pause/drain web and any worker, make a full backup, extract approved source, reuse the same external data, migrate and reload only after verification. Never seed or publish samples during upgrade. No live hosting deployment was performed.

For Meta automation see [WHATSAPP.md](docs/WHATSAPP.md). Free accounts may block Graph HTTPS and do not provide a reliable always-on worker; keep automation disabled until hosting supports it. WSGI and worker environments both need the protected Meta configuration; Bash exports alone do not reach WSGI. Never expose your data directory or secrets through a static mapping.
