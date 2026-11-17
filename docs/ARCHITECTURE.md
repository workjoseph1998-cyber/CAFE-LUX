# Architecture and security

Flask server-rendered Jinja, SQLite local disk, Pillow images, minimal local CSS/JS, Waitress loopback server. No Node build, background worker, paid API, customer account or card gateway.

`cafe/db.py` applies additive schema migrations through v3. `public.py` validates catalog choices, signs a lightweight cart cookie, prices products and areas server-side, performs final review and creates pending order snapshots under a SQLite write lock. Contact details are not stored in the cookie; only a review digest is. Unique order tokens handle repeated and concurrent submission. Availability is revalidated at checkout and stock is deducted only by authorized confirmation under a write lock.

`admin.py` manages catalog, media, content, operations, roles and orders. Passwords use salted Werkzeug scrypt hashes; dummy hashes cover unknown users. Active user and session-version checks run on every protected route. Operators are restricted to order operations and dashboard. Login and checkout limits persist in SQLite using the direct peer address (shared behind IIS). Mutations require CSRF, use parameterized SQL and render text with Jinja autoescaping. All public order access additionally requires the owning signed session; references alone reveal no contacts.

Images are byte/pixel limited, EXIF-oriented and re-encoded to random JPEG filenames; only recorded media is served. Runtime data lives outside source and source/protected path overlaps are rejected. A per-install key, distinct HttpOnly SameSite session cookie, Host allowlist, CSP, no-sniff, anti-framing and private-page no-store headers apply. HTTPS secure cookies are the default; Windows setup explicitly configures local HTTP mode for VM testing.

Stock is not reserved by abandoned WhatsApp links. Cancellation restores confirmed stock once; confirmation cannot oversell tracked stock. Order and notification URLs never claim messages were sent. Unknown fees use a separate `fee_known` flag; the internal numeric total excludes unknown fees and is not displayed as a final payable amount.

Single-instance SQLite is suitable for modest traffic and local persistent disk. Backups, access permissions and manual retention remain operational responsibilities. Scheduled slots are admin-maintained availability labels, without automatic capacity or expiry. No two-factor authentication, payment processing, tax engine or automatic hosting deployment is included.
