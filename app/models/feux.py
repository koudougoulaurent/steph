"""
Modèle Feux de Brousse
"""

from datetime import datetime
from app import db


class FeuxBrousse(db.Model):
    __tablename__ = 'feux_brousse'

    id = db.Column(db.Integer, primary_key=True)

    # Identification
    reference = db.Column(db.String(30), unique=True)   # FEU-2024-001
    date_debut = db.Column(db.Date, nullable=False, index=True)
    date_fin = db.Column(db.Date)
    duree_jours = db.Column(db.Integer)

    # Localisation
    zone = db.Column(db.String(120), nullable=False)
    village_proche = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    geojson = db.Column(db.Text)    # périmètre de la zone brûlée

    # Caractéristiques
    superficie_brulee_ha = db.Column(db.Float, default=0.0)
    intensite = db.Column(db.String(20))    # Faible | Moyen | Fort | Très fort
    type_vegetation = db.Column(db.String(80))  # Savane arborée, forêt galerie…
    cause = db.Column(db.String(50))        # Naturelle | Agricole | Pastorale | Inconnu | Criminel
    cause_detail = db.Column(db.Text)

    # Impact
    impact_faune = db.Column(db.String(20))   # Nul | Faible | Moyen | Sévère
    pertes_humaines = db.Column(db.Integer, default=0)
    pertes_animaux = db.Column(db.Integer, default=0)
    villages_affectes = db.Column(db.Integer, default=0)
    cultures_detruites_ha = db.Column(db.Float, default=0.0)
    description_impact = db.Column(db.Text)

    # Intervention
    intervention = db.Column(db.Boolean, default=False)
    agents_mobilises = db.Column(db.Integer, default=0)
    moyens_utilises = db.Column(db.Text)
    date_extinction = db.Column(db.Date)

    # Statut & suivi
    statut = db.Column(db.String(20), default='en_cours')  # en_cours | éteint | surveille
    signale_par = db.Column(db.String(100))
    photos = db.Column(db.Text)   # chemins JSON

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'date_debut': self.date_debut.isoformat() if self.date_debut else None,
            'zone': self.zone,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'superficie_brulee_ha': self.superficie_brulee_ha,
            'intensite': self.intensite,
            'cause': self.cause,
            'statut': self.statut,
            'type': 'feu'
        }

    def __repr__(self):
        return f'<FeuxBrousse {self.reference} - {self.zone}>'
