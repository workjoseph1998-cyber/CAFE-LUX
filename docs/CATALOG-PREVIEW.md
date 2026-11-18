# Fill and publish the actual customer catalog

The final release includes 22 small sample illustrations, approved starter descriptions, and editable example prices. You no longer need to enter these fields product by product to test the website.

## Existing Windows installation

1. Back up and stop the application. Extract `Cafe-LUX-Version-4.0-Quiet-Ritual.zip` into a new directory and keep the same `CAFE_LUX_DATA_DIR` and existing administrator. Run `setup.bat`, then `start.bat`. Existing installations migrate additively to schema 5; follow V4-UPGRADE.md first.
2. Sign in to `/admin` and select **Catalog preview** (or **Fill & publish starter catalog** in the product table toolbar).
3. Click **Fill missing info & publish all with sample prices**.
4. Open `/drinks`, `/coffee` or the homepage in a signed-out browser. These are the real customer pages, not an admin-only preview. All normal untouched starter products now have images, descriptions and prices and can be added to the cart.

The action takes a verified database/media backup, fills missing seeded fields and pending sample extra prices, enables newly priced starter variants, and publishes products that pass the normal validation. Selected newly published drinks and the four coffees are featured on the homepage. Actual checkout still needs your configured receiving WhatsApp number, delivery area and store availability; those business details are never invented.

Existing nonblank descriptions, uploaded photos, selling prices, stock and previously configured variant availability are kept. Existing users/orders and unrelated products are unchanged. If an administrator has already intentionally disabled all priced variants, or enabled an incomplete custom option, that product is left for review and its reason is shown. Repeating the action does not duplicate products/media or change existing prices.

## Example prices

Amounts use the store's configured currency and are editable test values, not a currency conversion or verified selling prices. With the default USD currency, examples include Espresso $1.50, Cappuccino $2.75/$3.25/$3.75 and LUX Signature Blend whole beans $5.50/$12.00/$22.00 for 200 g/500 g/1 kg. Each size/weight/preparation has its own explicit price. Alternative milks, extra shots and syrups have editable sample surcharges; sugar/base options can be explicitly free.

The 22 JPEG illustrations are 480 × 400 px, 236,346 bytes combined, each under 12 KB. They remain visibly labeled SAMPLE ILLUSTRATION; owner photos are never replaced. All descriptions, prices and images can be edited later in the normal admin editor.

## Optional command instead of the button

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\.venv\Scripts\python.exe manage.py publish-starter-samples --confirm-data-dir "$env:CAFE_LUX_DATA_DIR"
```

No need to seed again if the starter catalog is already present. Fresh installations still run the explicit starter seed first. The older **Add sample images & descriptions** action remains available when you only want missing content filled without publishing or pricing.

Windows and PythonAnywhere use the same application code. No remote deployment is performed.
