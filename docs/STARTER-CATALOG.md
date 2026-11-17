# Approved starter catalog — explicit, draft-only import

`setup.bat`, application startup and schema migrations never seed the catalog. Run it deliberately against your intended Café LUX data directory, after stopping/draining the application and pausing catalog edits:

```powershell
$env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData'
.\.venv\Scripts\python.exe manage.py migration-status
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed-starter-catalog --dry-run
.\.venv\Scripts\python.exe manage.py seed-starter-catalog --confirm-data-dir "$env:CAFE_LUX_DATA_DIR"
```

On Linux use `python manage.py ...` in the configured virtualenv, with `--confirm-data-dir "$CAFE_LUX_DATA_DIR"`. The confirmation argument must match the resolved data directory exactly; the command prints that directory. `--dry-run` makes no catalog writes. Application initialization may apply a required, automatically backed-up migration first; use `migration-status` and `migrate` explicitly before the dry run.

## Contents on an empty catalog

| Drink category | Draft products |
|---|---|
| Espresso & Classics | Espresso; Double Espresso; Americano; Macchiato; Cortado |
| Milk-Based Coffee | Cappuccino; Caffè Latte; Flat White; Mocha; Spanish Latte |
| Iced Coffee | Iced Americano; Iced Latte; Iced Spanish Latte; Iced Mocha; Cold Brew |
| Arabic & Traditional Coffee | Lebanese Coffee; Lebanese Coffee with Cardamom; Turkish Coffee |

| Packaged coffee | Category | Preparation combinations |
|---|---|---|
| LUX Lebanese Blend | Traditional Coffee | Plain ground; ground with cardamom |
| LUX Signature Blend | Signature Blends | Whole coffee beans; ground coffee |
| LUX Espresso Roast | Espresso Blends | Whole coffee beans; espresso-ground coffee |
| LUX Golden Roast | Specialty Blends | Whole coffee beans; ground coffee |

Each packaged preparation has its own **200 g, 500 g and 1 kg** variant: six independently configurable combinations per product. Preparation and weight are held in the existing variant label/grams/allowed-grinds model, without a second pricing system. Optional SKU and display order are editable per variant. A whole-bean choice cannot be combined with a ground-only weight variant; restrictions are checked server-side.

Espresso, Double Espresso, Macchiato, Cortado, Flat White and traditional coffees start with one serving option. Other approved drinks have independently priced Small, Regular and Large options. Iced products are cold-only; hot products are not automatically made iced.

All 22 products are unpublished/unfeatured; all 62 variants start disabled with **NULL price and NULL stock**. Factual origin, composition, roast, tasting notes and certifications are empty. No image is assigned and no business settings, accounts, orders, photos or receiver rules are modified.

## Customization

Sugar preferences are drafted for all drinks: No sugar, Less sugar, Regular sugar, Extra sugar. Milk choices (Regular/Oat/Almond) apply only to the milk-based and relevant iced milk drinks. Standard/Extra shot are drafted for appropriate espresso-based drinks, excluding Espresso/Double Espresso, Cold Brew and traditional preparations. No syrup/Vanilla/Caramel/Hazelnut are drafted for Caffè Latte, Iced Latte and Cold Brew. Administrators must confirm recipe compatibility and can edit/add/disable every option.

Each group is exclusive (one selection maximum), checked both in the UI and on the server. Extras are optional; not choosing one retains the product's configured base recipe. Do not use marketing descriptions as verified ingredient/allergen disclosures.

V2.0's extras table requires a numeric price. To preserve that schema without dropping/rebuilding the table, new extras use `price_pending=1`, `active=0` and an internal numeric sentinel of 0. **That sentinel is not an advertised free surcharge:** pending extras are excluded from public selection and rejected in crafted carts. Admin fields show the price as blank/Pending. Enter an explicit reviewed surcharge, including 0 when intentionally free, and enable the extra. No fabricated selling price is assigned to a starter variant.

## Idempotency and conflicts

Stable `starter_key` values identify categories, products, variants and extras. Existing records without a matching identity are never adopted by display name. Exact/closely similar names (case/accent/punctuation-insensitive comparison and conservative similarity detection) produce a CONFLICT report and are skipped. A category conflict also skips products in that category until manually resolved.

Review the named record and decide which one the business intends to keep. If they are distinct, rename your existing record to clearly distinguish it before rerunning. If it is the same intended product, manage the existing product manually and leave the seed conflict skipped; do not copy unreviewed SQL or overwrite it. Near-name detection is conservative, not a guarantee of semantic identity.

Already seeded products are skipped as a whole, so edited prices, availability, photos, descriptions and even intentionally removed options remain unchanged. A seed ledger prevents deleted seeded products/categories from being recreated. Each real seed run creates a distinct verified pre-seed SQLite snapshot and an audit record, even if there are no new additions.

## Review and publish

Open **Drinks** or **Beans & Ground Coffee** in admin. Filter Draft and use Missing image/price/readiness indicators. Open a product, review its description/ingredients, upload actual owner-approved photography, set variant prices and availability, configure stock/SKU/order and confirm extras. Publish from the editor, quick row control or bulk toolbar; all three share the same server-side validation.

Publication requires a name, description, registered uploaded photo present on disk, active category and at least one enabled priced variant. Every enabled variant must have a price, and no enabled extra may retain a pending price. Save incomplete products as drafts. Drafts never appear in public catalogs, search, featured sections or direct product URLs and cannot be ordered by a crafted request. Disabling the last priced variant of an already published product is refused; draft the product first.

Small neutral admin icons and the existing explicitly illustrative storefront fallbacks are placeholders, not real product photography. Seeding never replaces an uploaded image. Actual package artwork must come from the owner or an approved licensed source.


### V2.1.1 visual testing shortcut

Open **Catalog preview** in admin and click **Add sample images & descriptions**. This fills missing seeded images/descriptions after a verified full backup while preserving edits and draft/pricing state. The private preview shows all approved drafts immediately without publishing. See `CATALOG-PREVIEW.md`. The original seed remains draft-only and does not assign images automatically; preparing samples is an explicit action.


### Owner-requested sample prices and customer publication

The final release additionally provides **Fill missing info & publish all with sample prices**, as explicitly requested for VM testing. It fills only missing seeded content/prices, preserves existing prices and availability edits, and publishes valid products to the actual customer pages. This is separate from the draft-only seed and from content-only preparation. See `CATALOG-PREVIEW.md`; all example amounts remain editable.
