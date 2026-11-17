import io
import json
import socket
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from PIL import Image
from cafe import create_app
from cafe.db import db
from cafe.public import cents
from run import port_available
from conftest import post, login, add, checkout


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/shop",
        "/shop?kind=drink",
        "/shop?kind=ground",
        "/shop?kind=",
        "/product/1",
        "/product/2",
        "/cart",
        "/page/about",
        "/page/location",
        "/page/contact",
        "/page/privacy",
        "/page/terms",
    ],
)
def test_public_pages(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/products",
        "/admin/products/1",
        "/admin/categories",
        "/admin/settings",
        "/admin/media",
        "/admin/orders",
        "/admin/users",
    ],
)
def test_admin_protection(client, path):
    assert client.get(path).status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/products",
        "/admin/products/1",
        "/admin/products/0",
        "/admin/categories",
        "/admin/settings",
        "/admin/media",
        "/admin/orders",
        "/admin/users",
    ],
)
def test_admin_pages(client, path):
    login(client)
    assert client.get(path).status_code == 200


def test_csrf_all_mutations(client):
    assert client.post("/cart/add", data={"variant": 1}).status_code == 400
    assert client.post("/admin/login").status_code == 400


def test_arabic(client):
    post(client, "/language", {"lang": "ar"})
    html = client.get("/product/1").text
    assert 'dir="rtl"' in html and "لاتيه تجريبي" in html and "أضف إلى الحقيبة" in html


def test_prices_snapshot_idempotency(client, app):
    add(client, qty=2, addon="1", price="0.01")
    r = checkout(client, total="1")
    assert r.status_code == 302 and "/order/LUX-" in r.location
    assert "Pending WhatsApp Submission" in client.get(r.location).text
    with client.session_transaction() as s:
        token = s["order_token"]
    again = post(client, "/checkout", {"order_token": token})
    assert again.location == r.location
    with app.app_context():
        o = db().execute("SELECT * FROM orders").fetchone()
        assert o["total"] == 1250
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 1
        db().execute("UPDATE products SET name='Changed' WHERE id=1")
        db().execute("UPDATE variants SET price=9999 WHERE id=1")
        db().commit()
        assert json.loads(o["items"])[0]["name"] == "TEST Latte"
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10
    assert client.get(r.location).headers["Cache-Control"] == "no-store"


def test_weights_independent(app, client):
    with app.app_context():
        variants = db().execute("SELECT * FROM variants WHERE product_id=2").fetchall()
        assert [v["grams"] for v in variants] == [100, 200, 250, 500, 1000, 375]
    add(client, variant=4, grind="Fine")
    checkout(client)
    with app.app_context():
        assert db().execute("SELECT total FROM orders").fetchone()[0] == 647


def test_delivery_validation(client, app):
    add(client)
    r = checkout(client, fulfillment="delivery", address="x")
    assert r.location.endswith("/cart")
    with app.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 0
    checkout(
        client, fulfillment="delivery", address="Synthetic address for testing only"
    )
    with app.app_context():
        assert db().execute("SELECT total FROM orders").fetchone()[0] == 625


def test_closed_orders(client, app):
    add(client)
    with app.app_context():
        db().execute("UPDATE settings SET value='0' WHERE key='ordering'")
        db().commit()
    checkout(client)
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()


def test_unavailable_addons_stock(client, app):
    add(client, qty=11)
    with client.session_transaction() as s:
        assert not s.get("cart")
    add(client, addon="999")
    with client.session_transaction() as s:
        assert not s.get("cart")
    add(client, qty=6)
    add(client, qty=6)
    with client.session_transaction() as s:
        assert len(s["cart"]) == 1


def test_two_customers_cannot_oversell(app):
    clients = [app.test_client(), app.test_client()]
    for c in clients:
        add(c, qty=7)
        c.get("/checkout")
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(checkout, clients))
    with app.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 2
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10
    operator = app.test_client()
    login(operator)
    post(operator, "/admin/orders", {"id": 1, "status": "Confirmed"})
    post(operator, "/admin/orders", {"id": 2, "status": "Confirmed"})
    with app.app_context():
        assert (
            db()
            .execute("SELECT count(*) FROM orders WHERE status='Confirmed'")
            .fetchone()[0]
            == 1
        )
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 3


def test_cart_update_and_remove(client):
    add(client)
    post(client, "/cart", {"index": 0, "qty": 3})
    assert "11.25" in client.get("/cart").text
    post(client, "/cart", {"index": 0, "remove": 1})
    assert "Your bag is empty." in client.get("/cart").text


def test_status_and_stock_restore_once(client, app):
    add(client, qty=2)
    checkout(client)
    login(client)
    post(client, "/admin/orders", {"id": 1, "status": "Cancelled"})
    post(client, "/admin/orders", {"id": 1, "status": "Cancelled"})
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10
    post(client, "/admin/orders", {"id": 1, "status": "Delivered"})
    with app.app_context():
        assert db().execute("SELECT status FROM orders").fetchone()[0] == "Cancelled"


def test_order_privacy(client, app):
    add(client)
    r = checkout(client)
    assert app.test_client().get(r.location).status_code == 404


def test_login_rate_limit(client):
    for _ in range(5):
        assert (
            post(
                client, "/admin/login", {"username": "operator", "password": "wrong"}
            ).status_code
            == 200
        )
    assert login(client).status_code == 429


def test_disabled_user_session(client, app):
    login(client)
    with app.app_context():
        db().execute("UPDATE users SET active=0")
        db().commit()
    assert client.get("/admin/orders").status_code == 302


def test_admin_catalog_and_content(client, app):
    login(client)
    data = {
        "name": "Created drink",
        "name_ar": "قهوة",
        "description": "<script>alert(1)</script>",
        "kind": "drink",
        "temperature": "hot",
        "active": 0,
        "category_id": 1,
        "position": 0,
    }
    post(client, "/admin/products/0", data)
    with app.app_context():
        pid = db().execute("SELECT max(id) FROM products").fetchone()[0]
    post(
        client,
        f"/admin/products/{pid}/option",
        {"kind": "variant", "label": "Small", "price": "7.17", "active": 1},
    )
    image = io.BytesIO()
    Image.new("RGB", (30, 30), "brown").save(image, "PNG")
    image.seek(0)
    post(
        client,
        "/admin/media",
        {
            "upload": (image, "photo.png"),
            "assign_product": pid,
            "title": "Synthetic photo",
        },
    )
    with app.app_context():
        filename = (
            db().execute("SELECT image FROM products WHERE id=?", (pid,)).fetchone()[0]
        )
    data["image"] = filename
    post(client, f"/admin/products/{pid}", dict(data, active=1))
    html = client.get("/product/" + str(pid)).text
    assert "7.17" in html and "&lt;script&gt;" in html
    post(
        client,
        "/admin/settings",
        {
            "headline": "An edited headline",
            "currency": "EUR",
            "instagram": "javascript:alert(1)",
        },
    )
    with app.app_context():
        assert (
            db()
            .execute("SELECT value FROM settings WHERE key='currency'")
            .fetchone()[0]
            == "USD"
        )
    post(client, "/admin/settings", {"headline": "An edited headline"})
    assert "An edited headline" in client.get("/").text
    post(client, f"/admin/products/{pid}", dict(data, active=0))
    assert client.get("/product/" + str(pid)).status_code == 404


def test_safe_upload_and_usage(client, app):
    login(client)
    post(
        client,
        "/admin/media",
        {"upload": (io.BytesIO(b"<svg onload=alert(1)>"), "x.svg"), "title": "Unsafe"},
    )
    with app.app_context():
        assert db().execute("SELECT count(*) FROM media").fetchone()[0] == 0
    image = io.BytesIO()
    Image.new("RGB", (30, 30), "brown").save(image, "PNG")
    image.seek(0)
    post(
        client,
        "/admin/media",
        {"upload": (image, "../../coffee.png"), "title": "Coffee", "alt": "Cup"},
    )
    with app.app_context():
        m = dict(db().execute("SELECT * FROM media").fetchone())
    assert m["filename"].endswith(".jpg") and "/" not in m["filename"]
    assert client.get("/media/" + m["filename"]).status_code == 200
    post(client, "/admin/settings", {"logo": m["filename"]})
    post(client, "/admin/media", {"id": m["id"], "delete": 1})
    assert client.get("/media/" + m["filename"]).status_code == 200
    post(client, "/admin/settings", {"logo": ""})
    post(client, "/admin/media", {"id": m["id"], "delete": 1})
    assert client.get("/media/" + m["filename"]).status_code == 404


def test_backup_restore_and_migration(app, client):
    add(client)
    checkout(client)
    login(client)
    response = post(client, "/admin/backup")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as z:
        assert "cafe.sqlite3" in z.namelist() and "session.key" not in z.namelist()
    path = Path(app.config["DATA_DIR"]) / "test.zip"
    path.write_bytes(response.data)
    with app.app_context():
        db().execute("DELETE FROM order_history")
        db().execute("DELETE FROM orders")
        db().commit()
    result = app.test_cli_runner().invoke(args=["restore", str(path), "--confirm"])
    assert result.exit_code == 0, result.output
    again = create_app({"TESTING": True, "DATA_DIR": app.config["DATA_DIR"]})
    with again.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 1
        assert (
            db().execute("SELECT max(version) FROM schema_version").fetchone()[0] == 4
        )


def test_retention(client, app):
    add(client)
    checkout(client)
    login(client)
    with app.app_context():
        db().execute("UPDATE orders SET status='Delivered',created='2000-01-01'")
        db().commit()
    post(client, "/admin/retention")
    with app.app_context():
        assert db().execute("SELECT name FROM orders").fetchone()[0] == "[removed]"


def test_port_occupied():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        with pytest.raises(OSError):
            port_available(sock.getsockname()[1])


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1.234", "1000001", "bad"])
def test_money_rejects_invalid(value):
    with pytest.raises(ValueError):
        cents(value)


def test_cookie_security_and_headers(tmp_path):
    app = create_app({"DATA_DIR": str(tmp_path / "secure")})
    r = app.test_client().get("/")
    assert "Secure" in r.headers["Set-Cookie"] and "HttpOnly" in r.headers["Set-Cookie"]
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


def test_protected_storage():
    with pytest.raises(RuntimeError):
        create_app({"DATA_DIR": "/workspace/CAFE-LUX/data"})
    with pytest.raises(RuntimeError):
        create_app({"DATA_DIR": "/tmp/CirrusWorkplace"})


def test_current_price_revalidated(client, app):
    add(client)
    with app.app_context():
        db().execute("UPDATE variants SET price=512 WHERE id=1")
        db().commit()
    checkout(client)
    with app.app_context():
        assert db().execute("SELECT total FROM orders").fetchone()[0] == 762


def test_password_reset_revokes_sessions(client, app):
    login(client)
    other = app.test_client()
    login(other)
    post(
        client,
        "/admin/users",
        {"username": "operator", "password": "another-test-password"},
    )
    assert other.get("/admin/orders").status_code == 302
    assert client.get("/admin/orders").status_code == 302


def test_targeted_customer_deletion(client, app):
    add(client)
    checkout(client)
    login(client)
    post(client, "/admin/orders", {"id": 1, "status": "New", "anonymize": 1})
    with app.app_context():
        assert (
            db().execute("SELECT name FROM orders").fetchone()[0]
            == "Synthetic Customer"
        )
    post(client, "/admin/orders", {"id": 1, "status": "Delivered"})
    post(client, "/admin/orders", {"id": 1, "status": "Delivered", "anonymize": 1})
    with app.app_context():
        assert db().execute("SELECT name FROM orders").fetchone()[0] == "[removed]"


def test_invalid_host_and_unicode_csrf(client):
    assert client.get("/", headers={"Host": "attacker.invalid"}).status_code == 400
    assert (
        client.post("/language", data={"csrf": "غير صالح", "lang": "ar"}).status_code
        == 400
    )


def test_backup_rejects_traversal(app):
    path = Path(app.config["DATA_DIR"]) / "malicious.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("../escaped.txt", "bad")
    result = app.test_cli_runner().invoke(args=["restore", str(path), "--confirm"])
    assert result.exit_code != 0 and "Invalid backup path" in result.output
    assert not (path.parent.parent / "escaped.txt").exists()


def test_concurrent_duplicate_submit(app, client):
    add(client)
    client.get("/checkout")
    with client.session_transaction() as s:
        form = {
            "csrf": s["csrf"],
            "order_token": s["order_token"],
            "name": "Synthetic Customer",
            "phone": "+96171111111",
            "address": "Synthetic test street",
            "building": "Test landmark",
            "area": "1",
        }
    client.post("/checkout", data=form)
    form["confirm"] = "1"
    clones = [app.test_client(), app.test_client()]
    for c in clones:
        c.set_cookie("cafe_lux_session", client.get_cookie("cafe_lux_session").value)
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda c: c.post("/checkout", data=form), clones))
    assert all(r.status_code == 302 for r in responses)
    assert responses[0].location == responses[1].location
    with app.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 1
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10


def test_invalid_session_key_refused(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "session.key").write_text("")
    with pytest.raises(RuntimeError, match="Invalid session key"):
        create_app({"DATA_DIR": str(data)})


def test_data_configuration_required(monkeypatch):
    monkeypatch.delenv("CAFE_LUX_DATA_DIR", raising=False)
    with pytest.raises(RuntimeError, match="Set CAFE_LUX_DATA_DIR"):
        create_app()
