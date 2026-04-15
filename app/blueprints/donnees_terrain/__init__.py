"""
Blueprint Données Terrain — Import et gestion des couches Shapefile
"""
from flask import Blueprint

donnees_bp = Blueprint('donnees_terrain', __name__,
                       template_folder='templates')

# Doit être importé APRÈS la définition de donnees_bp pour éviter les imports circulaires
from app.blueprints.donnees_terrain import routes  # noqa: F401, E402
