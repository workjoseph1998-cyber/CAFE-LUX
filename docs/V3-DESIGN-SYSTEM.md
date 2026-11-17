# Café LUX 3.0 — Espresso Editorial Luxury

V3 rebuilds the customer experience and the operations workspace while keeping the existing Flask/SQLite architecture and business data. The branch is `feature/cafe-lux-v3-redesign`, based on the fetched `main` commit `cb4e56c`. It is not automatically merged or deployed.

## Customer design

The system uses espresso `#241C17`, ivory `#F5F1E9`, paper `#FFFDF8`, warm sand `#E9DFD0` and copper `#B77B54`. Large system-serif headlines pair with readable system-sans controls and product information. There are no remote fonts, frontend runtime dependencies or asset CDNs.

The homepage is composed as an editorial: full-bleed photographic illustration, oversized configured headline, asymmetric drink/coffee collection panels, published featured products, a copper Coffee Finder section, contrasting brand story and a concise ordering guide. Existing configured hero, logo, copy, visibility flags and photos continue to take precedence. No settings are rewritten to achieve the visual design.

Catalogs use immersive portrait imagery, category switching, search and current category filters. Cards retain actual names/descriptions/prices/availability from the database. Product pages combine a sticky desktop image gallery with the same real size/weight/grind/temperature/add-on inputs, quantity controls and live totals. User product photos and the existing clearly illustrative fallback/sample media are retained, not replaced.

A data-driven `/finder` page filters only currently published products by drink/packaged type, configured temperature and actual nonempty roast metadata. It does not infer taste, origins, recipes or recommendations from invented attributes. Empty matches are a designed state.

Recently viewed products store at most six numeric public product IDs in browser localStorage. No names, prices, addresses, phones or order information are stored there. `/recently-viewed` rebuilds the cards from current published/category-active records on every request, so archived or private products are not exposed and changed prices are not read from stale local metadata. Storage/network failures do not block browsing.

The bag is a progressively enhanced native dialog drawer. It fetches the real server-rendered cart, posts the same CSRF-protected forms and updates totals/counts using the server response. It preserves a normal `/cart` page for no-JavaScript/unsupported-browser fallback. A dedicated drawer footer keeps checkout visible while item rows scroll, with no content covered by a floating control. Drawer mutations also synchronize the standalone cart when that page is open.

Checkout is split visually into details, review and WhatsApp stages. Real area fees update the display; unknown fees never produce a claimed payable total. On phones the item list is collapsible while monetary totals stay visible. Final review still precedes pending-order creation. The WhatsApp screen explicitly requires manually tapping Send and never claims receipt or dispatch.

## Operations design

The admin is deliberately separate: a compact ivory/olive operations workspace with a light sidebar, dark selected navigation, clear breadcrumb/search header, seven small operational metrics and dense order/catalog tables. Dashboard order activity, next actions, catalog health and inventory have independent sections. No decorative charts or fabricated metrics are added.

Existing permission checks, product editors, bulk/quick actions, stock controls, media uploads, draft/publication validation, operations settings, order inspector, status history, notifications, backups and retention remain. Collapsed navigation and density preferences use the same browser keys as before. New admin styles cover every existing form/table, not just the dashboard. Labels and muted foreground colors were darkened for readability.

## Motion, responsiveness and accessibility

- Desktop layouts scale through 620/800/1120/1600px storefront breakpoints; admin has its own independent breakpoints.
- Phones have clear icon-and-label navigation, native form controls, 16px input text to reduce focus zoom, readable product options, and safe space for bottom navigation.
- Controls have visible keyboard focus. Native dialogs support Escape/focus trapping. Button and gallery labels remain accessible, and all user-entered text is escaped by Jinja.
- Motion is limited to card reveals/image hover, drawer entry, real loading feedback and browser-supported view transitions. Reduced-motion disables animation/transitions and keeps all content visible.
- Arabic RTL remains supported with logical layout properties and expanded translations for core navigation, product, Finder, bag and checkout labels. Administrator-entered translations remain authoritative; untranslated marketing copy falls back to English.

## Maintainable components

`_icons.html` supplies shared inline SVGs. `_cards.html` is reused by home, catalogs, Finder, related and recent products. `base.html` owns navigation/footer/drawer. Public CSS tokens and common controls live in `style.css`; the admin uses its own `admin.css`/`admin.js`. Public progressive enhancements are in `app.js`. No build pipeline is required.
