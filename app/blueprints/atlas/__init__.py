"""Blueprint Atlas — Valorisation des résultats de thèse"""

from flask import Blueprint

atlas_bp = Blueprint('atlas', __name__, template_folder='../../templates')

from app.blueprints.atlas import routes  # noqa: F401, E402
