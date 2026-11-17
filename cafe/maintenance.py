"""Verified local snapshots, usable before schema migrations and catalog writes."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from flask import current_app


def database_snapshot(connection, reason):
    data = Path(current_app.config["DATA_DIR"])
    target = (
        data
        / "backups"
        / (
            f"{reason}-"
            + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            + ".sqlite3"
        )
    )
    if connection.in_transaction:
        raise RuntimeError(
            "Finish database transactions before taking a safety snapshot."
        )
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise RuntimeError("Database integrity check failed. No changes applied.")
    try:
        with closing(sqlite3.connect(target)) as destination:
            connection.backup(destination)
        with closing(sqlite3.connect(target)) as restored, closing(
            sqlite3.connect(":memory:")
        ) as verification:
            restored.backup(verification)
            if verification.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Safety snapshot verification failed.")
            source_count = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            copy_count = verification.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            if source_count != copy_count:
                raise RuntimeError("Safety snapshot schema verification failed.")
        target.chmod(0o600)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target
