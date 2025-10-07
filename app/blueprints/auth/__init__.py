from flask import Blueprint

bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/",
    template_folder="../../templates/auth",
)

from . import routes
