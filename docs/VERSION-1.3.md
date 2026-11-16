# Café LUX 1.3 — Explore

This release is a menu and brand discovery website. Visitors explore drinks and packaged coffee, compare sizes/weights and prices, read product information and find the café.

## Public experience

- No cart icon, add-to-cart buttons, checkout forms or online ordering.
- Cart, checkout, order-confirmation and order-submission endpoints return 404, even if a previous database has ordering enabled.
- Drinks and Ground Coffee are separate, clear choices. The initial menu shows drinks.
- Category buttons, grouped headings, search, item counts and clear-filter links narrow choices.
- Warm light menu surfaces with darker text, larger prices and readable controls.
- Size/weight selectors preview configured prices without sending an order request.
- Espresso, iced coffee, Turkish coffee and hot chocolate use distinct generated fallback illustrations. Your uploaded images take priority.
- English/Arabic RTL, mobile navigation and reduced-motion behavior remain supported.
- The black/gold brand header and cinematic hero remain.

No selling prices were supplied. Existing prices remain unchanged. Unconfigured items show “Price coming soon”; no fake live prices are inserted. Screenshots use a visibly labeled synthetic-price fixture.

## Administration and data

Keep using /admin to manage categories, products, descriptions, photos, individual size/weight prices, availability, featured items, translations and website content. No new admin account is required when upgrading.

Existing products, stock, customers' historical order records, users, settings and uploaded images are retained. The administrative order history remains for old records; there is no public purchase workflow. Old order-acceptance flags do not re-enable it. Cart/checkout code is retained only for legacy regression coverage/future separately authorized changes; the production app blocks those endpoints.

## Upgrade on your VM

1. In the old application folder, run stop.bat. If it currently accepts orders, disable them and drain requests first.
2. Back up your existing Café LUX data and retain the old source/config.
3. Extract the complete Cafe-LUX-Version-1.3-Explore.zip into a new release folder.
4. Copy your current cafe-lux.local.json beside the new manage.py. This retains your existing data path, IIS hostname and cookie configuration.
5. Run setup.bat, then start.bat in the new folder. Use your existing /admin login.
6. Verify the homepage, Drinks/Ground Coffee, category/search controls, prices, product details, location and admin through your IIS URL.

Do not start the new release before stopping the old release from its original folder. Process records belong to their original application root. Do not copy the database into the source folder or overwrite existing data.

Windows setup/start/stop fixes and schema v2 remain. This cloud task does not deploy to your VM or change IIS.

## Validation

94 backend checks passed. The browser acceptance runner checks the real explore-only app: mobile/desktop layouts from 320–1440 pixels, category/search/reset, per-weight price preview, Arabic RTL, absence of public cart/checkout links and rejection of direct order requests. Admin management and coffee animations remain functional. See screenshots/browser-report.json for the recorded browser result.

The earlier checkout tests run only against an explicit internal test configuration, preserving regression coverage of historical code. They do not enable ordering in the shipped production configuration.
