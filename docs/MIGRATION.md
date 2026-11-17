# Migration and rollback

The previous application remains in Git history. Develop/review Version 2 on `feature/cafe-lux-v2-mobile-whatsapp`; merge into the default branch only after review. No history rewriting or unrelated release deletion is required.

## Upgrade

1. Disable ordering, drain requests and stop only Café LUX.
2. Using the old installation and its configured data path, create a database/media backup. Keep the old release folder and environment intact.
3. Extract Version 2 to a separate folder. Point `CAFE_LUX_DATA_DIR` at the same dedicated Café LUX data directory. Never point it at Cirrus data.
4. Run setup. Migration v3 adds routing, delivery areas, slots, status history, permissions and variant constraints; existing products, uploads, users and orders remain. Legacy Completed becomes Delivered, Ready for Pickup becomes Ready, and New becomes Received. Existing orders retain their prior deducted-stock behavior. Legacy settings are retained for data compatibility but obsolete pickup checkout is no longer exposed.
5. Configure actual delivery areas and WhatsApp receivers; existing single contact WhatsApp is not automatically treated as an order receiver. Validate locally before enabling ordering.

## Rollback

Stop Version 2 after draining. Restore the pre-upgrade data backup using the previous release's restore command, then run the previous release against that matching database. Keep a backup of Version 2 data separately if new orders were entered; a pre-upgrade restore will not include them. Do not downgrade schema in place. Never run old and new applications simultaneously on port 8000 or against the same database.

## Future portability

The Flask factory is standard WSGI and SQLite uses Linux-safe paths. A future host must set a dedicated persistent data directory, allowed hosts and production cookie/proxy settings. No PythonAnywhere account, WSGI hosting configuration or cloud deployment automation is created in this release. The current priority remains the Windows VM.
