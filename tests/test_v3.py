from cafe.db import db
from conftest import post, add


def test_finder_uses_only_published_product_attributes(client, app):
    with app.app_context():
        c = db()
        c.execute("UPDATE products SET roast='Owner configured roast' WHERE id=2")
        c.execute(
            "INSERT INTO products(name,kind,active,roast) VALUES ('PRIVATE draft coffee','ground',0,'Private draft roast')"
        )
        c.commit()
    response = client.get("/finder?kind=drink&temperature=cold")
    assert response.status_code == 200 and "TEST Latte" in response.text
    assert "TEST Ground" not in response.text
    response = client.get("/finder?kind=ground&roast=Owner+configured+roast")
    assert "TEST Ground" in response.text and "TEST Latte" not in response.text
    assert (
        "PRIVATE draft coffee" not in response.text
        and "Private draft roast" not in response.text
    )
    assert client.get("/finder?kind=ground&roast=Missing").status_code == 200
    assert "TEST Ground" not in client.get("/finder?kind=ground&roast=Missing").text
    assert client.get("/finder?kind=invalid").status_code == 400
    assert client.get("/finder?temperature=invalid").status_code == 400


def test_recent_fragment_revalidates_visibility_and_preserves_order(client, app):
    html = client.get("/recently-viewed?ids=2,1,2,999,not-an-id").text
    assert html.find("TEST Ground") < html.find("TEST Latte")
    assert html.count('href="/product/2"') == 1
    with app.app_context():
        db().execute("UPDATE products SET active=0 WHERE id=2")
        db().execute("UPDATE categories SET active=0 WHERE id=1")
        db().commit()
    html = client.get("/recently-viewed?ids=1,2").text
    assert "TEST Latte" not in html and "TEST Ground" not in html
    assert "product-card" not in client.get("/recently-viewed?ids=%3Cscript%3E").text


def test_cart_drawer_uses_real_server_forms_and_no_mutating_get(client, app):
    add(client, qty=2, addon="1")
    html = client.get("/cart").text
    assert 'id="cart-root"' in html and 'data-count="2"' in html
    assert 'action="/cart"' in html and "10.00" in html
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10
        assert not db().execute("SELECT 1 FROM orders").fetchone()
    assert client.post("/cart", data={"index": "0", "qty": "3"}).status_code == 400
    post(client, "/cart", {"index": "0", "qty": "3"})
    html = client.get("/cart").text
    assert "15.00" in html and 'data-count="3"' in html


def test_new_pages_preserve_privacy_and_rtl(client):
    assert client.get("/finder").status_code == 200
    post(client, "/language", {"lang": "ar"})
    assert 'dir="rtl"' in client.get("/finder").text
    assert 'dir="rtl"' in client.get("/cart").text
    html = client.get("/").text
    assert 'id="cart-drawer"' in html and 'href="/finder"' in html
    assert "card details" not in client.get("/recently-viewed?ids=1").text


def test_ordering_labels_are_derived_without_changing_settings(client, app):
    assert "Ordering is open" in client.get("/").text
    with app.app_context():
        db().execute("UPDATE settings SET value='1' WHERE key='paused'")
        db().commit()
    assert "Ordering is paused" in client.get("/drinks").text
    with app.app_context():
        assert (
            db().execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]
            == "1"
        )
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 0
