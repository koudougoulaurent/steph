from flask import Blueprint

indices_bp = Blueprint('indices', __name__, template_folder='templates')

from app.blueprints.indices import routes  # noqa: E402, F401
