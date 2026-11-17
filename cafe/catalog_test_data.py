"""Explicit owner-requested sample prices and publication for VM testing."""

from .db import db, audit
from .catalog import validate_publication
from .catalog_preview import prepare_catalog_preview, starter_descriptions

# Example amounts in the configured store currency, not verified selling prices.
DRINK_PRICES = {
    "espresso": [150],
    "double-espresso": [225],
    "americano": [200, 250, 300],
    "macchiato": [200],
    "cortado": [250],
    "cappuccino": [275, 325, 375],
    "caffe-latte": [300, 350, 400],
    "flat-white": [325],
    "mocha": [325, 375, 425],
    "spanish-latte": [350, 400, 450],
    "iced-americano": [250, 300, 350],
    "iced-latte": [325, 375, 425],
    "iced-spanish-latte": [375, 425, 475],
    "iced-mocha": [350, 400, 450],
    "cold-brew": [300, 350, 400],
    "lebanese-coffee": [200],
    "lebanese-cardamom": [225],
    "turkish-coffee": [225],
}
COFFEE_PRICES = {
    "lux-lebanese": [450, 950, 1750, 500, 1050, 1900],
    "lux-signature": [550, 1200, 2200, 575, 1250, 2300],
    "lux-espresso": [525, 1150, 2100, 550, 1200, 2200],
    "lux-golden": [600, 1300, 2400, 625, 1350, 2500],
}
EXTRA_PRICES = {
    "Oat milk": 50,
    "Almond milk": 50,
    "Extra shot": 75,
    "Vanilla": 35,
    "Caramel": 35,
    "Hazelnut": 35,
}
FEATURED = {"cappuccino", "caffe-latte", "iced-latte", "cold-brew", *COFFEE_PRICES}


def prepare_and_publish_starters():
    from .commands import make_backup

    # Full backup covers prices, publication settings and existing uploaded media.
    backup = make_backup()
    content = prepare_catalog_preview()
    conn = db()
    changed_prices = changed_extras = published = 0
    skipped = []
    conn.execute("BEGIN IMMEDIATE")
    try:
        for key in starter_descriptions():
            p = conn.execute(
                "SELECT * FROM products WHERE starter_key=?", (key,)
            ).fetchone()
            if not p:
                continue
            slug = key.removeprefix("starter.v21.product.")
            amounts = DRINK_PRICES.get(slug, COFFEE_PRICES.get(slug, []))
            for index, amount in enumerate(amounts):
                result = conn.execute(
                    "UPDATE variants SET price=?,active=1 WHERE product_id=? AND starter_key=? AND price IS NULL",
                    (amount, p["id"], key + f".variant.{index}"),
                )
                changed_prices += result.rowcount
            for extra in conn.execute(
                "SELECT * FROM addons WHERE product_id=? AND starter_key IS NOT NULL AND price_pending=1",
                (p["id"],),
            ).fetchall():
                conn.execute(
                    "UPDATE addons SET price=?,price_pending=0,active=1 WHERE id=?",
                    (EXTRA_PRICES.get(extra["name"], 0), extra["id"]),
                )
                changed_extras += 1
            try:
                validate_publication(p)
            except ValueError as error:
                skipped.append(f"{p['name']}: {error}")
                continue
            if not p["active"]:
                conn.execute(
                    "UPDATE products SET active=1,featured=? WHERE id=?",
                    (int(bool(p["featured"]) or slug in FEATURED), p["id"]),
                )
                published += 1
        audit(
            f"Owner-requested sample catalog: {changed_prices} variant prices, {changed_extras} extra prices, {published} products published"
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return dict(
        images=content["images"],
        descriptions=content["descriptions"],
        prices=changed_prices,
        extras=changed_extras,
        published=published,
        skipped=skipped,
        backup=str(backup),
    )
