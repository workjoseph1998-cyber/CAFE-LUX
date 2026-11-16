"""Real fresh-venv installation smoke test from nested/space/Unicode paths (Linux or Windows).
Uses downloaded/verified-by-pip distribution files if --wheelhouse is supplied.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="Cafe LUX install ") as tmp:
        base = Path(tmp)
        source = base / "nested folder" / "Café LUX" / "application"
        shutil.copytree(
            ROOT,
            source,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                "dist",
                "cafe-lux.local.json",
                "*.log",
            ),
        )
        data = base / "separate persistent data"
        env = os.environ.copy()
        for name in list(env):
            if name.startswith("CAFE_LUX_"):
                del env[name]
        env.update(
            CAFE_LUX_DATA_DIR=str(data), PYTHONUTF8="1", PYTHONIOENCODING="utf-8"
        )
        venv = source / ".venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        def run(*cmd):
            subprocess.run([str(python), *map(str, cmd)], cwd=base, env=env, check=True)

        pip = [
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            source / "requirements.txt",
        ]
        if args.wheelhouse:
            pip.extend(["--no-index", "--find-links", args.wheelhouse.resolve()])
        run(*pip)
        run(source / "manage.py", "init-config")
        # New shell: saved configuration must work with no application environment variables.
        del env["CAFE_LUX_DATA_DIR"]
        run(source / "manage.py", "init-db")
        run(source / "manage.py", "check")
        import sqlite3

        with sqlite3.connect(data / "cafe.sqlite3") as conn:
            conn.execute(
                "UPDATE settings SET value='PRESERVE THIS BUSINESS CONTENT' WHERE key='about'"
            )
        sentinel = data / "uploads" / "preserve.jpg"
        sentinel.write_bytes(b"test preservation sentinel")
        run(source / "manage.py", "init-config")
        run(source / "manage.py", "init-db")
        with sqlite3.connect(data / "cafe.sqlite3") as conn:
            assert (
                conn.execute("SELECT value FROM settings WHERE key='about'").fetchone()[
                    0
                ]
                == "PRESERVE THIS BUSINESS CONTENT"
            )
        assert sentinel.read_bytes() == b"test preservation sentinel"
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 8000))
            busy.listen()
            result = subprocess.run(
                [str(python), str(source / "run.py")],
                cwd=base,
                env=env,
                capture_output=True,
                text=True,
            )
            assert (
                result.returncode != 0 and "Port 8000 is occupied" in result.stderr
            ), result.stderr
        server = subprocess.Popen(
            [str(python), str(source / "run.py")],
            cwd=base,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise AssertionError(server.stderr.read().decode())
                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:8000/healthz", timeout=1
                    ) as response:
                        health = json.load(response)
                    if health["application"] == "cafe-lux":
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise AssertionError("Waitress did not become ready")
            with urllib.request.urlopen(
                "http://127.0.0.1:8000/", timeout=5
            ) as response:
                assert (
                    response.status == 200 and b"Luxury in Every Sip" in response.read()
                )
        finally:
            server.terminate()
            server.wait(timeout=15)
            server.stderr.close()
        print(
            "PASS: fresh venv, dependency install, imports, persistent config, nested/space/Unicode paths, rerun/data preservation, occupied port, Waitress HTTP readiness."
        )


if __name__ == "__main__":
    main()
