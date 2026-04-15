"""
Modèle Sites Vulnérables / Zones à risque environnemental
"""

from datetime import datetime
from app import db


class SiteVulnerable(db.Model):
    __tablename__ = 'sites_vulnerables'

    id = db.Column(db.Integer, primary_key=True)

    # Identification
    reference = db.Column(db.String(30), unique=True)   # SV-2024-001
    nom = db.Column(db.String(150), nullable=False)
    date_identification = db.Column(db.Date, nullable=False, index=True)

    # Localisation
    zone = db.Column(db.String(120))
    localite = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    geojson = db.Column(db.Text)

    # Caractéristiques
    type_site = db.Column(db.String(60))
    # Exemples : Corridor faunique | Zone humide | Forêt classée | Reboisement | Bassin versant
    #            Aire protégée | Site Ramsar | Habitat d'espèce menacée

    superficie_ha = db.Column(db.Float, default=0.0)
    altitude_m = db.Column(db.Float)

    # Évaluation de la vulnérabilité
    niveau_vulnerabilite = db.Column(db.String(20))  # Faible | Moyen | Élevé | Critique
    score_vulnerabilite = db.Column(db.Integer)       # 0-100

    # Pressions identifiées (multi-valeurs stockées en JSON)
    pressions = db.Column(db.Text)
    # Ex: ["Défrichement", "Pâturage excessif", "Exploitation minière", "Pollution"]

    # Espèces présentes / valeur écologique
    especes_cles = db.Column(db.Text)
    valeur_ecologique = db.Column(db.String(20))    # Faible | Moyenne | Haute | Très haute

    # Mesures de protection existantes
    mesures_protection = db.Column(db.Text)
    classement_legal = db.Column(db.String(80))   # Statut légal éventuel
    gestionnaire = db.Column(db.String(100))

    # Suivi
    derniere_visite = db.Column(db.Date)
    frequence_surveillance = db.Column(db.String(30))  # Mensuelle | Trimestrielle | Annuelle
    statut = db.Column(db.String(20), default='actif')  # actif | archive | restaure

    observations = db.Column(db.Text)
    photos = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'nom': self.nom,
            'type_site': self.type_site,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'niveau_vulnerabilite': self.niveau_vulnerabilite,
            'score_vulnerabilite': self.score_vulnerabilite,
            'zone': self.zone,
            'statut': self.statut,
            'type': 'site_vulnerable'
        }

    def __repr__(self):
        return f'<SiteVulnerable {self.reference} - {self.nom}>'
