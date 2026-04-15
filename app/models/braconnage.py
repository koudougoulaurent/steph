"""
Modèle Indicateurs de Braconnage
"""

from datetime import datetime
from app import db


class IndicateurBraconnage(db.Model):
    __tablename__ = 'indicateurs_braconnage'

    id = db.Column(db.Integer, primary_key=True)

    # Identification
    reference = db.Column(db.String(30), unique=True)   # BR-2024-001
    date_constat = db.Column(db.Date, nullable=False, index=True)
    heure_constat = db.Column(db.Time)

    # Localisation
    zone = db.Column(db.String(120), nullable=False)
    localite = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    geojson = db.Column(db.Text)

    # Type d'indicateur
    type_indicateur = db.Column(db.String(60), nullable=False)
    # Piège | Collet | Arme | Cadavre animal | Camp de braconnier
    # Traces de chasse | Carcasse | Trafic espèce | Charbon illégal | Coupe illégale

    # Détails
    description = db.Column(db.Text)
    especes_concernees = db.Column(db.Text)  # JSON list
    nombre_indices = db.Column(db.Integer, default=1)   # Nb de pièges/collets/etc.

    # Gravité
    niveau_gravite = db.Column(db.String(20))    # Faible | Moyen | Grave | Critique
    activite_recente = db.Column(db.Boolean, default=True)  # activité récente ou ancienne

    # Réponse
    alerte_emise = db.Column(db.Boolean, default=False)
    saisies_effectuees = db.Column(db.Boolean, default=False)
    detail_saisies = db.Column(db.Text)
    arrestations = db.Column(db.Integer, default=0)
    suite_judiciaire = db.Column(db.Boolean, default=False)
    numero_pv = db.Column(db.String(50))

    # Statut
    statut = db.Column(db.String(20), default='nouveau')
    # nouveau | en_cours | traite | archive | transmis_justice

    signale_par = db.Column(db.String(100))
    source_info = db.Column(db.String(80))   # Patrouille | Riverain | Informateur | Drone
    photos = db.Column(db.Text)
    observations = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'date_constat': self.date_constat.isoformat() if self.date_constat else None,
            'type_indicateur': self.type_indicateur,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'zone': self.zone,
            'niveau_gravite': self.niveau_gravite,
            'statut': self.statut,
            'type': 'braconnage'
        }

    def __repr__(self):
        return f'<IndicateurBraconnage {self.reference} - {self.type_indicateur}>'
