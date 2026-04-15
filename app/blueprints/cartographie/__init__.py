from flask import Blueprint
carto_bp = Blueprint('cartographie', __name__, template_folder='templates')
from app.blueprints.cartographie import routes  # noqa
