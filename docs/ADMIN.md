# Café LUX 2.1 administration

Sign in at `/admin` using an existing account. On a new installation only, create one with `manage.py init-admin`. Passwords are never seeded or reset by upgrades. Administrators manage all features; order operators can only access dashboard/orders, inspect details, update statuses and prepare customer notifications. Every route rechecks permissions.

## Catalog workflow

Run the explicit starter import described in `STARTER-CATALOG.md` after backing up and migrating. The compact sidebar separates Drinks from Beans & Ground Coffee. Categories, photos, operations and website settings stay accessible. Collapse the sidebar for icon-only navigation with tooltips; toggle Compact/Comfortable density in the header. Preferences are stored locally in the current browser, not in customer data.

Product tables show category, variant count, pending/starting price, stock, status, missing-image/price indicators and readiness checks. Search/filter/sort results and page through inventories (30 records per page). Display order is editable from the row. Quick Live, Publish in the editor and bulk publishing use identical server-side validation. Bulk actions are atomic; one invalid selected product prevents the whole publication action. Move selected products to draft without deleting them.

The product editor groups Basic information, Images, Pricing & variants, Customization and Publishing. Save an incomplete product as draft first. Enter confirmed descriptions/recipes/ingredient facts; starter marketing copy is not verified ingredient disclosure. Upload and assign a real owned/licensed product photo directly from the editor, or select one from Product images. Uploads retain previous image files and never overwrite another file. Unsupported files are rejected, decoded images are resized to at most 1600 px and re-encoded as optimized JPEGs.

Edit each enabled variant's independent price, grams, stock, optional SKU and order. Blank stock disables tracking; zero means unavailable. Preparation/grind and hot/cold restrictions belong to the exact variant, so whole-bean and ground combinations cannot be interchanged. Draft variants are disabled and unpriced until reviewed. Extras are optional and can use exclusive Milk/Sugar/Strength/Syrup groups. Pending surcharges show blank; enter an explicit value (including 0 for intentionally free) before enabling. Drafts and pending extras cannot be bought through crafted requests.

Publish requires a name, description, a registered uploaded photo that exists on disk, an active category and at least one enabled priced variant. All enabled variants need explicit prices; enabled extras cannot be pending. Existing legacy records are not automatically unpublished by migration, but future edit/publication operations enforce the checks. Changing the last purchasable variant of a live product requires drafting it first. Unsaved changes trigger browser navigation warnings; external variant/extra forms warn if another form has unsaved changes.

## Operations

Compact tables manage real WhatsApp receivers and delivery areas. Set one enabled default receiver. An area can use another enabled receiver; a disabled assignment falls back to the enabled default. Each order routes to one number. No receiver or no active area means checkout is unavailable. Unknown delivery fees are clearly pending and never shown as a final payable total. Existing settings are not changed by catalog seeding.

Set daily hours in Asia/Beirut time, closure dates and optional dated schedule slots. Slots remain administrator-maintained availability labels; disable full/past slots manually. Pausing stops all new submissions. A closure/out-of-hours period blocks immediate orders while explicitly configured scheduled slots can remain available.

## Orders

The order table supports reference/customer/phone search, UTC date/status filters and 30-row pages. Inspect opens an optional private side panel, or follow the reference/Details link for the full page. Both show delivery details, selected sizes/weights/preparations/extras, notes, totals, receiver and status history, with the same authorization. Status updates and manual WhatsApp notification links are in this compact detail view.

Initial status is **Pending WhatsApp Submission**. Customers must open WhatsApp and tap Send; the website cannot infer message receipt. Mark Received only after staff actually see the message. Confirmed/Preparing/Ready/Out for Delivery/Delivered changes deduct tracked stock once under a write lock. Pending/Received do not reserve stock, so staff confirmation can fail if another order consumed inventory. Cancellation restores only stock actually deducted and cannot reopen a cancelled order. Only Delivered product sales count as revenue; delivery charges are excluded.

Notification links prepare messages to the actual customer's saved phone and order reference. Staff must tap Send. Opening the link neither changes status nor claims delivery.

Backups/retention are in the dashboard's administrative tools section. Retention anonymizes closed orders when explicitly applied; expire backup copies separately. Backup ZIPs contain private customer data and hashes and must never enter Git or public hosting static directories.
