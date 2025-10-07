from flask import Blueprint
bp = Blueprint("refs", __name__, url_prefix="/refs", template_folder="templates")
from . import routes  # noqa
