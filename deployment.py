"""Shared, standard-library-only deployment configuration; safe before pip install."""

import json
import os
import re
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
CONFIG_NAME = "cafe-lux.local.json"
SUPPORTED_MIN = (3, 11)
SUPPORTED_MAX = (3, 14)  # Exclusive; dependencies validated for CPython 3.11-3.13.


def check_python(version=None):
    version = version or sys.version_info
    if not SUPPORTED_MIN <= tuple(version[:2]) < SUPPORTED_MAX:
        raise RuntimeError("Python 3.11, 3.12 or 3.13 is required (3.12 recommended).")


def config_path(root=None):
    return Path(root or APP_ROOT) / CONFIG_NAME


def read_config(root=None):
    path = config_path(root)
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(config, dict):
            raise ValueError("expected a JSON object")
        return config
    except (ValueError, OSError) as exc:
        raise RuntimeError(
            f"Cannot read {path}: {exc}. Restore or correct this local configuration; do not delete your data."
        ) from exc


def validate_hosts(value):
    hosts = value.split(",") if isinstance(value, str) else value
    if not isinstance(hosts, list) or not hosts:
        raise RuntimeError("Allowed hosts must contain at least one hostname.")
    result = []
    for host in hosts:
        if not isinstance(host, str):
            raise RuntimeError("Allowed hosts must be names, not URLs.")
        host = host.strip().lower()
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", host):
            raise RuntimeError(
                "Use hostnames only, comma separated, without scheme, port or path."
            )
        if host not in result:
            result.append(host)
    return result


def validate_data_path(value, root=None, protected=()):
    path = Path(value)
    if not path.is_absolute():
        raise RuntimeError("CAFE_LUX_DATA_DIR must be an absolute path.")
    path = path.resolve()
    root = Path(root or APP_ROOT).resolve()
    for other in [root, *(Path(p).resolve() for p in protected)]:
        if path == other or other in path.parents or path in other.parents:
            raise RuntimeError(
                "Use separate Cafe LUX storage outside source and protected application directories."
            )
    if any("cirrus" in part.lower() for part in path.parts):
        raise RuntimeError("Cafe LUX storage must not overlap Cirrus directories.")
    return path


def load_environment(root=None):
    """Explicit process variables override persisted non-secret installation settings."""
    config = read_config(root)
    mapping = {
        "data_dir": "CAFE_LUX_DATA_DIR",
        "allowed_hosts": "CAFE_LUX_ALLOWED_HOSTS",
        "trust_proxy": "CAFE_LUX_TRUST_PROXY",
        "insecure_local": "CAFE_LUX_INSECURE_LOCAL",
        "protected_dirs": "CAFE_LUX_PROTECTED_DIRS",
    }
    for key, env_name in mapping.items():
        if env_name in os.environ or key not in config:
            continue
        value = config[key]
        if key == "allowed_hosts":
            value = ",".join(validate_hosts(value))
        elif key == "protected_dirs":
            if not isinstance(value, list) or not all(
                isinstance(p, str) for p in value
            ):
                raise RuntimeError("protected_dirs must be a list of absolute paths.")
            value = os.pathsep.join(value)
        elif key in ("trust_proxy", "insecure_local"):
            if not isinstance(value, bool):
                raise RuntimeError(key + " must be true or false.")
            value = "1" if value else "0"
        elif not isinstance(value, str):
            raise RuntimeError(key + " must be a string.")
        os.environ[env_name] = value
    if "CAFE_LUX_ALLOWED_HOSTS" in os.environ:
        validate_hosts(os.environ["CAFE_LUX_ALLOWED_HOSTS"])
    return config


def save_config(config, root=None):
    path = config_path(root)
    temporary = path.with_suffix(".json.tmp")
    # Single operator install/update. No credentials are stored in this file.
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=True, indent=2)
        file.write("\n")
    os.replace(temporary, path)


def initialize_config(root=None):
    root = Path(root or APP_ROOT).resolve()
    config = read_config(root)
    load_environment(root)
    data = os.environ.get("CAFE_LUX_DATA_DIR") or config.get("data_dir")
    if not data:
        if os.name != "nt":
            raise RuntimeError(
                "Set CAFE_LUX_DATA_DIR to an absolute dedicated data directory."
            )
        data = r"C:\CafeLuxData"
    protected = [
        p for p in os.environ.get("CAFE_LUX_PROTECTED_DIRS", "").split(os.pathsep) if p
    ]
    data = validate_data_path(data, root, protected)
    # Prevent a rerun with a stale shell variable silently selecting another database.
    previous = config.get("data_dir")
    if previous and Path(previous).resolve() != data:
        raise RuntimeError(
            "Data directory differs from saved configuration. Use manage.py configure --data-dir after stopping the server; setup will not silently switch databases."
        )
    config.update(
        data_dir=str(data),
        allowed_hosts=validate_hosts(
            os.environ.get(
                "CAFE_LUX_ALLOWED_HOSTS",
                config.get("allowed_hosts", ["localhost", "127.0.0.1"]),
            )
        ),
        trust_proxy=os.environ.get("CAFE_LUX_TRUST_PROXY", "1") == "1",
        insecure_local=os.environ.get("CAFE_LUX_INSECURE_LOCAL", "0") == "1",
        protected_dirs=protected,
    )
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ("uploads", "logs", "backups"):
        (data / name).mkdir(exist_ok=True)
    save_config(config, root)
    return config
