"""Dedicated loopback listener. IIS must be configured separately."""

import os
import socket
from cafe import create_app
from deployment import load_environment, check_python


def port_available(port=8000):
    with socket.socket() as sock:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", port))


if __name__ == "__main__":
    check_python()
    load_environment()
    if not os.environ.get("CAFE_LUX_DATA_DIR"):
        raise SystemExit("CAFE_LUX_DATA_DIR is required. Run setup first.")
    try:
        port_available()
    except OSError:
        raise SystemExit(
            "Port 8000 is occupied. Stop the previous application yourself; nothing was terminated."
        )
    app = create_app()
    from waitress import serve
    from logging.handlers import RotatingFileHandler
    import logging

    handler = RotatingFileHandler(
        os.path.join(app.config["DATA_DIR"], "logs", "application.log"),
        maxBytes=2000000,
        backupCount=5,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.addHandler(handler)
    # Bind loopback only. ProxyFix trusts one HTTPS indication only when explicitly enabled.
    serve(
        app,
        host="127.0.0.1",
        port=8000,
        threads=4,
        max_request_body_size=8 * 1024 * 1024,
        clear_untrusted_proxy_headers=False,
    )
