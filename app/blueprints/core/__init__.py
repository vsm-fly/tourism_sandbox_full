from flask import Blueprint

bp = Blueprint("core", __name__, url_prefix="")  # без template_folder и без префикса "/"
from . import routes  # noqa: E402,F401
