"""Local management commands; never starts a public listener."""

import sys
from cafe import create_app

if __name__ == "__main__":
    args = sys.argv[1:]
    app = create_app(
        {
            "INIT_DB": not (
                args
                and args[0]
                in ("migration-status", "backup", "prepare-update", "restore")
            )
        }
    )
    if args and args[0] == "init-admin":
        args[0] = "create-admin"
    with app.app_context():
        app.cli.main(args=args, prog_name="manage.py")
