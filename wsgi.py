"""WSGI entry point for managed hosting. Never starts Waitress or a listener."""

from cafe import create_app

application = create_app()
