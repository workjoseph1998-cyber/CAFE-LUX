# Administration

Sign in at `/admin` using an account created with `manage.py init-admin`. Administrators have full access. Order operators can view the dashboard, manage orders and prepare customer notifications; catalog, media, users and settings are forbidden server-side. Password resets and disabling accounts revoke existing sessions.

## Launch configuration

1. Upload actual owned/licensed product photos in Product images. Images are decoded, resized and re-encoded; SVG and executable uploads are rejected.
2. Create categories and products. Drinks and packaged coffee have separate public catalogs. Unpublish products or disable categories for temporary unavailability.
3. Add independently priced sizes and package weights (custom grams supported). Blank price is not purchasable; blank stock means untracked. A zero stock variant is unavailable. Use whole-bean / ground descriptors in variant labels. Configure product grind/temperature choices, then narrow them per variant where combinations differ.
4. Add optional extras with prices. An exclusive group such as Milk or Sugar allows at most one of those extras. Leave the group blank for independent extras. Include the normal/default choice in your product description; extras are optional.
5. Mark featured products. Edit hero, bilingual copy, images, sections and promotion in Website & settings. Contact links start blank and can each be hidden while retaining their values.
6. Under Ordering & delivery configure actual WhatsApp numbers in `+` international format. Choose one active default. Configure only real delivery areas, independent fees, optional minimums and estimates. An area can assign another receiver; a disabled assigned receiver falls back to the active default. No silent fan-out occurs.
7. Set daily hours (Asia/Beirut; overnight ranges supported), closure dates and optional dated schedule slots. Disable full/past slots manually; slot labels are administrator-managed availability, not automatic capacity allocation. Pausing stops all new orders, including scheduled orders. When outside hours or on closure dates, immediate orders are refused; explicitly enabled slots remain available.
8. Enable ordering after testing.

## Order handling

Initial state is Pending WhatsApp Submission. The customer must manually tap Send. Opening a link proves nothing about delivery. Mark Received only when staff actually see the WhatsApp message. Confirming (or advancing into preparation) deducts tracked stock transactionally; pending/received submissions do not reserve stock. Two pending submissions may compete for stock; only confirmations that still have enough stock succeed. Cancellation restores previously deducted stock once, and cancelled orders cannot reopen.

States: Pending WhatsApp Submission, Received, Confirmed, Preparing, Ready, Out for Delivery, Delivered, Cancelled. Only Delivered contributes to sales. Orders retain price/option snapshots, receiving number, delivery area, schedule and status history. Filter by UTC date/status. Notifications prepare a WhatsApp message to the actual customer with the order reference; staff must tap Send. They do not change status or claim transmission.

Retention removes personal details from closed orders when explicitly run. Expire backup copies separately. Backups contain sensitive data and must never enter Git or a public release ZIP.
