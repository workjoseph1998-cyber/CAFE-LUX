from contextlib import closing
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import click
from flask import current_app
from werkzeug.security import generate_password_hash
from .db import db, audit, LATEST_SCHEMA


def make_backup():
    data = Path(current_app.config["DATA_DIR"])
    source = data / "cafe.sqlite3"
    if not source.is_file() or source.stat().st_size == 0:
        raise RuntimeError(
            "No existing Café LUX database to back up. Check the intended data directory."
        )
    if (
        not db().execute("SELECT 1 FROM sqlite_master WHERE name='products'").fetchone()
        or db().execute("PRAGMA integrity_check").fetchone()[0] != "ok"
    ):
        raise RuntimeError("Database validation failed; no backup created.")
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
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("Backup archive verification failed.")
            restored = Path(temp) / "verify.sqlite3"
            restored.write_bytes(archive.read("cafe.sqlite3"))
            with closing(sqlite3.connect(restored)) as verify:
                if verify.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Restored snapshot integrity check failed.")
    target.chmod(0o600)
    return target


def register(app):
    app.config["DUMMY_HASH"] = generate_password_hash(
        "unusable-" + __import__("secrets").token_hex(16)
    )

    @app.cli.command("init-db")
    def init():
        click.echo("Database schema v4 initialized; existing data retained.")

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
            if conn.execute("PRAGMA integrity_check").fetchone()[
                0
            ] != "ok" or conn.execute(
                "SELECT max(version) FROM schema_version"
            ).fetchone()[
                0
            ] not in (
                2,
                3,
                4,
            ):
                raise click.ClickException("Backup integrity/version failed.")
            conn.close()
            safety = make_backup()
            db().close()
            shutil.copy2(root / "cafe.sqlite3", data / "cafe.sqlite3")
            if (root / "uploads").exists():
                shutil.copytree(root / "uploads", data / "uploads", dirs_exist_ok=True)
            click.echo("Restored. Safety backup: " + str(safety))

    @app.cli.command("migrate")
    def migrate():
        click.echo(f"Data directory: {app.config['DATA_DIR']}")
        click.echo(
            f"Schema v{LATEST_SCHEMA} ready. Prior versions were backed up before migration. Catalog seeding is separate."
        )

    @app.cli.command("prepare-update")
    def prepare_update():
        click.echo(f"Data directory: {app.config['DATA_DIR']}")
        click.echo(f"Verified database + media backup: {make_backup()}")
        click.echo(
            "No code updated or hosting reloaded. Stop/drain requests, update approved code and dependencies, run migrate, then reload manually."
        )

    @app.cli.command("migration-status")
    def migration_status():
        path = Path(app.config["DATABASE"])
        click.echo(f"Data directory: {app.config['DATA_DIR']}")
        if not path.exists():
            click.echo(
                f"No database. Target schema: {LATEST_SCHEMA}. Run migrate to initialize."
            )
            return
        with closing(
            sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        ) as conn:
            found = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name='schema_version'"
            ).fetchone()
            version = (
                conn.execute(
                    "SELECT coalesce(max(version),0) FROM schema_version"
                ).fetchone()[0]
                if found
                else 0
            )
        click.echo(
            f"Current schema: {version}; target: {LATEST_SCHEMA}; "
            + ("up to date" if version == LATEST_SCHEMA else "migration required")
        )

    @app.cli.command("seed-starter-catalog")
    @click.option(
        "--confirm-data-dir",
        type=click.Path(path_type=Path),
        help="Must match the intended persistent data directory.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Report planned catalog additions and conflicts without catalog writes.",
    )
    def seed(confirm_data_dir, dry_run):
        from .starter_catalog import seed_catalog

        data = Path(app.config["DATA_DIR"])
        click.echo(f"Data directory: {data}")
        if not dry_run and (
            confirm_data_dir is None or confirm_data_dir.resolve() != data
        ):
            raise click.ClickException(
                "Pass --confirm-data-dir with this exact directory. No catalog changes applied."
            )
        result = seed_catalog(dry_run=dry_run)
        for line in result:
            click.echo(line)

    @app.cli.command("prepare-catalog-preview")
    @click.option("--confirm-data-dir", required=True, type=click.Path(path_type=Path))
    def prepare_preview(confirm_data_dir):
        from .catalog_preview import prepare_catalog_preview

        data = Path(app.config["DATA_DIR"])
        click.echo(f"Data directory: {data}")
        if confirm_data_dir.resolve() != data:
            raise click.ClickException(
                "Directory mismatch. No catalog content changed."
            )
        try:
            result = prepare_catalog_preview()
        except (ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(
            f"Added {result['images']} small sample images; filled {result['descriptions']} missing descriptions."
        )
        if result["backup"]:
            click.echo("Verified database + existing media backup: " + result["backup"])
        click.echo(
            "Existing edits, prices, stock and publication state preserved. Open Admin → Catalog preview."
        )

    @app.cli.command("publish-starter-samples")
    @click.option("--confirm-data-dir", required=True, type=click.Path(path_type=Path))
    def publish_starter_samples(confirm_data_dir):
        from .catalog_test_data import prepare_and_publish_starters

        data = Path(app.config["DATA_DIR"])
        if confirm_data_dir.resolve() != data:
            raise click.ClickException("Directory mismatch. No changes applied.")
        result = prepare_and_publish_starters()
        click.echo(
            f"Published {result['published']} products; filled {result['prices']} sample variant prices and {result['images']} missing images. Backup: {result['backup']}"
        )
        for issue in result["skipped"]:
            click.echo(issue)
