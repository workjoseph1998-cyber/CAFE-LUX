# V2.1.1 — see the catalog without uploading 22 photos

The approved seed already includes starter descriptions. This update makes them visible in a private catalog preview and supplies 22 original small sample illustrations: hot drinks, iced drinks and coffee bags. Images are **480 × 400 px**, about **231 KiB total**, with each under **12 KB**. They are labeled illustrations, not actual product or owner-approved packaging photographs.

## On your existing Windows VM

1. Back up/stop the current application as in `MIGRATION.md`.
2. Extract the complete V2.1.1 ZIP into a new folder. Reuse the same `CAFE_LUX_DATA_DIR` and existing administrator. Run `setup.bat`, then `start.bat`. No new schema migration beyond V2.1's schema v4 is required.
3. Sign in and open **Admin → Catalog preview**.
4. Click **Add sample images & descriptions** once.

All seeded products with missing images receive their matching small sample illustration. Missing descriptions receive the approved starter copy. Existing photos, edited descriptions, prices, stock, categories, publication settings, users and order history are retained. Rerunning does not duplicate media or overwrite edits. There is no need to seed the catalog again when it has already been added.

The preview displays all 18 drink drafts and four coffee drafts in the storefront's cream-and-brown layout, with full descriptions. It also works before preparation using the bundled sample thumbnails, so you can inspect immediately. It is restricted to administrators and offers no purchase button. Prices remain pending until you set them; no fake selling prices are created and drafts remain hidden publicly.

If you deliberately publish an item with a sample illustration and your own configured prices for VM testing, the image remains visibly labeled SAMPLE ILLUSTRATION. Use your actual photos and reviewed descriptions for real business offers.

## Optional PowerShell command instead of the button

Run in the extracted application directory, using your actual persistent data path:

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\.venv\Scripts\python.exe manage.py prepare-catalog-preview --confirm-data-dir "$env:CAFE_LUX_DATA_DIR"
```

The command and button perform the same operation. A verified full database/media backup is made before changes. New image filenames are stable and content-addressed; original files are never overwritten. Only products with known approved starter identities can receive this content. Fresh installations still run the explicit approved catalog seed first.

Linux/PythonAnywhere uses the same code and `python manage.py prepare-catalog-preview --confirm-data-dir "$CAFE_LUX_DATA_DIR"`. No deployment is performed.
