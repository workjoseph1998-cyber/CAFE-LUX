from cafe.db import db
from cafe.starter_catalog import seed_catalog
from cafe.catalog_test_data import prepare_and_publish_starters
from conftest import post, login, add


def test_samples_fill_publish_public_pages_and_repeat(app, client):
    with app.app_context():
        seed_catalog()
        before = [tuple(r) for r in db().execute("SELECT * FROM users")]
        result = prepare_and_publish_starters()
        assert (
            result["images"] == 22
            and result["prices"] == 62
            and result["published"] == 22
        )
        assert not result["skipped"]
        products = (
            db()
            .execute("SELECT * FROM products WHERE starter_key IS NOT NULL")
            .fetchall()
        )
        for p in products:
            assert p["active"] and p["image"] and p["description"]
        assert (
            not db()
            .execute(
                "SELECT 1 FROM variants WHERE starter_key IS NOT NULL AND (price IS NULL OR stock IS NOT NULL)"
            )
            .fetchone()
        )
        assert [tuple(r) for r in db().execute("SELECT * FROM users")] == before
        prices = [tuple(r) for r in db().execute("SELECT * FROM variants")]
        again = prepare_and_publish_starters()
        assert again["prices"] == 0 and again["images"] == 0 and again["published"] == 0
        assert prices == [tuple(r) for r in db().execute("SELECT * FROM variants")]
        espresso = (
            db().execute("SELECT * FROM products WHERE name='Espresso'").fetchone()
        )
        vid = (
            db()
            .execute("SELECT id FROM variants WHERE product_id=?", (espresso["id"],))
            .fetchone()[0]
        )
    html = client.get("/drinks").text
    assert "Double Espresso" in html and "Caffè Latte" in html and "USD 1.50" in html
    assert "LUX Signature Blend" in client.get("/coffee").text
    assert "Cappuccino" in client.get("/").text
    assert client.get(f"/product/{espresso['id']}").status_code == 200
    add(client, variant=vid)
    assert "1.50" in client.get("/cart").text


def test_existing_prices_content_stock_and_availability_survive(app):
    with app.app_context():
        seed_catalog()
        c = db()
        pid = c.execute("SELECT id FROM products WHERE name='Espresso'").fetchone()[0]
        c.execute(
            "UPDATE products SET description='Owner edited recipe' WHERE id=?", (pid,)
        )
        c.execute(
            "UPDATE variants SET price=999,stock=7,active=0 WHERE product_id=?", (pid,)
        )
        c.commit()
        result = prepare_and_publish_starters()
        variant = c.execute(
            "SELECT * FROM variants WHERE product_id=?", (pid,)
        ).fetchone()
        assert (
            variant["price"] == 999 and variant["stock"] == 7 and variant["active"] == 0
        )
        assert (
            c.execute("SELECT description FROM products WHERE id=?", (pid,)).fetchone()[
                0
            ]
            == "Owner edited recipe"
        )
        assert (
            c.execute("SELECT active FROM products WHERE id=?", (pid,)).fetchone()[0]
            == 0
        )
        assert any("Espresso:" in issue for issue in result["skipped"])


def test_admin_publish_action_and_permissions(app, client):
    with app.app_context():
        seed_catalog()
    assert client.post("/admin/catalog-preview/publish").status_code == 400
    login(client)
    response = post(client, "/admin/catalog-preview/publish")
    assert response.location.endswith("/drinks")
    assert "Published 22 starter products" in client.get("/drinks").text
    with app.app_context():
        db().execute("UPDATE users SET role='operator'")
        db().commit()
    assert post(client, "/admin/catalog-preview/publish").status_code == 403
