"""Configuration and operator CLI regression tests, isolated from real installation data."""

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from deployment import (
    check_python,
    initialize_config,
    load_environment,
    read_config,
    validate_data_path,
    validate_hosts,
    save_config,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def clean_environment(monkeypatch):
    for name in [
        "CAFE_LUX_DATA_DIR",
        "CAFE_LUX_ALLOWED_HOSTS",
        "CAFE_LUX_TRUST_PROXY",
        "CAFE_LUX_INSECURE_LOCAL",
        "CAFE_LUX_PROTECTED_DIRS",
    ]:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.mark.parametrize("version", [(3, 11), (3, 12), (3, 13)])
def test_supported_python(version):
    check_python(version)


@pytest.mark.parametrize("version", [(3, 10), (3, 9), (3, 14), (2, 7)])
def test_unsupported_python(version):
    with pytest.raises(RuntimeError, match="Python 3.11"):
        check_python(version)


@pytest.mark.parametrize(
    "name",
    [
        "https://example.com",
        "example.com:8000",
        "example.com/path",
        "evil@host",
        "",
        None,
    ],
)
def test_invalid_hosts(name):
    with pytest.raises(RuntimeError):
        validate_hosts(name)


def test_bom_and_unicode_config(tmp_path, clean_environment):
    root = tmp_path / "nested folder" / "Café LUX"
    root.mkdir(parents=True)
    data = tmp_path / "Données Café"
    clean_environment.setenv("CAFE_LUX_DATA_DIR", str(data))
    config = initialize_config(root)
    assert Path(config["data_dir"]) == data
    sentinel = data / "uploads" / "keep.jpg"
    sentinel.write_bytes(b"preserve")
    initialize_config(root)
    assert sentinel.read_bytes() == b"preserve"
    p = root / "cafe-lux.local.json"
    p.write_text(json.dumps(config), encoding="utf-8-sig")
    assert read_config(root) == config
    clean_environment.delenv("CAFE_LUX_DATA_DIR")
    load_environment(root)
    assert os.environ["CAFE_LUX_DATA_DIR"] == str(data)


def test_rerun_refuses_silent_data_switch(tmp_path, clean_environment):
    root = tmp_path / "app"
    root.mkdir()
    clean_environment.setenv("CAFE_LUX_DATA_DIR", str(tmp_path / "data-one"))
    initialize_config(root)
    clean_environment.setenv("CAFE_LUX_DATA_DIR", str(tmp_path / "data-two"))
    with pytest.raises(RuntimeError, match="differs from saved"):
        initialize_config(root)
    assert not (tmp_path / "data-two").exists()


def test_corrupt_config_preserved(tmp_path):
    file = tmp_path / "cafe-lux.local.json"
    file.write_text("{broken")
    with pytest.raises(RuntimeError, match="Cannot read"):
        read_config(tmp_path)
    assert file.read_text() == "{broken"


def test_absolute_data_and_protected_paths(tmp_path):
    with pytest.raises(RuntimeError):
        validate_data_path("relative")
    with pytest.raises(RuntimeError):
        validate_data_path(tmp_path, root=tmp_path / "app")
    with pytest.raises(RuntimeError):
        validate_data_path(
            tmp_path / "protected" / "data",
            root=tmp_path / "app",
            protected=[tmp_path / "protected"],
        )


def test_config_no_secrets_and_environment_override(tmp_path, clean_environment):
    config = {
        "data_dir": str(tmp_path / "saved-data"),
        "allowed_hosts": ["localhost", "shop.example"],
        "trust_proxy": True,
        "insecure_local": False,
    }
    save_config(config, tmp_path)
    clean_environment.setenv("CAFE_LUX_ALLOWED_HOSTS", "127.0.0.1")
    load_environment(tmp_path)
    assert os.environ["CAFE_LUX_ALLOWED_HOSTS"] == "127.0.0.1"
    assert os.environ["CAFE_LUX_TRUST_PROXY"] == "1"
    assert os.environ["CAFE_LUX_INSECURE_LOCAL"] == "0"
    assert set(read_config(tmp_path)) == set(config)


def test_manage_admin_and_repeated_database_init(tmp_path, app):
    env = os.environ.copy()
    env["CAFE_LUX_DATA_DIR"] = app.config["DATA_DIR"]
    env["PYTHONUTF8"] = "1"

    def run(args, **kw):
        return subprocess.run(
            [sys.executable, str(ROOT / "manage.py"), *args],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            **kw,
        )

    for _ in range(2):
        result = run(["init-db"])
        assert result.returncode == 0, result.stderr
    secret = "synthetic-only-admin-pass"
    result = run(
        ["init-admin", "--username", "newoperator", "--password-stdin"],
        input=secret + "\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert secret not in result.stdout
    from cafe.db import db
    from werkzeug.security import check_password_hash

    with app.app_context():
        users = db().execute("SELECT * FROM users").fetchall()
        assert len(users) == 2
        user = (
            db().execute("SELECT * FROM users WHERE username='newoperator'").fetchone()
        )
        assert check_password_hash(user["password"], secret)
        assert db().execute("SELECT count(*) FROM products").fetchone()[0] == 2
    result = run(["check"])
    assert result.returncode == 0, result.stderr


def test_interactive_admin_prompts_are_preserved(app):
    result = app.test_cli_runner().invoke(
        args=["create-admin"],
        input="prompt-test-admin\nsynthetic-prompt-password\nsynthetic-prompt-password\n",
    )
    assert result.exit_code == 0, result.output
    assert "Administrator created." in result.output
    assert "synthetic-prompt-password" not in result.output
