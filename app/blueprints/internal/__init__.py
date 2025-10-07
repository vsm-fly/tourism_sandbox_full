from flask import Blueprint
bp = Blueprint("internal", __name__, url_prefix="/internal")
from . import routes  # noqa
