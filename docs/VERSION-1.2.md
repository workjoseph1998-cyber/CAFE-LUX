# Version 1.2 — Glass Menu

The update adds a coffee-shop starter catalog and a smoked-glass visual treatment while retaining the Windows 1.1 setup/start/stop fixes.

## Included starter menu

- Espresso Classics: Espresso, Double Espresso, Americano, Cappuccino.
- Lattes & Chocolate: Café Latte, Caramel Latte, Vanilla Latte, Café Mocha, Hot Chocolate.
- Iced Coffee: Iced Americano, Iced Latte, Iced Caramel Latte, Cold Brew.
- Arabic & Turkish: Arabic Coffee, Turkish Coffee.
- Ground Coffee: House Blend, Espresso Blend, Arabic Coffee Blend, Turkish Coffee Blend.

English/Arabic names and starter descriptions are editable. Review ingredients/preparation before selling. Ground coffee includes individually priced 100 g, 200 g, 250 g, 500 g and 1 kg options; admin can add custom weights. Drink sizes are editable.

**No real prices were provided.** New items show “Price to be configured” and cannot be purchased until priced. Existing prices appear beneath product names; “From” appears only when prices differ. Existing stock, descriptions, ordering settings, accounts and orders are retained.

In /admin → Products → Edit, set each size/weight price, save the option, and review publication/availability. Configure currency in Website & settings. No exchange rate or real selling price is invented.

## Safe VM upgrade

1. In your **old application folder**, disable orders if necessary, drain requests and run stop.bat. Stop the old installation before moving: its process record belongs to its original path.
2. Back up using the old installation's python manage.py backup. Keep old source/config/data.
3. Extract the complete Cafe-LUX-Version-1.2-Glass-Menu.zip into a separate new release folder.
4. Copy your existing Café LUX cafe-lux.local.json beside the new manage.py to retain the same data directory. Do not put the database inside source.
5. In the new folder run setup.bat. Initialization adds missing starter items once, without modifying existing matching product names/prices/availability.
6. Run start.bat; sign in with your existing admin. Only new installations need init-admin.
7. Review starter descriptions/photos, set real prices and test through your IIS URL.

The import is remembered in settings. Later edits, renamed/archived/deleted starter items are not recreated. Matching product names/types and category names are reused without modification.

Schema remains v2. Source rollback does not remove new rows; archive unwanted items through admin or deliberately restore a pre-upgrade backup while stopped. Windows Host/cookie configuration and port 8000 are unchanged.

## Glass design

Frosted navigation, translucent dark panels, gold borders, rounded product cards and category tiles. Fields remain readable. Browsers without backdrop-filter receive a dark fallback. Reduced transparency/motion and Arabic RTL remain supported.

## Verification

88 backend tests passed, including one-time import, weights, preservation of prices/stock/content/archives, deletion persistence, price display and unpriced-purchase refusal. Updated browser screenshots use the real starter catalog in a disposable database with a prominent synthetic-price banner; see screenshots/browser-report.json. No real deployment data is packaged.

No deployment or test on your actual VM was performed by this cloud task. Follow the upgrade steps and VM-CHECKLIST.md.
