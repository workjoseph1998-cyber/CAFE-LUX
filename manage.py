"""Local management commands; never starts a public listener."""
import sys
from cafe import create_app
if __name__ == '__main__':
    app = create_app()
    args = sys.argv[1:]
    if args and args[0] == 'init-admin':
        args[0] = 'create-admin'
    with app.app_context():
        app.cli.main(args=args, prog_name='manage.py')
