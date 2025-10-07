# app/__init__.py
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Расширения
from .extensions import db, migrate
try:
    from .extensions import login_manager, csrf  # type: ignore
except Exception:
    login_manager = None
    csrf = None


def _register_bp(app: Flask, import_path: str, url_prefix: str | None = None) -> None:
    """
    Осторожно импортирует и регистрирует блюпринт.
    Если что-то пошло не так — логируем стек и продолжаем.
    """
    try:
        mod_path, obj_name = import_path.rsplit(".", 1)
        mod = __import__(mod_path, fromlist=[obj_name])
        bp = getattr(mod, obj_name)
        app.register_blueprint(bp, url_prefix=url_prefix)
    except Exception as e:
        app.logger.exception("Blueprint %s not registered: %s", import_path, e)


def create_app() -> Flask:
    app = Flask(__name__)

    # ---------- Конфиг ----------
    try:
        from .config import Config
        app.config.from_object(Config)
    except Exception:
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "SQLALCHEMY_DATABASE_URI", "sqlite:///cashbox.db"
        )
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)

    # За обратным прокси (nginx/Traefik)
    if str(app.config.get("APP_BEHIND_PROXY", os.getenv("APP_BEHIND_PROXY", "0"))).lower() in {"1", "true", "yes"}:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)  # type: ignore

    # ---------- Расширения ----------
    db.init_app(app)
    migrate.init_app(app, db)

    if login_manager is not None:
        login_manager.init_app(app)
        login_manager.login_view = "auth.login"

        @login_manager.user_loader  # type: ignore
        def load_user(user_id: str):
            try:
                from .models.user import User
                return User.query.get(int(user_id))
            except Exception:
                return None

    if csrf is not None:
        # пример: ограничить жизнь токена — app.config["WTF_CSRF_TIME_LIMIT"] = 3600
        csrf.init_app(app)

    # ---------- Блюпринты ----------
    _register_bp(app, "app.blueprints.banks.bp", url_prefix="/banks")
    _register_bp(app, "app.blueprints.core.bp", url_prefix=None)
    _register_bp(app, "app.blueprints.auth.bp", url_prefix=None)  # /login
    _register_bp(app, "app.blueprints.internal.bp", url_prefix="/internal")
    _register_bp(app, "app.blueprints.refs.bp", url_prefix="/refs")

    # ---------- Импорт моделей (для Alembic/metadata) ----------
    try:
        from . import models  # noqa: F401
        from .models import finance, tourism, party, ref_codes, user  # noqa: F401
    except Exception as e:
        app.logger.warning("Models not fully imported: %s", e)

    # ---------- Jinja: фильтры и контекст ----------
    @app.template_filter("fmt2")
    def fmt2(value):
        """Форматирует число двумя знаками после точки."""
        if value is None or value == "":
            return "0.00"
        try:
            v = Decimal(str(value))
        except Exception:
            try:
                v = Decimal(value)
            except Exception:
                return str(value)
        return f"{v:.2f}"

    @app.context_processor
    def inject_globals():
        return {"current_year": datetime.utcnow().year}

    # ---------- Безопасность заголовков ----------
    @app.after_request
    def _security_headers(resp):
        allow_cdn = str(app.config.get("ALLOW_CDN", os.getenv("ALLOW_CDN", "0"))).lower() in {"1", "true", "yes"}

        csp_parts = [
            "default-src 'self'",
            "img-src 'self' data: https://cdn.jsdelivr.net",
            "font-src 'self' data: https://cdn.jsdelivr.net",
            "connect-src 'self' https://cdn.jsdelivr.net",
        ]

        style_src = ["'self'", "'unsafe-inline'"]
        script_src = ["'self'"]

        if allow_cdn:
            # Разрешаем загрузку Bootstrap и иконок с CDN
            style_src += [
                "https://cdn.jsdelivr.net",
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/",
                "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/",
            ]
            script_src += [
                "https://cdn.jsdelivr.net",
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/",
            ]

        csp_parts.append("style-src " + " ".join(style_src))
        csp_parts.append("script-src " + " ".join(script_src))

        resp.headers.setdefault("Content-Security-Policy", "; ".join(csp_parts))
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        return resp

    # ---------- Обработчик CSRF ----------
    try:
        from flask_wtf.csrf import CSRFError
    except Exception:
        CSRFError = None  # type: ignore

    if CSRFError is not None:
        from flask import render_template

        @app.errorhandler(CSRFError)  # type: ignore
        def handle_csrf_error(e):
            return render_template("errors/csrf.html", reason=getattr(e, "description", "CSRF error")), 400

    return app
