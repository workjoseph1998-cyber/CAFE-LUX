# Database migrations

Current application schema: **5**, release **4.0.0**. Follow [V4 installation, migration and rollback](V4-UPGRADE.md). `migration-status` is read-only; `migrate` adds missing migrations with a verified snapshot before an existing database changes. Startup/setup also migrate. Stop web and workers before applying changes.

Legacy schemas 2, 3 and 4 are supported as migration inputs. Existing catalog keys/images/prices/orders/users/settings remain. Schema 3 normalized legacy statuses; schema 4 added starter keys/options metadata; schema 5 adds V4 persistent features. The baseline schema and original regression fixtures stay in tests for compatibility verification, not as alternative maintained versions.

Never run sample/seed/publication commands as part of an upgrade. Do not copy a running SQLite file without its journals; use the backup API/command and verify the reopened backup. Newer/unrecognized schemas are rejected. Rollback to V3 requires its verified pre-upgrade database, not deletion of V4 schema. Preserve/reconcile later orders and account changes first.
