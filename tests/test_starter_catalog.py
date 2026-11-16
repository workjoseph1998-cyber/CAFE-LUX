from cafe import create_app
from cafe.db import db
from cafe.starter_catalog import CATALOG
from conftest import add


def seeded_app(path):
    return create_app(
        {
            "TESTING": True,
            "DATA_DIR": str(path),
            "SESSION_COOKIE_SECURE": False,
            "SEED_STARTER_CATALOG": True,
        }
    )


def test_new_install_has_editable_unpriced_menu(tmp_path):
    app = seeded_app(tmp_path / "new")
    with app.app_context():
        assert db().execute("SELECT count(*) FROM categories").fetchone()[0] == len(
            CATALOG
        )
        assert db().execute("SELECT count(*) FROM products").fetchone()[0] == 19
        assert (
            db()
            .execute("SELECT count(*) FROM variants WHERE price IS NOT NULL")
            .fetchone()[0]
            == 0
        )
        assert (
            db()
            .execute("SELECT value FROM settings WHERE key='ordering'")
            .fetchone()[0]
            == "0"
        )
        weights = (
            db()
            .execute(
                "SELECT grams FROM variants v JOIN products p ON p.id=v.product_id WHERE p.name='House Blend' ORDER BY grams"
            )
            .fetchall()
        )
        assert [w[0] for w in weights] == [100, 200, 250, 500, 1000]
    client = app.test_client()
    html = client.get("/shop").text
    assert (
        "Espresso Classics" in html and "Iced Latte" in html and "House Blend" in html
    )
    assert html.count("Price to be configured") == 19
    assert "category-menu" in client.get("/").text


def test_upgrade_retains_existing_prices_stock_content_and_archives(app):
    with app.app_context():
        conn = db()
        conn.execute(
            "INSERT INTO products(name,kind,active) VALUES ('Espresso','drink',0)"
        )
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO variants(product_id,label,price,stock) VALUES (?,'Existing',1234,7)",
            (pid,),
        )
        conn.execute("UPDATE settings SET value='Owner headline' WHERE key='headline'")
        conn.commit()
    updated = seeded_app(app.config["DATA_DIR"])
    with updated.app_context():
        assert (
            db()
            .execute("SELECT count(*) FROM products WHERE name='Espresso'")
            .fetchone()[0]
            == 1
        )
        assert (
            db().execute("SELECT active FROM products WHERE id=?", (pid,)).fetchone()[0]
            == 0
        )
        assert tuple(
            db()
            .execute("SELECT price,stock FROM variants WHERE product_id=?", (pid,))
            .fetchone()
        ) == (1234, 7)
        assert (
            db()
            .execute("SELECT value FROM settings WHERE key='headline'")
            .fetchone()[0]
            == "Owner headline"
        )
        db().execute(
            "DELETE FROM variants WHERE product_id=(SELECT id FROM products WHERE name='Cold Brew')"
        )
        db().execute("DELETE FROM products WHERE name='Cold Brew'")
        db().commit()
    again = seeded_app(app.config["DATA_DIR"])
    with again.app_context():
        assert (
            not db().execute("SELECT 1 FROM products WHERE name='Cold Brew'").fetchone()
        )
        assert (
            db()
            .execute("SELECT count(*) FROM categories WHERE name='Iced Coffee'")
            .fetchone()[0]
            == 1
        )


def test_card_prices_come_from_saved_variants(client, app):
    with app.app_context():
        db().execute("UPDATE variants SET price=375 WHERE product_id=1")
        db().commit()
    html = client.get("/shop?kind=drink").text
    assert "USD 3.75" in html
    assert "<small>From</small>" not in html
    with app.app_context():
        db().execute("UPDATE variants SET price=610 WHERE id=2")
        db().commit()
    assert "<small>From</small>" in client.get("/shop?kind=drink").text


def test_unpriced_starter_cannot_be_purchased(tmp_path):
    app = seeded_app(tmp_path / "data")
    client = app.test_client()
    add(client)
    assert "Your bag is empty." in client.get("/cart").text
