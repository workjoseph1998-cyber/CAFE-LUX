import importlib.util
import io
import json
import os
import runpy
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path
import pytest
from PIL import Image
from cafe import create_app
from cafe.db import db, LATEST_SCHEMA
from cafe.starter_catalog import seed_catalog, DRINKS, COFFEE
from conftest import add, checkout, post, login


@pytest.fixture
def empty_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATA_DIR": str(tmp_path / "empty-data"),
            "SESSION_COOKIE_SECURE": False,
        }
    )


def seed(app, dry=False):
    with app.app_context():
        return seed_catalog(dry_run=dry)


def test_approved_catalog_counts_and_no_facts_or_prices(empty_app):
    seed(empty_app)
    with empty_app.app_context():
        conn = db()
        assert conn.execute("SELECT count(*) FROM categories").fetchone()[0] == 8
        assert (
            conn.execute("SELECT count(*) FROM products WHERE kind='drink'").fetchone()[
                0
            ]
            == 18
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM products WHERE kind='ground'"
            ).fetchone()[0]
            == 4
        )
        assert not conn.execute(
            "SELECT 1 FROM products WHERE active!=0 OR featured!=0 OR image!=''"
        ).fetchone()
        assert not conn.execute(
            "SELECT 1 FROM variants WHERE price IS NOT NULL OR stock IS NOT NULL OR active!=0"
        ).fetchone()
        assert not conn.execute(
            "SELECT 1 FROM products WHERE origin!='' OR roast!='' OR bean!='' OR notes!=''"
        ).fetchone()
        assert conn.execute("SELECT count(*) FROM variants").fetchone()[0] == 62
        assert {
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT grams FROM variants WHERE grams IS NOT NULL"
            )
        } == {200, 500, 1000}
        assert all(
            r[0] == 6
            for r in conn.execute(
                "SELECT count(*) FROM variants v JOIN products p ON p.id=v.product_id WHERE p.kind='ground' GROUP BY p.id"
            )
        )
        assert not conn.execute(
            "SELECT 1 FROM addons WHERE active!=0 OR price_pending!=1"
        ).fetchone()
        for category, title, items in DRINKS:
            for slug, name, desc, size, temp in items:
                product = conn.execute(
                    "SELECT * FROM products WHERE name=?", (name,)
                ).fetchone()
                assert product["temperature"] == temp and product["description"] == desc
                assert conn.execute(
                    "SELECT count(*) FROM variants WHERE product_id=?", (product["id"],)
                ).fetchone()[0] == (1 if size == "single" else 3)
        traditional = conn.execute(
            "SELECT id FROM products WHERE name='Turkish Coffee'"
        ).fetchone()[0]
        assert [
            r[0]
            for r in conn.execute(
                "SELECT name FROM addons WHERE product_id=?", (traditional,)
            )
        ] == ["No sugar", "Less sugar", "Regular sugar", "Extra sugar"]


def test_seed_idempotency_preserves_admin_edits_and_removals(empty_app):
    seed(empty_app)
    with empty_app.app_context():
        c = db()
        c.execute(
            "UPDATE products SET name='Owner changed name',description='Owner recipe',position=99 WHERE id=1"
        )
        c.execute(
            "UPDATE variants SET label='Owner size',price=717,stock=17,sku='OWNER',position=33,active=1 WHERE id=1"
        )
        c.execute(
            "UPDATE addons SET name='Owner extra',price=155,price_pending=0,active=1 WHERE id=1"
        )
        c.execute("UPDATE categories SET name='Owner category',position=70 WHERE id=1")
        c.execute("DELETE FROM addons WHERE product_id=2")
        c.execute("DELETE FROM variants WHERE product_id=2")
        c.execute("DELETE FROM products WHERE id=2")
        c.commit()
        before = {
            t: [tuple(r) for r in c.execute("SELECT * FROM " + t)]
            for t in ["products", "variants", "addons", "categories"]
        }
    seed(empty_app)
    with empty_app.app_context():
        for t, rows in before.items():
            assert [tuple(r) for r in db().execute("SELECT * FROM " + t)] == rows
        assert (
            len(
                list(
                    (Path(empty_app.config["DATA_DIR"]) / "backups").glob(
                        "pre-starter-catalog-*.sqlite3"
                    )
                )
            )
            == 2
        )


def test_dry_run_and_similar_name_conflicts(empty_app):
    with empty_app.app_context():
        c = db()
        c.execute(
            "INSERT INTO products(name,kind,description) VALUES ('ESPRESSO','drink','Owner recipe')"
        )
        c.commit()
        before = [tuple(r) for r in c.execute("SELECT * FROM products")]
    result = seed(empty_app, True)
    assert any("CONFLICT product" in r for r in result)
    with empty_app.app_context():
        assert [tuple(r) for r in db().execute("SELECT * FROM products")] == before
        assert db().execute("SELECT count(*) FROM categories").fetchone()[0] == 0
    seed(empty_app)
    with empty_app.app_context():
        assert (
            db().execute("SELECT description FROM products WHERE id=1").fetchone()[0]
            == "Owner recipe"
        )
        assert (
            db()
            .execute("SELECT count(*) FROM products WHERE starter_key IS NOT NULL")
            .fetchone()[0]
            == 21
        )


def test_seed_preserves_existing_orders_users_uploads_and_settings(app, client):
    add(client)
    checkout(client)
    with app.app_context():
        conn = db()
        conn.execute(
            "INSERT INTO media(filename,title) VALUES ('existing.jpg','Owner photo')"
        )
        conn.commit()
        uploaded = Path(app.config["DATA_DIR"]) / "uploads" / "existing.jpg"
        uploaded.write_bytes(b"owner-image-bytes")
        tables = [
            "users",
            "orders",
            "order_history",
            "settings",
            "media",
            "products",
            "variants",
            "addons",
        ]
        before = {
            t: [tuple(r) for r in conn.execute("SELECT * FROM " + t)] for t in tables
        }
        result = seed_catalog()
        for t, rows in before.items():
            after = [tuple(r) for r in conn.execute("SELECT * FROM " + t)]
            assert after[: len(rows)] == rows
        assert uploaded.read_bytes() == b"owner-image-bytes"
        backup = next(
            (Path(app.config["DATA_DIR"]) / "backups").glob(
                "pre-starter-catalog-*.sqlite3"
            )
        )
        with sqlite3.connect(backup) as copy:
            assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert copy.execute("SELECT count(*) FROM orders").fetchone()[0] == 1


def test_drafts_hidden_and_unorderable(empty_app):
    seed(empty_app)
    client = empty_app.test_client()
    for path in ["/", "/drinks", "/coffee", "/shop?q=Espresso"]:
        html = client.get(path).text
        assert "LUX Signature Blend" not in html and "Double Espresso" not in html
    with empty_app.app_context():
        products = db().execute("SELECT * FROM products").fetchall()
        variants = db().execute("SELECT * FROM variants").fetchall()
    for p in products:
        assert client.get("/product/" + str(p["id"])).status_code == 404
    for v in variants:
        post(
            client,
            "/cart/add",
            dict(variant=v["id"], qty=1, temperature="hot", grind=v["allowed_grinds"]),
        )
        with client.session_transaction() as session:
            assert not session.get("cart")


def upload(client, pid):
    image = io.BytesIO()
    Image.new("RGB", (40, 40), "brown").save(image, "PNG")
    image.seek(0)
    return post(
        client,
        "/admin/media",
        {
            "upload": (image, "synthetic.png"),
            "assign_product": pid,
            "title": "Synthetic photo",
        },
    )


def product_data(p, **changes):
    keys = [
        "name",
        "name_ar",
        "description",
        "description_ar",
        "kind",
        "category_id",
        "image",
        "temperature",
        "grinds",
        "position",
    ]
    return {**{k: p[k] if p[k] is not None else "" for k in keys}, **changes}


def test_publication_validation_editor_quick_bulk(app, client):
    seed(app)
    login(client)
    with app.app_context():
        p = dict(
            db()
            .execute("SELECT * FROM products WHERE name='Double Espresso'")
            .fetchone()
        )
        vid = (
            db()
            .execute("SELECT id FROM variants WHERE product_id=?", (p["id"],))
            .fetchone()[0]
        )
    pid = p["id"]
    post(client, f"/admin/products/{pid}", product_data(p, active=1))
    post(client, f"/admin/products/{pid}/quick", dict(active=1, position=0))
    post(client, "/admin/products/bulk", dict(ids=[str(pid), "1"], action="publish"))
    assert client.get(f"/product/{pid}").status_code == 404
    upload(client, pid)
    post(
        client,
        f"/admin/products/{pid}/option",
        dict(
            id=vid,
            kind="variant",
            label="Single serving",
            price="2.75",
            active=1,
            position=1,
            sku="SYNTHETIC",
        ),
    )
    with app.app_context():
        p = dict(db().execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone())
    post(client, f"/admin/products/{pid}", product_data(p, intent="publish"))
    assert client.get(f"/product/{pid}").status_code == 200
    assert (
        "Double Espresso" in client.get("/drinks").text
        and "Double Espresso" not in client.get("/coffee").text
    )
    # Disabling its last sale option cannot leave a published product invalid.
    post(
        client,
        f"/admin/products/{pid}/option",
        dict(id=vid, kind="variant", label="Single serving", price="2.75"),
    )
    with app.app_context():
        assert (
            db().execute("SELECT active FROM variants WHERE id=?", (vid,)).fetchone()[0]
            == 1
        )
    post(client, "/admin/products/bulk", dict(ids=[str(pid)], action="draft"))
    assert client.get(f"/product/{pid}").status_code == 404


def test_pending_extras_never_become_free_sales(app, client):
    seed(app)
    login(client)
    with app.app_context():
        p = db().execute("SELECT * FROM products WHERE name='Caffè Latte'").fetchone()
        aid = (
            db()
            .execute(
                "SELECT id FROM addons WHERE product_id=? AND name='Oat milk'",
                (p["id"],),
            )
            .fetchone()[0]
        )
        pid = p["id"]
    post(
        client,
        f"/admin/products/{pid}/option",
        dict(id=aid, kind="addon", name="Oat milk", option_group="Milk", active=1),
    )
    with app.app_context():
        a = db().execute("SELECT * FROM addons WHERE id=?", (aid,)).fetchone()
        assert not a["active"] and a["price_pending"]
    post(
        client,
        f"/admin/products/{pid}/option",
        dict(
            id=aid,
            kind="addon",
            name="Oat milk",
            option_group="Milk",
            price="0",
            active=1,
        ),
    )
    with app.app_context():
        a = db().execute("SELECT * FROM addons WHERE id=?", (aid,)).fetchone()
        assert a["active"] and not a["price_pending"] and a["price"] == 0


def test_catalog_filters_pagination_and_role_enforcement(app, client):
    seed(app)
    login(client)
    html = client.get("/admin/drinks?status=draft&q=Iced&sort=name").text
    assert "Iced Mocha" in html and "LUX Golden Roast" not in html
    html = client.get("/admin/coffee?status=draft").text
    assert "LUX Golden Roast" in html and "Cappuccino" not in html
    assert "Missing image" in html and "Missing price" in html
    with app.app_context():
        for n in range(50):
            db().execute(
                "INSERT INTO products(name,kind) VALUES (?,'drink')",
                (f"Pagination synthetic {n}",),
            )
        db().commit()
    assert "30 shown" in client.get("/admin/drinks").text
    with app.app_context():
        db().execute("UPDATE users SET role='operator'")
        db().commit()
    for path in ["/admin/drinks", "/admin/coffee"]:
        assert client.get(path).status_code == 403
    assert (
        post(
            client, "/admin/products/bulk", dict(ids=["1"], action="draft")
        ).status_code
        == 403
    )
    assert post(client, "/admin/products/1/quick", dict(active="1")).status_code == 403


def test_v20_migration_backup_and_restart_preserves_every_record(tmp_path):
    data = tmp_path / "v20-data"
    data.mkdir()
    with sqlite3.connect(data / "cafe.sqlite3") as conn:
        conn.executescript(Path("tests/fixtures/schema_v3.sql").read_text())
        conn.execute(
            "INSERT INTO users(username,password) VALUES ('owner','synthetic-hash')"
        )
        conn.execute(
            "INSERT INTO products(name,kind,description) VALUES ('Owner coffee','ground','Owner description')"
        )
        before = {
            table: conn.execute("SELECT * FROM " + table).fetchall()
            for table in ["users", "products"]
        }
    for _ in range(2):
        app = create_app({"DATA_DIR": str(data), "TESTING": True})
        with app.app_context():
            assert (
                db().execute("SELECT max(version) FROM schema_version").fetchone()[0]
                == 5
            )
            for table, rows in before.items():
                after = [
                    tuple(r)[: len(rows[0])]
                    for r in db().execute("SELECT * FROM " + table)
                ]
                assert after == rows
    backups = list((data / "backups").glob("pre-migration-v3-*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as saved:
        assert (
            saved.execute("SELECT max(version) FROM schema_version").fetchone()[0] == 3
        )
        assert saved.execute("SELECT * FROM users").fetchall() == before["users"]


def test_seed_cli_explicit_directory_and_status_is_read_only(empty_app):
    runner = empty_app.test_cli_runner()
    result = runner.invoke(args=["seed-starter-catalog"])
    assert result.exit_code != 0 and "--confirm-data-dir" in result.output
    result = runner.invoke(args=["seed-starter-catalog", "--dry-run"])
    assert result.exit_code == 0 and "18 drink" in result.output
    result = runner.invoke(
        args=[
            "seed-starter-catalog",
            "--confirm-data-dir",
            empty_app.config["DATA_DIR"],
        ]
    )
    assert result.exit_code == 0 and "Verified, restorable" in result.output
    result = runner.invoke(
        args=[
            "seed-starter-catalog",
            "--confirm-data-dir",
            empty_app.config["DATA_DIR"],
        ]
    )
    assert result.exit_code == 0 and "0 drink" in result.output


def test_wsgi_https_host_allowlist_and_no_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CAFE_LUX_DATA_DIR", str(tmp_path / "linux-data"))
    monkeypatch.setenv("CAFE_LUX_ALLOWED_HOSTS", "synthetic-lux.pythonanywhere.com")
    monkeypatch.setenv("CAFE_LUX_INSECURE_LOCAL", "0")
    monkeypatch.setenv("CAFE_LUX_TRUST_PROXY", "1")
    module = runpy.run_path("wsgi.py")
    application = module["application"]
    assert not application.debug and application.config["SESSION_COOKIE_SECURE"]
    client = application.test_client()
    response = client.get(
        "/",
        base_url="https://synthetic-lux.pythonanywhere.com",
        headers={"X-Forwarded-Proto": "https"},
    )
    assert response.status_code == 200 and "Secure" in response.headers["Set-Cookie"]
    assert client.get("/", headers={"Host": "attacker.invalid"}).status_code == 400
    assert callable(application.wsgi_app)
    assert "waitress" not in Path("wsgi.py").read_text().lower().split("from cafe")[1]


def test_windows_contract_and_status_before_migration(tmp_path):
    assert (
        "127.0.0.1" in Path("run.py").read_text()
        and "port=8000" in Path("run.py").read_text()
    )
    for script in ["setup.bat", "start.bat", "stop.bat", "check-install.bat"]:
        assert "%~dp0" in Path(script).read_text()
    data = tmp_path / "old"
    data.mkdir()
    with sqlite3.connect(data / "cafe.sqlite3") as conn:
        conn.executescript(Path("tests/fixtures/schema_v3.sql").read_text())
    environment = {**os.environ, "CAFE_LUX_DATA_DIR": str(data)}
    result = subprocess.run(
        [sys.executable, "manage.py", "migration-status"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
        and "Current schema: 3" in result.stdout
        and "target: 5" in result.stdout
    )
    with sqlite3.connect(data / "cafe.sqlite3") as conn:
        assert (
            conn.execute("SELECT max(version) FROM schema_version").fetchone()[0] == 3
        )
    result = subprocess.run(
        [sys.executable, "manage.py", "prepare-update"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0 and "Verified database + media backup:" in result.stdout
    )
    with sqlite3.connect(data / "cafe.sqlite3") as conn:
        assert (
            conn.execute("SELECT max(version) FROM schema_version").fetchone()[0] == 3
        )


def test_approved_customizations_and_coffee_combination_survive_whatsapp(app, client):
    from cafe.public import whatsapp_message

    seed(app)
    login(client)
    with app.app_context():
        conn = db()
        latte = dict(
            conn.execute("SELECT * FROM products WHERE name='Caffè Latte'").fetchone()
        )
        coffee = dict(
            conn.execute(
                "SELECT * FROM products WHERE name='LUX Signature Blend'"
            ).fetchone()
        )
        drink_variant = dict(
            conn.execute(
                "SELECT * FROM variants WHERE product_id=? ORDER BY position LIMIT 1",
                (latte["id"],),
            ).fetchone()
        )
        bean_variant = dict(
            conn.execute(
                "SELECT * FROM variants WHERE product_id=? AND grams=500 AND allowed_grinds='Ground coffee'",
                (coffee["id"],),
            ).fetchone()
        )
        extras = [
            dict(
                conn.execute(
                    "SELECT * FROM addons WHERE product_id=? AND name=?",
                    (latte["id"], name),
                ).fetchone()
            )
            for name in ["Oat milk", "Extra shot", "Vanilla", "Less sugar"]
        ]
    for product in [latte, coffee]:
        upload(client, product["id"])
    for v, price in [(drink_variant, "3.85"), (bean_variant, "8.99")]:
        post(
            client,
            f"/admin/products/{v['product_id']}/option",
            dict(
                kind="variant",
                id=v["id"],
                label=v["label"],
                grams=v["grams"] or "",
                allowed_grinds=v["allowed_grinds"],
                allowed_temperatures=v["allowed_temperatures"],
                price=price,
                active=1,
            ),
        )
    for extra, price in zip(extras, ["1.00", "1.25", "0.50", "0"]):
        post(
            client,
            f"/admin/products/{latte['id']}/option",
            dict(
                kind="addon",
                id=extra["id"],
                name=extra["name"],
                option_group=extra["option_group"],
                price=price,
                active=1,
            ),
        )
    for product in [latte, coffee]:
        with app.app_context():
            current = dict(
                db()
                .execute("SELECT * FROM products WHERE id=?", (product["id"],))
                .fetchone()
            )
        post(
            client,
            f"/admin/products/{product['id']}",
            product_data(current, intent="publish"),
        )
        assert client.get(f"/product/{product['id']}").status_code == 200
    add(
        client, variant=drink_variant["id"], qty=2, addon=[str(a["id"]) for a in extras]
    )
    add(client, variant=bean_variant["id"], grind="Ground coffee")
    response = checkout(client)
    assert "/order/LUX-" in response.location
    with app.app_context():
        order = dict(db().execute("SELECT * FROM orders").fetchone())
        assert order["subtotal"] == 2219 and order["total"] == 2469
        message = whatsapp_message(order)
        for text in [
            "Oat milk",
            "Extra shot",
            "Vanilla",
            "Less sugar",
            "Ground coffee",
            "500 g",
        ]:
            assert text in message
        frozen = order["items"]
        db().execute(
            "UPDATE products SET name=? WHERE id=?", ("Owner new name", latte["id"])
        )
        db().execute(
            "UPDATE variants SET price=9999 WHERE id=?", (drink_variant["id"],)
        )
        db().commit()
        assert db().execute("SELECT items FROM orders").fetchone()[0] == frozen


def test_order_operator_can_inspect_details_but_cannot_edit_catalog(app, client):
    add(client)
    checkout(client)
    login(client)
    with app.app_context():
        db().execute("UPDATE users SET role='operator'")
        db().commit()
    assert client.get("/admin/orders/1").status_code == 200
    assert client.get("/admin/products/1").status_code == 403


def test_foreign_or_newer_database_is_not_silently_initialized(tmp_path):
    data = tmp_path / "newer"
    data.mkdir()
    with sqlite3.connect(data / "cafe.sqlite3") as c:
        c.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY)")
        c.execute("INSERT INTO schema_version VALUES (999)")
    with pytest.raises(RuntimeError, match="newer"):
        create_app({"DATA_DIR": str(data)})

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    with sqlite3.connect(foreign / "cafe.sqlite3") as c:
        c.execute("CREATE TABLE unrelated_business(private_value TEXT)")
    with pytest.raises(RuntimeError, match="Unrecognized database"):
        create_app({"DATA_DIR": str(foreign)})
    with sqlite3.connect(foreign / "cafe.sqlite3") as c:
        assert c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == [("unrelated_business",)]
