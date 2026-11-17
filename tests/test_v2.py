import json
import sqlite3
import subprocess
from urllib.parse import urlsplit, parse_qs
from werkzeug.security import generate_password_hash
from cafe import create_app
from cafe.db import db
from cafe.public import receiver, store_open
from conftest import post, add, checkout, login


def test_separate_catalogs(client):
    assert "TEST Latte" in client.get("/drinks").text
    assert "TEST Ground" not in client.get("/drinks").text
    assert "TEST Ground" in client.get("/coffee").text
    assert "TEST Latte" not in client.get("/coffee").text


def test_review_before_save_and_changed_price_review(client, app):
    add(client)
    client.get("/checkout")
    with client.session_transaction() as s:
        token = s["order_token"]
    details = dict(
        order_token=token,
        name="Synthetic Customer",
        phone="+96171111111",
        address="Test street",
        building="Test building",
        area="1",
    )
    r = post(client, "/checkout", details)
    assert r.status_code == 200 and "Nothing has been submitted yet" in r.text
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()
        db().execute("UPDATE variants SET price=599 WHERE id=1")
        db().commit()
    r = post(client, "/checkout", dict(details, confirm="1"))
    assert r.status_code == 200 and "5.99" in r.text
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()
    r = post(client, "/checkout", dict(details, confirm="1"))
    assert "/order/" in r.location


def test_mixed_cart_whatsapp_message_and_unknown_fee(client, app):
    with app.app_context():
        db().execute("UPDATE delivery_areas SET fee=NULL")
        db().commit()
    add(client, qty=2, addon="1")
    add(client, variant=4, grind="Fine")
    r = checkout(client, notes="Call & wait / شكراً")
    import re, html

    link = html.unescape(
        re.search(r'href="(https://wa.me/[^"]+)"', client.get(r.location).text).group(1)
    )
    parsed = urlsplit(link)
    assert parsed.path == "/96171123456"
    msg = parse_qs(parsed.query)["text"][0]
    assert "2 × TEST Latte" in msg and "TEST extra" in msg
    assert "200 g" in msg and "Fine" in msg
    assert "Delivery: To Be Confirmed" in msg and "Final total to be confirmed" in msg
    assert "Call & wait / شكراً" in msg
    assert "Payment: Cash on Delivery" in msg
    with app.app_context():
        o = db().execute("SELECT * FROM orders").fetchone()
        assert o["subtotal"] == 1397 and o["fee_known"] == 0
        assert o["status"] == "Pending WhatsApp Submission" and o["stock_deducted"] == 0


def test_routing_and_fallback(app, client):
    with app.app_context():
        conn = db()
        conn.execute(
            "INSERT INTO whatsapp_numbers(label,phone,active) VALUES ('Area receiver','+96171111112',1)"
        )
        conn.execute("UPDATE delivery_areas SET whatsapp_id=2")
        conn.commit()
        area = conn.execute("SELECT * FROM delivery_areas").fetchone()
        assert receiver(area)["id"] == 2
        conn.execute("UPDATE whatsapp_numbers SET active=0 WHERE id=2")
        assert receiver(area)["id"] == 1
        conn.execute("UPDATE whatsapp_numbers SET active=0")
        assert receiver(area) is None
        conn.commit()
    add(client)
    checkout(client)
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()


def test_scheduled_closed_pause_and_minimum(app, client):
    add(client)
    with app.app_context():
        conn = db()
        conn.execute(
            "UPDATE settings SET value='00:00' WHERE key IN ('opening','closing')"
        )
        conn.execute("UPDATE settings SET value='1' WHERE key='scheduled'")
        conn.execute(
            "INSERT INTO schedule_slots(label) VALUES ('Synthetic available slot')"
        )
        conn.commit()
    checkout(client)
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()
    checkout(client, slot="999")
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()
    r = checkout(client, slot="1")
    assert "/order/" in r.location
    with app.app_context():
        assert (
            db().execute("SELECT requested_time FROM orders").fetchone()[0]
            == "Synthetic available slot"
        )
        db().execute("UPDATE settings SET value='1' WHERE key='paused'")
        db().commit()
    add(client)
    checkout(client, slot="1")
    with app.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 1


def test_delivery_minimum_and_disabled_area(app, client):
    add(client)
    with app.app_context():
        db().execute("UPDATE delivery_areas SET minimum=1000")
        db().commit()
    checkout(client)
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()
        db().execute("UPDATE delivery_areas SET minimum=0,active=0")
        db().commit()
    checkout(client)
    with app.app_context():
        assert not db().execute("SELECT 1 FROM orders").fetchone()


def test_confirm_deducts_once_and_cancel_restores(client, app):
    add(client, qty=3)
    checkout(client)
    login(client)
    for status in [
        "Received",
        "Confirmed",
        "Confirmed",
        "Preparing",
        "Ready",
        "Out for Delivery",
        "Delivered",
    ]:
        post(client, "/admin/orders", dict(id="1", status=status))
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 7
        assert db().execute("SELECT count(*) FROM order_history").fetchone()[0] == 8
    for _ in range(2):
        post(client, "/admin/orders", dict(id="1", status="Cancelled"))
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10


def test_notification_prepares_only(client, app):
    add(client)
    checkout(client)
    login(client)
    r = client.get("/admin/orders/1/notify/Confirmed")
    assert r.status_code == 302 and r.location.startswith(
        "https://wa.me/96171111111?text="
    )
    with app.app_context():
        assert (
            db().execute("SELECT status FROM orders").fetchone()[0]
            == "Pending WhatsApp Submission"
        )


def test_operations_and_operator_authorization(client, app):
    login(client)
    post(
        client,
        "/admin/operations",
        dict(kind="number", label="Bad number", phone="123", active="1"),
    )
    with app.app_context():
        assert db().execute("SELECT count(*) FROM whatsapp_numbers").fetchone()[0] == 1
    post(
        client,
        "/admin/operations",
        dict(
            kind="number",
            label="Backup",
            phone="+96171111112",
            active="1",
            is_default="1",
        ),
    )
    with app.app_context():
        assert (
            db()
            .execute("SELECT phone FROM whatsapp_numbers WHERE is_default=1")
            .fetchone()[0]
            == "+96171111112"
        )
    post(
        client,
        "/admin/operations",
        dict(
            kind="hours",
            opening="09:00",
            closing="21:00",
            closures="2026-12-25",
            ordering="1",
            scheduled="1",
        ),
    )
    assert client.get("/admin/operations").status_code == 200
    with app.app_context():
        db().execute("UPDATE users SET role='operator'")
        db().commit()
    assert client.get("/admin/orders").status_code == 200
    assert client.get("/admin/operations").status_code == 403
    assert (
        post(client, "/admin/settings", {"headline": "Unauthorized"}).status_code == 403
    )
    assert (
        post(
            client,
            "/admin/users",
            dict(username="attacker", password="fake-password-123"),
        ).status_code
        == 403
    )


def test_category_visibility_and_contacts(client, app):
    login(client)
    post(client, "/admin/categories", dict(id=1, name="Hidden category", position=0))
    assert "TEST Latte" not in client.get("/drinks").text
    assert client.get("/product/1").status_code == 404
    add(client)
    assert "unavailable" in client.get("/cart").text.lower()
    post(
        client,
        "/admin/settings",
        dict(email="synthetic@example.test", visible_email="0"),
    )
    assert "synthetic@example.test" not in client.get("/").text
    post(client, "/admin/settings", dict(visible_email="1"))
    assert "synthetic@example.test" in client.get("/").text


def test_existing_v2_database_migrates_without_data_loss(tmp_path):
    # SCHEMA remains the baseline v1 DDL; migrations evolve it additively.
    from cafe.db import SCHEMA

    data = tmp_path / "legacy"
    data.mkdir()
    conn = sqlite3.connect(data / "cafe.sqlite3")
    conn.executescript(SCHEMA)
    conn.execute(
        "ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1"
    )
    conn.executemany("INSERT INTO schema_version VALUES (?)", [(1,), (2,)])
    conn.execute("INSERT INTO products(name,kind) VALUES ('Existing coffee','ground')")
    conn.execute(
        "INSERT INTO orders(reference,token,name,phone,fulfillment,currency,subtotal,delivery,total,items,status) VALUES ('OLD-TEST','test-token','Synthetic','+96171111111','delivery','USD',100,0,100,'[]','Completed')"
    )
    conn.commit()
    conn.close()
    for _ in range(2):
        migrated = create_app({"DATA_DIR": str(data), "TESTING": True})
        with migrated.app_context():
            assert (
                db().execute("SELECT name FROM products").fetchone()[0]
                == "Existing coffee"
            )
            assert (
                db().execute("SELECT status FROM orders").fetchone()[0] == "Delivered"
            )
            assert (
                db().execute("SELECT max(version) FROM schema_version").fetchone()[0]
                == 4
            )


def test_variant_restrictions_and_exclusive_extras(client, app):
    with app.app_context():
        db().execute("UPDATE variants SET allowed_grinds='Whole beans' WHERE id=4")
        db().execute("UPDATE addons SET option_group='Milk' WHERE id=1")
        db().execute(
            "INSERT INTO addons(product_id,name,price,option_group) VALUES (1,'Other milk',50,'Milk')"
        )
        db().commit()
    add(client, variant=4, grind="Fine")
    with client.session_transaction() as s:
        assert not s.get("cart")
    add(client, variant=4, grind="Whole beans")
    add(client, addon=["1", "2"])
    with client.session_transaction() as s:
        assert len(s["cart"]) == 1


def test_wsgi_import_and_diagnostics(app, monkeypatch):
    monkeypatch.setenv("CAFE_LUX_DATA_DIR", app.config["DATA_DIR"])
    import runpy

    runpy.run_path("scripts/diagnose.py", run_name="__main__")
    assert callable(create_app().wsgi_app)


def test_management_entrypoint(tmp_path):
    import os, sys, secrets

    environment = {**os.environ, "CAFE_LUX_DATA_DIR": str(tmp_path / "cli-data")}
    for args in [
        ["init-db"],
        [
            "init-admin",
            "--username",
            "synthetic-admin",
            "--password",
            secrets.token_urlsafe(24),
        ],
    ]:
        result = subprocess.run(
            [sys.executable, "manage.py", *args],
            env=environment,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_cancellation_restores_only_actual_deductions(client, app):
    add(client, variant=2)
    checkout(client)
    login(client)
    post(client, "/admin/orders", dict(id=1, status="Confirmed"))
    with app.app_context():
        db().execute("UPDATE variants SET stock=5 WHERE id=2")
        db().commit()
    post(client, "/admin/orders", dict(id=1, status="Cancelled"))
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=2").fetchone()[0] == 5
