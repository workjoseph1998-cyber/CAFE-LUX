import pytest
from cafe import create_app
from cafe.db import db


@pytest.fixture
def explore(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATA_DIR": str(tmp_path / "data"),
            "SEED_STARTER_CATALOG": True,
            "SESSION_COOKIE_SECURE": False,
        }
    )


@pytest.mark.parametrize("path", ["/cart", "/checkout", "/order/anything"])
def test_order_pages_not_exposed(explore, path):
    assert explore.test_client().get(path).status_code == 404


def test_order_submission_disabled_even_if_old_setting_enabled(explore):
    with explore.app_context():
        db().execute("UPDATE settings SET value='1' WHERE key='ordering'")
        db().commit()
    client = explore.test_client()
    assert client.post("/cart/add", data={"variant": 1, "qty": 1}).status_code == 404
    assert client.post("/checkout", data={"name": "Synthetic"}).status_code == 404
    with explore.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 0


def test_explore_has_categories_prices_and_no_cart_calls_to_action(explore):
    client = explore.test_client()
    with explore.app_context():
        db().execute("UPDATE variants SET price=375 WHERE product_id=1")
        db().commit()
    for path in ["/", "/shop", "/product/1", "/shop?kind=ground"]:
        html = client.get(path).text
        assert (
            "Add to bag" not in html
            and 'href="/cart"' not in html
            and 'href="/checkout"' not in html
        )
    assert "USD 3.75" in client.get("/shop").text
    assert "Sizes &amp; prices" in client.get("/product/1").text
    assert "House Blend" in client.get("/shop?kind=ground").text
    assert "House Blend" not in client.get("/shop").text


def test_category_and_search_narrow_the_explore_menu(explore):
    client = explore.test_client()
    with explore.app_context():
        cid = (
            db()
            .execute("SELECT id FROM categories WHERE name='Iced Coffee'")
            .fetchone()[0]
        )
    html = client.get(f"/shop?category={cid}").text
    assert "<h3><a" in html and "Iced Latte" in html and "Double Espresso" not in html
    assert "No matches" in client.get("/shop?q=nonexistentchoice").text
