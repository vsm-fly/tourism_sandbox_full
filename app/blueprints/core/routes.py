from flask import render_template, current_app, url_for
from flask_login import login_required, current_user
from . import bp

# Безопасная генерация URL: если endpoint отсутствует — вернём "#"
def _safe_url(endpoint: str, **kwargs) -> str:
    try:
        return url_for(endpoint, **kwargs)
    except Exception:
        return "#"

# Дадим хелпер шаблонам
@bp.app_context_processor
def inject_helpers():
    return {"safe_url": _safe_url}

@bp.route("/")
@login_required
def dashboard():
    return render_template("core/dashboard.html", user=current_user)
