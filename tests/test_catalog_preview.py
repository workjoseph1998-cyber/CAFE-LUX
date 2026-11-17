import io
import zipfile
from pathlib import Path
from PIL import Image
from cafe.db import db
from cafe.catalog_preview import prepare_catalog_preview
from cafe.starter_catalog import seed_catalog
from conftest import post, login


def test_sample_sizes_and_original_assets(app):
    with app.app_context():
        root = Path(app.static_folder) / "images" / "starter-samples"
        samples = list(root.glob("*.jpg"))
        assert len(samples) == 22
        assert sum(p.stat().st_size for p in samples) < 300_000
        for file in samples:
            assert file.stat().st_size < 16_000
            with Image.open(file) as image:
                assert image.size == (480, 400) and image.format == "JPEG"


def test_prepare_missing_content_backup_and_idempotence(app, client):
    with app.app_context():
        seed_catalog()
        c = db()
        c.execute("UPDATE products SET description='' WHERE name='Espresso'")
        c.execute(
            "UPDATE products SET description='Owner description' WHERE name='Caffè Latte'"
        )
        c.execute(
            "INSERT INTO media(filename,title) VALUES ('owner.jpg','Owner photo')"
        )
        owner = Path(app.config["DATA_DIR"]) / "uploads" / "owner.jpg"
        owner.write_bytes(b"owner-photo-unchanged")
        c.execute(
            "UPDATE products SET image='owner.jpg' WHERE name='LUX Signature Blend'"
        )
        c.commit()
        before = {
            t: [tuple(r) for r in c.execute("SELECT * FROM " + t)]
            for t in ["users", "orders", "settings", "variants", "addons"]
        }
        result = prepare_catalog_preview()
        assert result["images"] == 21 and result["descriptions"] == 1
        with zipfile.ZipFile(result["backup"]) as backup:
            assert backup.read("uploads/owner.jpg") == b"owner-photo-unchanged"
        assert (
            c.execute(
                "SELECT description FROM products WHERE name='Espresso'"
            ).fetchone()[0]
            == "Short, concentrated coffee."
        )
        assert (
            c.execute(
                "SELECT description FROM products WHERE name='Caffè Latte'"
            ).fetchone()[0]
            == "Owner description"
        )
        assert (
            c.execute(
                "SELECT image FROM products WHERE name='LUX Signature Blend'"
            ).fetchone()[0]
            == "owner.jpg"
        )
        assert owner.read_bytes() == b"owner-photo-unchanged"
        for t, rows in before.items():
            assert [tuple(r) for r in c.execute("SELECT * FROM " + t)] == rows
        images = [tuple(r) for r in c.execute("SELECT id,image FROM products")]
        media = [tuple(r) for r in c.execute("SELECT * FROM media")]
        again = prepare_catalog_preview()
        assert again == dict(images=0, descriptions=0, backup=None)
        assert images == [tuple(r) for r in c.execute("SELECT id,image FROM products")]
        assert media == [tuple(r) for r in c.execute("SELECT * FROM media")]


def test_admin_button_and_private_preview_without_prices(app, client):
    with app.app_context():
        seed_catalog()
    assert client.get("/admin/catalog-preview").status_code == 302
    assert client.post("/admin/catalog-preview/prepare").status_code == 400
    login(client)
    response = post(client, "/admin/catalog-preview/prepare")
    assert response.location.endswith("/admin/catalog-preview")
    drinks = client.get("/admin/catalog-preview").text
    coffee = client.get("/admin/catalog-preview?kind=ground").text
    assert "Short, concentrated coffee." in drinks and "Iced Mocha" in drinks
    assert "LUX Golden Roast" in coffee and "Price pending" in coffee
    assert "Sample illustration" in drinks and "Draft" in drinks
    assert "Double Espresso" not in client.get("/drinks").text
    with app.app_context():
        c = db()
        file = c.execute("SELECT image FROM products WHERE name='Espresso'").fetchone()[
            0
        ]
        assert file.startswith("starter-sample-")
        assert not c.execute(
            "SELECT 1 FROM variants WHERE starter_key IS NOT NULL AND (price IS NOT NULL OR stock IS NOT NULL)"
        ).fetchone()
        assert not c.execute(
            "SELECT 1 FROM products WHERE starter_key IS NOT NULL AND active=1"
        ).fetchone()
    assert client.get("/media/" + file).status_code == 200
    with app.app_context():
        db().execute("UPDATE users SET role='operator'")
        db().commit()
    assert client.get("/admin/catalog-preview").status_code == 403
    assert post(client, "/admin/catalog-preview/prepare").status_code == 403


def test_preview_cli_directory_confirmation(app):
    with app.app_context():
        seed_catalog()
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "prepare-catalog-preview",
            "--confirm-data-dir",
            "/tmp/wrong-lux-directory",
        ]
    )
    assert result.exit_code != 0
    result = runner.invoke(
        args=["prepare-catalog-preview", "--confirm-data-dir", app.config["DATA_DIR"]]
    )
    assert result.exit_code == 0 and "22 small sample images" in result.output
