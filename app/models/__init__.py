"""
VégéSuivi Pro - Modèles de données
"""

from app.models.user import User
from app.models.couverture import Couverture, ClasseCouverture
from app.models.feux import FeuxBrousse
from app.models.sites_vulnerables import SiteVulnerable
from app.models.braconnage import IndicateurBraconnage
from app.models.collecte import CampagneCollecte, ObservationTerrain
from app.models.rapport import Rapport
from app.models.donnees_shp import CoucheDonneesTerrain

__all__ = [
    'User', 'Couverture', 'ClasseCouverture',
    'FeuxBrousse', 'SiteVulnerable', 'IndicateurBraconnage',
    'CampagneCollecte', 'ObservationTerrain', 'Rapport',
    'CoucheDonneesTerrain',
]
