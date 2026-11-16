"""Operator entry point. Resolves installation config independently of working directory."""

import argparse
import sys
from deployment import (
    check_python,
    initialize_config,
    load_environment,
    read_config,
    save_config,
    validate_data_path,
    validate_hosts,
)


def main():
    parser = argparse.ArgumentParser(
        description="Cafe LUX installation and administration"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init-config", "init-db", "init-admin", "check", "backup"):
        sub.add_parser(name)
    config = sub.add_parser("configure")
    config.add_argument(
        "--host",
        action="append",
        help="Public IIS hostname (repeatable); loopback hosts remain allowed",
    )
    config.add_argument(
        "--data-dir",
        help="Select storage explicitly; does not move or overwrite existing data",
    )
    config.add_argument(
        "--local-http",
        action="store_true",
        help="Development only: disable Secure cookie flag",
    )
    config.add_argument(
        "--secure-cookies", action="store_true", help="Restore default Secure cookies"
    )
    args = parser.parse_args()
    try:
        check_python()
        if args.command == "init-config":
            initialize_config()
            print("Installation configuration saved. Existing data retained.")
            return 0
        if args.command == "configure":
            settings = read_config()
            if not settings:
                raise RuntimeError("Run setup.bat first.")
            if args.host:
                settings["allowed_hosts"] = validate_hosts(
                    ["localhost", "127.0.0.1", *args.host]
                )
            if args.data_dir:
                protected = settings.get("protected_dirs", [])
                settings["data_dir"] = str(
                    validate_data_path(args.data_dir, protected=protected)
                )
            if args.local_http and args.secure_cookies:
                raise RuntimeError("Choose local HTTP or Secure cookies, not both.")
            if args.local_http:
                settings["insecure_local"] = True
            if args.secure_cookies:
                settings["insecure_local"] = False
            save_config(settings)
            print(
                "Configuration saved. Restart Cafe LUX to apply. Data was not moved or overwritten."
            )
            return 0
        load_environment()
        if args.command == "check":
            from cafe import create_app

            app = create_app()
            from cafe.db import db

            with app.app_context():
                if db().execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("Database integrity check failed.")
            print("Configuration, imports and database verified.")
            return 0
        if args.command in ("init-db", "init-admin", "backup"):
            from cafe import create_app
            from flask.cli import FlaskGroup

            cli = FlaskGroup(create_app=create_app)
            cli.main(
                args=[{"init-admin": "create-admin"}.get(args.command, args.command)],
                standalone_mode=False,
            )
        return 0
    except (RuntimeError, OSError, ImportError) as exc:
        print("Cafe LUX: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
