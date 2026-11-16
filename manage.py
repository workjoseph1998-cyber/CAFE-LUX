"""Operator entry point. Resolves installation config independently of working directory."""

import argparse
import sys
import os
from pathlib import Path
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
        command_parser = sub.add_parser(name)
        if name == "init-admin":
            command_parser.add_argument("--username")
            command_parser.add_argument(
                "--password-stdin",
                action="store_true",
                help="For automation only: read one password line from standard input, never a command-line password",
            )
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
                if (Path(settings["data_dir"]) / "server-process.json").exists():
                    raise RuntimeError(
                        "Stop Cafe LUX before changing its data directory. Resolve any stale process record first."
                    )
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
            data_value = os.environ.get("CAFE_LUX_DATA_DIR")
            if not data_value:
                raise RuntimeError("Missing storage configuration. Run setup.bat.")
            data = validate_data_path(
                data_value,
                protected=[
                    p
                    for p in os.environ.get("CAFE_LUX_PROTECTED_DIRS", "").split(
                        os.pathsep
                    )
                    if p
                ],
            )
            if not all(
                (data / name).is_file() for name in ("cafe.sqlite3", "session.key")
            ):
                raise RuntimeError(
                    "Missing initialized database or session key. Run setup.bat with the correct data directory."
                )
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

            if args.command == "init-admin" and (args.password_stdin or args.username):
                if not args.password_stdin or not args.username:
                    raise RuntimeError(
                        "Use both --username and --password-stdin for automation, or neither for interactive setup."
                    )
                if sys.stdin.isatty():
                    raise RuntimeError(
                        "--password-stdin requires redirected input; use normal interactive init-admin in a terminal."
                    )
                password = sys.stdin.readline(1026).rstrip("\r\n")
                if len(password) > 1024:
                    raise RuntimeError("Password exceeds 1024 characters.")
                from cafe.commands import create_administrator
                from click import ClickException

                try:
                    with create_app().app_context():
                        create_administrator(args.username, password)
                except ClickException as exc:
                    exc.show()
                    return exc.exit_code
                print("Administrator created.")
                return 0
            cli = FlaskGroup(create_app=create_app)
            from click import ClickException, Abort

            try:
                cli.main(
                    args=[
                        {"init-admin": "create-admin"}.get(args.command, args.command)
                    ],
                    standalone_mode=False,
                )
            except ClickException as exc:
                exc.show()
                return exc.exit_code
            except Abort:
                print("Administrator initialization cancelled.", file=sys.stderr)
                return 1
        return 0
    except (RuntimeError, OSError, ImportError) as exc:
        print("Cafe LUX: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
