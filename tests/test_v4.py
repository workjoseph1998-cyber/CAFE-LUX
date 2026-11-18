import hashlib
import hmac
import json
import re
import time
from pathlib import Path
import pytest
from cafe.db import db
from cafe.whatsapp import process_one, DeliveryError
from conftest import post, login, add, checkout


def register(client, name="customer-one"):
    r = post(
        client,
        "/account/register",
        {"username": name, "password": "synthetic-long-password"},
    )
    assert r.status_code == 200
    codes = re.findall(r"<code>([0-9a-f]{24})</code>", r.text)
    assert len(codes) == 3
    return codes


def order(client, app, consent="1"):
    add(client)
    response = checkout(client, whatsapp_opt_in=consent)
    assert response.status_code == 302
    with app.app_context():
        return dict(
            db().execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1").fetchone()
        )


def config(app, monkeypatch, mode="mock"):
    monkeypatch.setenv("CAFE_LUX_WHATSAPP_MODE", mode)
    monkeypatch.setenv("META_APP_SECRET", "synthetic-secret")
    monkeypatch.setenv("META_WHATSAPP_VERIFY_TOKEN", "synthetic-verify")
    monkeypatch.setenv("META_ACCESS_TOKEN", "synthetic-token")
    monkeypatch.setenv("META_GRAPH_VERSION", "v23.0")
    monkeypatch.setenv("META_WABA_ID", "5678")
    with app.app_context():
        conn = db()
        conn.execute("UPDATE whatsapp_numbers SET cloud_phone_id='1234'")
        conn.execute("UPDATE settings SET value='1' WHERE key='wa_automation'")
        conn.execute(
            "UPDATE settings SET value='synthetic_template' WHERE key LIKE 'wa_confirmed_%' OR key LIKE 'wa_out_%'"
        )
        conn.commit()


def webhook(client, app, o, **kw):
    message = {
        "id": "wamid.synthetic",
        "from": o["phone"].lstrip("+"),
        "timestamp": str(int(time.time())),
        "type": "text",
        "text": {"body": o["reference"]},
    }
    message.update(kw)
    data = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "5678",
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "1234"},
                            "messages": [message],
                        }
                    }
                ],
            }
        ],
    }
    raw = json.dumps(data).encode()
    sig = "sha256=" + hmac.new(b"synthetic-secret", raw, hashlib.sha256).hexdigest()
    return client.post(
        "/integrations/whatsapp/webhook",
        data=raw,
        content_type="application/json",
        headers={"X-Hub-Signature-256": sig},
    )


def test_accounts_isolation_recovery_no_phone_link(app, client):
    guest = order(client, app)
    codes = register(client)
    assert guest["reference"] not in client.get("/account").text
    own = order(client, app)
    assert own["reference"] in client.get("/account").text
    other = app.test_client()
    register(other, "customer-two")
    assert other.get("/order/" + own["reference"]).status_code == 404
    assert post(other, "/account/reorder/" + str(own["id"])).status_code == 404
    # A recovery code is one time and invalidates every existing session.
    recovery = app.test_client()
    result = post(
        recovery,
        "/account/recover",
        {
            "username": "customer-one",
            "recovery": codes[0],
            "password": "another-long-password",
        },
    )
    assert result.status_code == 302
    assert client.get("/account").status_code == 302
    assert (
        post(
            recovery,
            "/account/recover",
            {
                "username": "customer-one",
                "recovery": codes[0],
                "password": "changed-long-password",
            },
        ).status_code
        == 200
    )
    with app.app_context():
        assert (
            db()
            .execute("SELECT count(*) FROM customer_recovery WHERE used=1")
            .fetchone()[0]
            == 1
        )
        assert all(
            codes[0] not in r[0]
            for r in db().execute("SELECT hash FROM customer_recovery")
        )


def test_favorites_merge_and_visibility(app, client):
    post(client, "/favorites/1")
    assert "TEST Latte" in client.get("/favorites").text
    register(client)
    with app.app_context():
        assert db().execute("SELECT count(*) FROM favorites").fetchone()[0] == 1
        db().execute("UPDATE products SET active=0 WHERE id=1")
        db().commit()
    assert "TEST Latte" not in client.get("/favorites").text
    assert post(client, "/favorites/1").status_code == 404


def test_addresses_cannot_read_or_delete_other_customer(app, client):
    register(client)
    post(
        client,
        "/account",
        {
            "action": "address",
            "label": "Private home",
            "area": "1",
            "address": "Private street",
            "building": "Private building",
        },
    )
    other = app.test_client()
    register(other, "another-account")
    post(other, "/account", {"action": "delete_address", "id": "1"})
    add(other)
    assert "Private street" not in other.get("/checkout?address=1").text
    with app.app_context():
        assert (
            db().execute("SELECT count(*) FROM customer_addresses").fetchone()[0] == 1
        )


def test_reorder_uses_current_price_and_stock(app, client):
    register(client)
    o = order(client, app)
    with app.app_context():
        db().execute("UPDATE variants SET price=999 WHERE id=1")
        db().commit()
    post(client, "/account/reorder/" + str(o["id"]))
    assert "9.99" in client.get("/cart").text
    with app.app_context():
        db().execute("UPDATE variants SET stock=0 WHERE id=1")
        db().commit()
    post(client, "/cart", {"clear": "1"})
    post(client, "/account/reorder/" + str(o["id"]))
    with client.session_transaction() as s:
        assert s["cart"] == []


def test_promotion_server_amount_and_usage_race(app, client):
    with app.app_context():
        db().execute(
            "INSERT INTO promotions(code,kind,value,active,usage_limit) VALUES('TEST','percent',20,1,1)"
        )
        db().commit()
    add(client, qty=2)
    post(client, "/cart/promotion", {"code": "TEST"})
    checkout(client, discount="99999")
    with app.app_context():
        o = db().execute("SELECT * FROM orders").fetchone()
        assert o["subtotal"] == 750 and o["discount"] == 150 and o["total"] == 850
    other = app.test_client()
    add(other)
    post(other, "/cart/promotion", {"code": "TEST"})
    with other.session_transaction() as s:
        assert not s.get("promotion")
    # Cancellation releases a use.
    login(client)
    post(client, "/admin/orders", {"id": "1", "status": "Cancelled"})
    post(other, "/cart/promotion", {"code": "TEST"})
    with other.session_transaction() as s:
        assert s["promotion"] == "TEST"


def test_bundle_aggregate_stock_and_cancel_exact_once(app, client):
    with app.app_context():
        db().execute("INSERT INTO bundles(name,price,active) VALUES('Test pair',500,1)")
        db().execute(
            "INSERT INTO bundle_items(bundle_id,variant_id,qty,temperature) VALUES(1,1,2,'hot')"
        )
        db().commit()
    post(client, "/bundles/1/add", {"qty": "2"})
    add(client, qty=7)  # combined eleven must reject
    with client.session_transaction() as s:
        assert len(s["cart"]) == 1
    checkout(client)
    login(client)
    post(client, "/admin/orders", {"id": "1", "status": "Confirmed"})
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 6
        assert db().execute("SELECT total FROM orders").fetchone()[0] == 1250
    post(client, "/admin/orders", {"id": "1", "status": "Cancelled"})
    post(client, "/admin/orders", {"id": "1", "status": "Cancelled"})
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 10
        assert (
            db().execute("SELECT count(*) FROM inventory_movements").fetchone()[0] == 2
        )


def test_webhook_signature_matching_duplicates(app, client, monkeypatch):
    config(app, monkeypatch)
    o = order(client, app)
    assert client.post("/integrations/whatsapp/webhook", json={}).status_code == 403
    assert (
        client.get(
            "/integrations/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=synthetic-verify&hub.challenge=123"
        ).text
        == "123"
    )
    assert webhook(client, app, o).status_code == 200
    assert webhook(client, app, o).status_code == 200
    with app.app_context():
        assert db().execute("SELECT status FROM orders").fetchone()[0] == "Received"
        assert db().execute("SELECT count(*) FROM whatsapp_incoming").fetchone()[0] == 1
        assert db().execute("SELECT count(*) FROM whatsapp_jobs").fetchone()[0] == 0


@pytest.mark.parametrize(
    "override",
    [
        {"from": "96170000000"},
        {"text": {"body": "No reference"}},
        {"timestamp": "1"},
        {"text": {"body": "LUX-000000000000 LUX-111111111111"}},
    ],
)
def test_webhook_unmatched_review_only(app, client, monkeypatch, override):
    config(app, monkeypatch)
    o = order(client, app)
    assert webhook(client, app, o, **override).status_code == 200
    with app.app_context():
        assert (
            db().execute("SELECT status FROM orders").fetchone()[0]
            == "Pending WhatsApp Submission"
        )
        assert (
            db().execute("SELECT state FROM whatsapp_incoming").fetchone()[0]
            == "manual_review"
        )


def test_exact_two_automatic_triggers_and_mock_never_sent(app, client, monkeypatch):
    config(app, monkeypatch)
    order(client, app)
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
        post(client, "/admin/orders", {"id": "1", "status": status})
    with app.app_context():
        assert [
            r[0] for r in db().execute("SELECT kind FROM whatsapp_jobs ORDER BY id")
        ] == ["Confirmed", "Out for Delivery"]
        process_one()
        process_one()
        assert all(
            r[0] == "mocked" and r[1] is None
            for r in db().execute("SELECT state,message_id FROM whatsapp_jobs")
        )


def test_no_opt_in_no_queue(app, client, monkeypatch):
    config(app, monkeypatch)
    order(client, app, consent="")
    login(client)
    post(client, "/admin/orders", {"id": "1", "status": "Confirmed"})
    with app.app_context():
        assert db().execute("SELECT count(*) FROM whatsapp_jobs").fetchone()[0] == 0


def test_worker_retry_and_unknown_outcome(app, client, monkeypatch):
    config(app, monkeypatch, "live")
    order(client, app)
    login(client)
    post(client, "/admin/orders", {"id": "1", "status": "Confirmed"})
    calls = []

    def rejected(path, payload):
        if payload is None:
            return {
                "data": [
                    {
                        "name": "synthetic_template",
                        "language": "en",
                        "status": "APPROVED",
                        "components": [{"type": "BODY", "text": "Order {{1}}"}],
                    }
                ]
            }
        calls.append(payload)
        raise DeliveryError("retry", "HTTP 429")

    app.config["WHATSAPP_TRANSPORT"] = rejected
    with app.app_context():
        process_one()
        assert db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "retry"
        db().execute("UPDATE whatsapp_jobs SET due=0")
        db().commit()

        def uncertain(path, payload):
            if payload is None:
                return {
                    "data": [
                        {
                            "name": "synthetic_template",
                            "language": "en",
                            "status": "APPROVED",
                            "components": [{"type": "BODY", "text": "Order {{1}}"}],
                        }
                    ]
                }
            raise DeliveryError("uncertain", "Timeout")

        app.config["WHATSAPP_TRANSPORT"] = uncertain
        process_one()
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "uncertain"
        )
        assert process_one() is False
    assert len(calls) == 1


@pytest.mark.parametrize(
    "path",
    [
        "/account/login",
        "/account/register",
        "/account/recover",
        "/favorites",
        "/bundles",
        "/admin/inventory",
        "/admin/customers",
        "/admin/promotions",
        "/admin/bundles",
        "/admin/website",
        "/admin/website/preview",
        "/admin/whatsapp",
        "/admin/reports",
    ],
)
def test_new_pages(app, client, path):
    if path.startswith("/admin"):
        assert client.get(path).status_code == 302
        login(client)
    response = client.get(path)
    assert response.status_code == 200
    if path.startswith(("/account", "/favorites", "/admin")):
        assert response.headers["Cache-Control"] == "no-store"


def test_area_receiver_without_default_available(app, client):
    with app.app_context():
        db().execute("UPDATE whatsapp_numbers SET is_default=0")
        db().execute("UPDATE delivery_areas SET whatsapp_id=1")
        db().commit()
    add(client)
    assert "Review your order" in client.get("/checkout").text
    assert checkout(client).status_code == 302


def test_inventory_and_draft_publish(app, client):
    login(client)
    post(
        client,
        "/admin/inventory",
        {
            "id": "1",
            "stock": "25",
            "low_threshold": "4",
            "reason": "Test restock",
            "unit_cost": "1.00",
        },
    )
    with app.app_context():
        assert db().execute("SELECT stock FROM variants WHERE id=1").fetchone()[0] == 25
        assert db().execute("SELECT delta FROM inventory_movements").fetchone()[0] == 15
    post(
        client,
        "/admin/website",
        {
            "headline": "Private draft headline",
            "home_sections": "drinks,story",
            "action": "draft",
        },
    )
    assert "Private draft headline" not in client.get("/").text
    assert "Private draft headline" in client.get("/admin/website/preview").text
    post(
        client,
        "/admin/website",
        {
            "headline": "Published headline",
            "home_sections": "drinks",
            "action": "publish",
        },
    )
    assert "Published headline" in client.get("/").text


def test_template_approval_required_and_transport_submission(app, client, monkeypatch):
    config(app, monkeypatch, "live")
    order(client, app)
    login(client)
    post(client, "/admin/orders", {"id": "1", "status": "Confirmed"})
    calls = []

    def adapter(path, payload):
        calls.append((path, payload))
        return {
            "data": [
                {
                    "name": "synthetic_template",
                    "language": "en",
                    "status": "PENDING",
                    "components": [{"type": "BODY", "text": "Order {{1}}"}],
                }
            ]
        }

    app.config["WHATSAPP_TRANSPORT"] = adapter
    with app.app_context():
        process_one()
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "blocked"
        )
        assert len(calls) == 1 and calls[0][1] is None
    post(client, "/admin/whatsapp", {"action": "retry", "id": "1"})

    def approved(path, payload):
        if payload is None:
            return {
                "data": [
                    {
                        "name": "synthetic_template",
                        "language": "en",
                        "status": "APPROVED",
                        "components": [{"type": "BODY", "text": "Order {{1}}"}],
                    }
                ]
            }
        calls.append((path, payload))
        return {"messages": [{"id": "wamid.provider-one"}]}

    app.config["WHATSAPP_TRANSPORT"] = approved
    with app.app_context():
        process_one()
        job = dict(db().execute("SELECT * FROM whatsapp_jobs").fetchone())
        assert job["state"] == "submitted" and job["message_id"] == "wamid.provider-one"
        from cafe.whatsapp import update_status

        # Receiver ID binds statuses too; no stale callback can lower read to sent.
        update_status(
            {"id": "wamid.provider-one", "status": "delivered"}, "wrong-phone"
        )
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "submitted"
        )
        for status in ["delivered", "read", "sent", "failed", "read"]:
            update_status({"id": "wamid.provider-one", "status": status}, "1234")
        db().commit()
        assert db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "read"
        assert db().execute("SELECT count(*) FROM whatsapp_events").fetchone()[0] == 4
    assert calls[-1][1]["template"]["components"][0]["parameters"][0][
        "text"
    ].startswith("LUX-")
    assert "ACCESS_TOKEN" not in json.dumps(calls)


def test_worker_crash_boundaries_and_opt_out(app, client, monkeypatch):
    config(app, monkeypatch)
    o = order(client, app)
    staff = app.test_client()
    login(staff)
    post(staff, "/admin/orders", {"id": "1", "status": "Confirmed"})
    with app.app_context():
        db().execute(
            "UPDATE whatsapp_jobs SET state='processing',lease_until=1,request_started=1"
        )
        db().commit()
        assert process_one() is False
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "uncertain"
        )
    post(staff, "/admin/whatsapp", {"action": "retry", "id": "1"})
    with app.app_context():
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "uncertain"
        )
    post(staff, "/admin/whatsapp", {"action": "retry", "id": "1", "reconciled": "1"})
    post(client, "/order/" + o["reference"] + "/opt-out")
    with app.app_context():
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "cancelled"
        )
        assert db().execute("SELECT whatsapp_opt_in FROM orders").fetchone()[0] == 0


def test_reports_currency_costs_and_customer_privacy(app, client):
    register(client)
    post(
        client,
        "/account",
        {
            "action": "profile",
            "name": "Private Customer",
            "phone": "+96171111111",
            "email": "synthetic@example.test",
        },
    )
    o = order(client, app)
    login(client)
    post(client, "/admin/orders", {"id": str(o["id"]), "status": "Delivered"})
    with app.app_context():
        db().execute(
            "INSERT INTO orders(reference,token,status,name,phone,fulfillment,currency,subtotal,delivery,total,items) VALUES('FOREIGN','foreign-token','Delivered','Other','Other','delivery','EUR',99999,0,99999,'[]')"
        )
        db().commit()
    report = client.get("/admin/reports?currency=USD").text
    assert "3.75" in report and "999.99" not in report
    assert "Unavailable: incomplete historical costs" in report
    assert "synthetic@example.test" in client.get("/admin/customers/1").text
    post(client, "/admin/customers/1", {"action": "erase"})
    assert client.get("/account").status_code == 302
    with app.app_context():
        c = db().execute("SELECT * FROM customers").fetchone()
        assert not c["email"] and not c["active"]
        assert (
            db()
            .execute("SELECT phone FROM orders WHERE id=?", (o["id"],))
            .fetchone()[0]
            == "[removed]"
        )


def test_v4_private_backup_roundtrip(app, client, tmp_path):
    import zipfile
    import sqlite3

    register(client)
    post(client, "/favorites/1")
    order(client, app)
    result = app.test_cli_runner().invoke(args=["backup"])
    assert result.exit_code == 0, result.output
    archives = list((Path(app.config["DATA_DIR"]) / "backups").glob("*.zip"))
    assert archives
    with zipfile.ZipFile(max(archives, key=lambda p: p.stat().st_mtime)) as z:
        z.extract("cafe.sqlite3", tmp_path)
        assert not any("session.key" in n or "env" in n for n in z.namelist())
    with sqlite3.connect(tmp_path / "cafe.sqlite3") as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT count(*) FROM customers").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM favorites").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
        assert (
            conn.execute("SELECT max(version) FROM schema_version").fetchone()[0] == 5
        )


def test_rate_limits_and_csrf_on_new_routes(app, client):
    assert client.post("/account/register").status_code == 400
    assert client.post("/favorites/1").status_code == 400
    for _ in range(10):
        assert (
            post(
                client, "/account/login", {"username": "unknown", "password": "wrong"}
            ).status_code
            == 200
        )
    assert (
        post(
            client, "/account/login", {"username": "unknown", "password": "wrong"}
        ).status_code
        == 429
    )


def test_concurrent_promotion_last_use_is_atomic(app):
    from concurrent.futures import ThreadPoolExecutor

    clients = [app.test_client(), app.test_client()]
    with app.app_context():
        db().execute(
            "INSERT INTO promotions(code,kind,value,active,usage_limit) VALUES('LASTUSE','fixed',100,1,1)"
        )
        db().commit()
    forms = []
    for c in clients:
        add(c)
        post(c, "/cart/promotion", {"code": "LASTUSE"})
        c.get("/checkout")
        with c.session_transaction() as s:
            token = s["order_token"]
        data = {
            "order_token": token,
            "name": "Synthetic concurrent",
            "phone": "+96171111111",
            "address": "Synthetic street",
            "building": "Synthetic building",
            "area": "1",
        }
        assert post(c, "/checkout", data).status_code == 200
        forms.append({**data, "confirm": "1"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda i: post(clients[i], "/checkout", forms[i]), range(2))
        )
    assert sum("/order/LUX-" in r.location for r in results) == 1
    with app.app_context():
        assert db().execute("SELECT count(*) FROM orders").fetchone()[0] == 1


def test_full_customer_backup_cli_restore(app, client, tmp_path):
    register(client)
    post(client, "/favorites/1")
    order(client, app)
    assert app.test_cli_runner().invoke(args=["backup"]).exit_code == 0
    backup = max(
        (Path(app.config["DATA_DIR"]) / "backups").glob("*.zip"),
        key=lambda p: p.stat().st_mtime,
    )
    with app.app_context():
        db().execute("UPDATE customers SET name='Changed after backup'")
        db().execute("DELETE FROM favorites")
        db().commit()
    result = app.test_cli_runner().invoke(args=["restore", str(backup), "--confirm"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db().execute("SELECT name FROM customers").fetchone()[0] == ""
        assert db().execute("SELECT count(*) FROM favorites").fetchone()[0] == 1
        assert db().execute("PRAGMA foreign_key_check").fetchall() == []


def test_account_logout_and_shared_browser_never_leave_order_grants(app, client):
    register(client)
    own = order(client, app)
    assert client.get("/order/" + own["reference"]).status_code == 200
    post(client, "/account/logout")
    assert client.get("/order/" + own["reference"]).status_code == 404
    assert post(client, "/order/" + own["reference"] + "/opt-out").status_code == 404
    register(client, "next-shared-browser-user")
    assert client.get("/order/" + own["reference"]).status_code == 404
    assert post(client, "/account/reorder/" + str(own["id"])).status_code == 404


def test_late_callback_from_old_attempt_cannot_deliver_a_new_retry(
    app, client, monkeypatch
):
    config(app, monkeypatch)
    order(client, app)
    login(client)
    post(client, "/admin/orders", {"id": "1", "status": "Confirmed"})
    with app.app_context():
        db().execute(
            "UPDATE whatsapp_jobs SET state='failed',message_id='wamid.old-attempt'"
        )
        old_key = db().execute("SELECT job_key FROM whatsapp_jobs").fetchone()[0]
        db().commit()
    post(client, "/admin/whatsapp", {"action": "retry", "id": "1"})
    with app.app_context():
        job = db().execute("SELECT * FROM whatsapp_jobs").fetchone()
        assert job["job_key"] != old_key and job["message_id"] is None
        from cafe.whatsapp import update_status

        update_status(
            {
                "id": "wamid.old-attempt",
                "status": "delivered",
                "biz_opaque_callback_data": old_key,
            },
            "1234",
        )
        db().commit()
        assert (
            db().execute("SELECT state FROM whatsapp_attempts").fetchone()[0]
            == "delivered"
        )
        assert (
            db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0] == "cancelled"
        )
        assert (
            db().execute("SELECT message_id FROM whatsapp_jobs").fetchone()[0] is None
        )
        assert process_one() is False
