import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from werkzeug.security import generate_password_hash
from cafe import create_app
from cafe.db import db


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATA_DIR": str(tmp_path / "data"),
            "SESSION_COOKIE_SECURE": False,
        }
    )
    with app.app_context():
        conn = db()
        conn.execute(
            "INSERT INTO users(username,password) VALUES (?,?)",
            ("operator", generate_password_hash("test-only-password")),
        )
        conn.execute("INSERT INTO categories(name) VALUES ('Test category')")
        conn.execute(
            "INSERT INTO products(name,name_ar,kind,category_id,active,featured,temperature) VALUES ('TEST Latte','لاتيه تجريبي','drink',1,1,1,'both')"
        )
        conn.execute(
            "INSERT INTO products(name,kind,active,featured,grinds) VALUES ('TEST Ground','ground',1,1,'Fine,Whole beans')"
        )
        conn.execute(
            "INSERT INTO variants(product_id,label,price,stock) VALUES (1,'Regular',375,10)"
        )
        conn.execute(
            "INSERT INTO variants(product_id,label,price,stock) VALUES (1,'Large',610,NULL)"
        )
        for grams, price in [
            (100, 211),
            (200, 397),
            (250, 499),
            (500, 899),
            (1000, 1501),
            (375, 701),
        ]:
            conn.execute(
                "INSERT INTO variants(product_id,label,grams,price) VALUES (2,?,?,?)",
                (str(grams) + " g", grams, price),
            )
        conn.execute(
            "INSERT INTO addons(product_id,name,price) VALUES (1,'TEST extra',125)"
        )
        conn.execute(
            "UPDATE settings SET value='1' WHERE key IN ('ordering','delivery')"
        )
        conn.execute("UPDATE settings SET value='2.50' WHERE key='delivery_fee'")
        conn.execute("INSERT INTO whatsapp_numbers(label,phone,is_default) VALUES ('Synthetic main','+96171123456',1)")
        conn.execute("INSERT INTO delivery_areas(name,fee) VALUES ('Synthetic area',250)")
        conn.commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def post(client, path, data=None):
    client.get("/")
    with client.session_transaction() as s:
        csrf = s["csrf"]
    return client.post(path, data={"csrf": csrf, **(data or {})})


def login(client):
    return post(
        client,
        "/admin/login",
        {"username": "operator", "password": "test-only-password"},
    )


def add(client, variant=1, qty=1, **kw):
    return post(
        client,
        "/cart/add",
        {"variant": str(variant), "qty": str(qty), "temperature": "hot", **kw},
    )


def checkout(client, **kw):
    client.get("/checkout")
    with client.session_transaction() as s:
        token = s["order_token"]
    data = {"order_token": token, "name": "Synthetic Customer", "phone": "+96171111111", "address": "Synthetic test street", "building": "Test landmark", "area": "1", **kw}
    response = post(client, "/checkout", data)
    if response.status_code == 200:
        response = post(client, "/checkout", {**data, "confirm": "1"})
    return response
