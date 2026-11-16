# Administrator setup and everyday use

## First run

1. Follow the Windows setup guide; run the interactive `create-admin` command. There is no public administrator registration or default password.
2. Sign in at `/admin` over HTTPS. Login sessions expire after one hour. Five failed attempts trigger a persistent 15-minute lockout per direct connection IP. See the IIS limitation in the Windows guide.
3. Open **Website & settings**: configure brand, USD or another three-letter currency, English/Arabic hero text, About story, banner, footer, location, opening hours, contact and social links. Fields are blank or explicitly pending until supplied. No sourcing or history claims are prefilled.
4. Upload your logo, original packaging artwork, product images, lifestyle and café photos in **Media library**, then select them in products or settings. The original chat packaging files were not available as downloadable workspace attachments; they are not bundled. A generated editorial hero is supplied as a replaceable default.
5. Create categories in either language. Set their display order.
6. Create products; keep them as drafts while preparing their images, options and prices.
7. Enable pickup/delivery as appropriate, set delivery charge and minimum subtotal, test the entire cash flow, then enable **Accept orders**. Currency changes do not convert amounts; review every product price before changing currency.

## Catalog

Each product has a type (drink / ground coffee), editable English and Arabic name/description, category, main image, multi-image gallery, temperature, roast, origin, bean, flavor notes, preparation instructions, comma-separated grind choices, display order, featured flag and publish flag.

Missing Arabic content falls back to English. Interface labels use Arabic with an RTL layout. User-supplied option labels and business information can contain either language. For fully localized presentation, populate Arabic names and descriptions and use bilingual free-text business fields.

Create any number of **independently priced** sizes or weights. Standard ground weights are 100, 200, 250, 500 and 1000 grams; type any custom grams and label (for example 375 g) into a new variant. Prices do not scale automatically with weight. Blank price means not purchasable. Explicit `0.00` is a free variant. Stock tracks packages/cups per variant, not raw bean weight. Blank stock means unlimited/untracked. Zero stock means sold out.

Add drink extras per product with their own price, availability and Arabic label. Disable an option to remove it from sale. Uncheck Published to archive a product; order snapshots remain intact. Featured products appear on the homepage. Unfeatured products remain in the shop. Ordering is always validated against the current server catalog, regardless of browser totals.

## Images

Upload JPEG, PNG or WebP, max 8 MB and 20 megapixels. The server decodes and rewrites images as bounded JPEGs with random filenames, stripping metadata. Transparency is flattened by RGB conversion; use a suitable opaque logo. SVG, executable and animated uploads are not accepted. Titles and alt text are editable. Drag a file onto the file input or choose it; a local preview is shown.

To replace: upload a new image, select it in each product/section that used the old image, then delete the unreferenced original. The library lists references and blocks deletion while any product (including an archived draft) or section uses an image. Media filenames are public random identifiers; never upload private customer information.

## Orders and inventory

Orders list the customer details, immutable item names/options/prices, currency, fee, method, requested time, notes and status. Pagination retains access to all orders. All timestamps and daily/monthly reports use UTC.

Stock is atomically reserved when an order is saved. Cancelling restores tracked stock **once**. A cancelled order cannot be reopened; make a new order. Completed and pending orders retain their reservation. The confirmation page is restricted to the customer's session and cannot be retrieved by guessing a reference from a different browser.

Pickup time is a request, not a booking guarantee. Delivery is a manually fulfilled option; zones and route planning are not automated. Cash payment is due on pickup or delivery. Order-status changes do not automatically send SMS, email or WhatsApp messages; staff must contact the customer directly.

## Reports, privacy, administrators

Overview shows orders today/month, pending count, completed revenue by currency, variant/product and category sales, low-stock warnings and the recent audit log. Pending/cancelled totals are excluded from completed revenue. No exchange rates or cross-currency totals are invented.

Set a retention period (default 365 days), then **Apply retention policy** to anonymize personal details in older completed/cancelled orders. This is a deliberate manual action; schedule operational review. Backup copies need their own expiry policy. For a targeted customer deletion request, use **Remove customer details** on the completed/cancelled order. Active orders must be closed first. Expire corresponding backup copies separately. Financial snapshots remain after anonymization.

Administrators all have full management privileges. Create/reset/disable accounts in Administrators. Password resets and disable actions revoke existing sessions. You cannot disable your own account. Losing all admin access requires a trusted server operator to run `create-admin` with a new username; no unauthenticated recovery backdoor exists.

Daily settings require no source edits. Operational deployment, secure storage permissions and restore commands remain trusted server-operator tasks.
