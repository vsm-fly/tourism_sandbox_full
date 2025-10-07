# app/blueprints/banks/__init__.py
from flask import Blueprint

bp = Blueprint("banks", __name__, url_prefix="/banks")

# Регистрируем все view из routes.py
from . import routes  # noqa: E402,F401
