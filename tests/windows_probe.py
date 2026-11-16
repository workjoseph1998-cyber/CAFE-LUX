"""Helpers used only by the Windows integration test in its disposable installation."""

import json
import secrets
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from deployment import load_environment

config = load_environment()
data = Path(config["data_dir"])
command = sys.argv[1]
if command == "seed":
    password = secrets.token_urlsafe(24)
    result = subprocess.run(
        [sys.executable, str(root / "manage.py"), "init-admin"],
        input="windows-test-admin\n" + password + "\n" + password + "\n",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert password not in result.stdout
    with sqlite3.connect(data / "cafe.sqlite3") as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM users WHERE username='windows-test-admin'"
            ).fetchone()[0]
            == 1
        )
        conn.execute(
            "UPDATE settings SET value='WINDOWS PRESERVATION SENTINEL' WHERE key='about'"
        )
    (data / "uploads" / "keep.jpg").write_bytes(b"test image preservation sentinel")
elif command == "verify":
    with sqlite3.connect(data / "cafe.sqlite3") as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM users WHERE username='windows-test-admin'"
            ).fetchone()[0]
            == 1
        )
        assert (
            conn.execute("SELECT value FROM settings WHERE key='about'").fetchone()[0]
            == "WINDOWS PRESERVATION SENTINEL"
        )
    assert (
        data / "uploads" / "keep.jpg"
    ).read_bytes() == b"test image preservation sentinel"
elif command == "health":
    with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=5) as response:
        assert json.load(response)["application"] == "cafe-lux"
    with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=5) as response:
        assert response.status == 200
elif command == "busy":
    import socket, time

    with socket.socket() as busy:
        busy.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        busy.bind(("127.0.0.1", 8000))
        busy.listen()
        (data / "busy-ready").write_text("ready")
        time.sleep(120)
print("PASS: Windows probe " + command)
