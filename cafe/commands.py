import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import click
from flask import current_app
from werkzeug.security import generate_password_hash
from .db import db, audit


def make_backup():
    data = Path(current_app.config["DATA_DIR"])
    target = (
        data
        / "backups"
        / (
            "CafeLUX-"
            + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            + ".zip"
        )
    )
    with tempfile.TemporaryDirectory() as temp:
        database = Path(temp) / "cafe.sqlite3"
        dst = sqlite3.connect(database)
        db().backup(dst)
        dst.close()
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(database, "cafe.sqlite3")
            for file in (data / "uploads").glob("*.jpg"):
                z.write(file, "uploads/" + file.name)
    return target


def register(app):
    app.config["DUMMY_HASH"] = generate_password_hash(
        "unusable-" + __import__("secrets").token_hex(16)
    )

    @app.cli.command("init-db")
    def init():
        click.echo("Database schema v2 initialized; existing data retained.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def admin(username, password):
        import re

        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,100}", username) or len(password) < 12:
            raise click.ClickException(
                "Use a valid username and password of at least 12 characters."
            )
        if db().execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise click.ClickException(
                "User exists. Change passwords in Admin / Users."
            )
        db().execute(
            "INSERT INTO users(username,password) VALUES (?,?)",
            (username, generate_password_hash(password)),
        )
        audit("Created admin " + username)
        db().commit()
        click.echo("Administrator created.")

    @app.cli.command("backup")
    def backup():
        click.echo(str(make_backup()))

    @app.cli.command("restore")
    @click.argument("archive", type=click.Path(exists=True, path_type=Path))
    @click.option(
        "--confirm",
        is_flag=True,
        help="Confirm services are stopped and replacement is intended.",
    )
    def restore(archive, confirm):
        if not confirm:
            raise click.ClickException(
                "Stop the server, then use --confirm. Existing data will be backed up first."
            )
        data = Path(app.config["DATA_DIR"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with zipfile.ZipFile(archive) as z:
                if sum(i.file_size for i in z.infolist()) > 2 * 1024**3:
                    raise click.ClickException("Backup exceeds 2 GB.")
                for name in z.namelist():
                    p = Path(name)
                    if (
                        p.is_absolute()
                        or ".." in p.parts
                        or (
                            name != "cafe.sqlite3"
                            and not (
                                len(p.parts) == 2
                                and p.parts[0] == "uploads"
                                and p.suffix == ".jpg"
                            )
                        )
                    ):
                        raise click.ClickException("Invalid backup path.")
                z.extractall(root)
            if not (root / "cafe.sqlite3").exists():
                raise click.ClickException("Missing database.")
            conn = sqlite3.connect(root / "cafe.sqlite3")
            if (
                conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or conn.execute("SELECT max(version) FROM schema_version").fetchone()[0]
                != 2
            ):
                raise click.ClickException("Backup integrity/version failed.")
            conn.close()
            safety = make_backup()
            db().close()
            shutil.copy2(root / "cafe.sqlite3", data / "cafe.sqlite3")
            if (root / "uploads").exists():
                shutil.copytree(root / "uploads", data / "uploads", dirs_exist_ok=True)
            click.echo("Restored. Safety backup: " + str(safety))

    @app.cli.command("demo")
    def demo():
        # Draft examples have no prices; never publish sample offers automatically.
        if db().execute("SELECT 1 FROM products").fetchone():
            raise click.ClickException("Demo requires an empty catalog.")
        for kind, name, ar in [
            ("drink", "Signature Latte", "لاتيه لوكس"),
            ("drink", "Espresso", "إسبريسو"),
            ("drink", "Cold Brew", "كولد برو"),
            ("ground", "House Blend", "خلطة الدار"),
            ("ground", "Arabic Coffee", "قهوة عربية"),
        ]:
            cur = db().execute(
                "INSERT INTO products(name,name_ar,description,description_ar,kind,grinds,featured) VALUES (?,?,?,?,?,?,1)",
                (
                    name,
                    ar,
                    "Draft example — replace with your own description.",
                    "مثال تجريبي — أضف وصفك الخاص.",
                    kind,
                    "Whole beans,Fine,Medium" if kind == "ground" else "",
                ),
            )
            for label, grams in (
                [
                    ("100 g", 100),
                    ("200 g", 200),
                    ("250 g", 250),
                    ("500 g", 500),
                    ("1 kg", 1000),
                ]
                if kind == "ground"
                else [("Regular", None), ("Large", None)]
            ):
                db().execute(
                    "INSERT INTO variants(product_id,label,grams) VALUES (?,?,?)",
                    (cur.lastrowid, label, grams),
                )
        db().commit()
        click.echo("Draft examples created. All remain unpublished and unpriced.")
