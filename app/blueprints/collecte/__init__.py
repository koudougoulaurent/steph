from flask import Blueprint
collecte_bp = Blueprint('collecte', __name__, template_folder='templates')
from app.blueprints.collecte import routes  # noqa
