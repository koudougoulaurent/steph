from flask import Blueprint
rapports_bp = Blueprint('rapports', __name__, template_folder='templates')
from app.blueprints.rapports import routes  # noqa
