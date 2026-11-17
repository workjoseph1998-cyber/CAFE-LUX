import os
import secrets
from pathlib import Path
import json
from flask import (
    Flask,
    abort,
    request,
    session,
    render_template,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import SecurityError
from .db import init_db, close_db, settings


def create_app(test_config=None):
    app = Flask(__name__)
    configured_data = (test_config or {}).get("DATA_DIR") or os.environ.get(
        "CAFE_LUX_DATA_DIR"
    )
    if not configured_data and os.name == "nt":
        configured_data = r"C:\CafeLuxData"
    if not configured_data:
        raise RuntimeError(
            "Set CAFE_LUX_DATA_DIR to a dedicated directory outside the application before setup or startup."
        )
    data = Path(configured_data).resolve()
    # Never store runtime data inside source or an explicitly protected application.
    source = Path(__file__).resolve().parent.parent
    protected = [
        Path(p).resolve()
        for p in os.environ.get("CAFE_LUX_PROTECTED_DIRS", "").split(os.pathsep)
        if p
    ]
    if (
        data == source
        or source in data.parents
        or data in source.parents
        or any(data == p or p in data.parents or data in p.parents for p in protected)
        or any("cirrus" in p.lower() for p in data.parts)
    ):
        raise RuntimeError(
            "Use a separate Café LUX data directory outside source and protected applications."
        )
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ("uploads", "backups", "logs"):
        (data / name).mkdir(exist_ok=True)
    secret_path = data / "session.key"
    if not secret_path.exists():
        try:
            fd = os.open(secret_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    secret = secret_path.read_text().strip()
    if len(secret) < 64:
        raise RuntimeError(
            "Invalid session key. Restore a valid key or reinitialize it offline."
        )
    app.config.update(
        INIT_DB=True,
        SECRET_KEY=secret,
        DATA_DIR=str(data),
        DATABASE=str(data / "cafe.sqlite3"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        SESSION_COOKIE_NAME="cafe_lux_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("CAFE_LUX_INSECURE_LOCAL") != "1",
        PERMANENT_SESSION_LIFETIME=3600,
    )
    app.config["TRUSTED_HOSTS"] = [
        h.strip()
        for h in os.environ.get("CAFE_LUX_ALLOWED_HOSTS", "localhost,127.0.0.1").split(
            ","
        )
        if h.strip()
    ]
    if test_config:
        app.config.update(test_config)
    if os.environ.get("CAFE_LUX_TRUST_PROXY") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0)
    app.teardown_appcontext(close_db)
    if app.config["INIT_DB"]:
        with app.app_context():
            init_db()

    @app.before_request
    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        if request.method == "POST" and not secrets.compare_digest(
            str(session["csrf"]).encode(), request.form.get("csrf", "").encode()
        ):
            abort(400, "Invalid form token. Reload the page and try again.")

    @app.after_request
    def security(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; frame-src https://www.google.com; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        if request.path.startswith(("/admin", "/checkout", "/order", "/cart")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.context_processor
    def context():
        ar = session.get("lang") == "ar"
        from .i18n import WORDS
        from .db import db

        def media_alt(filename, fallback=""):
            row = (
                db()
                .execute("SELECT alt FROM media WHERE filename=?", (filename,))
                .fetchone()
            )
            return row["alt"] if row and row["alt"] else fallback

        site = settings()
        if not request.path.startswith("/admin"):
            for key in (
                "instagram",
                "facebook",
                "whatsapp",
                "email",
                "phone",
                "address",
                "maps",
                "hours",
                "map_embed",
            ):
                if site.get("visible_" + key) != "1":
                    site[key] = ""
        current_user = (
            db()
            .execute(
                "SELECT role FROM users WHERE id=? AND active=1",
                (session.get("user_id"),),
            )
            .fetchone()
            if request.path.startswith("/admin")
            else None
        )
        return dict(
            admin_role=current_user["role"] if current_user else None,
            media_alt=media_alt,
            site=site,
            ar=ar,
            tr=lambda s: WORDS.get(s, s) if ar else s,
            csrf_token=session.get("csrf", ""),
            cart_count=sum(x["qty"] for x in session.get("cart", [])),
        )

    app.jinja_env.filters["fromjson"] = json.loads

    @app.template_filter("money")
    def money(v):
        return f"{v / 100:,.2f}"

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error(e):
        if isinstance(e, SecurityError):
            return "Invalid host.", 400
        return render_template("error.html", error=e), e.code

    @app.errorhandler(500)
    def internal(e):
        return (
            render_template(
                "error.html", error="Something went wrong. Please try again."
            ),
            500,
        )

    from .public import bp
    from .admin import bp as admin

    app.register_blueprint(bp)
    app.register_blueprint(admin)
    from .commands import register

    register(app)
    return app
