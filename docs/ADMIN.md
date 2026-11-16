# Café LUX 1.3 — Administrator guide

Sign in at /admin through your configured IIS HTTPS address. Existing accounts survive upgrades. For a new installation, run python manage.py init-admin from the application venv; no default password exists.

## Menu and categories

Categories are editable in English/Arabic with display order. Published drinks and packaged coffee are separate menu modes. Public category buttons show only categories with visible products.

Products support English/Arabic names/descriptions, type, category, main image, gallery, temperature, preparation information, grinds, roast/origin/flavor notes, display order, featured status and publication status. Uncheck Published to archive. Missing Arabic content falls back to English.

Review starter descriptions/ingredients before publishing your actual menu. Starter items are imported once; your later edits, renames, archives and deletions are preserved.

## Prices and sizes

Products → Edit → Sizes & package weights: enter a label, optional grams and an individual price. Save each option. Ground weights can include 100 g, 200 g, 250 g, 500 g, 1 kg or any custom grams; pricing is independent, never scaled automatically.

Blank price means “Price coming soon.” Zero is an explicit free price. Public visitors can choose sizes to preview the exact configured price; no cart or order is created. Currency is set under Website & settings; changing it does not convert existing numbers.

## Photos and website content

Upload JPEG/PNG/WebP through Media library, then select the image in the product or website settings. Safe decoding, 8 MB/20 megapixel limits, random filenames, JPEG re-encoding and reference-aware deletion remain.

Your actual product photos override generated fallback illustrations. Update alt text and image titles for accessibility. About, location, contact details, hours, links, homepage copy/images, logo, featured visibility, footer and policies remain editable.

## Explore-only mode

There are no public purchase controls or order endpoints in this release. Old order acceptance settings cannot turn them back on. Order history, reports, retention and backup controls are retained for historical records and data continuity.

Administrators still manage accounts and passwords. Password resets/disable actions revoke sessions. Use regular database/media backups, secure storage permissions and the documented retention policy for historical personal data. No real customer records or passwords belong in Git or release ZIPs.

See VERSION-1.3.md for upgrade instructions and WINDOWS.md for IIS Host/cookie configuration.
