"""
Modèles Collecte de données terrain
"""

from datetime import datetime
from app import db


class CampagneCollecte(db.Model):
    """
    Campagne de collecte de données sur le terrain
    (mission, tournée d'inspection, inventaire…)
    """
    __tablename__ = 'campagnes_collecte'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True)   # CAM-2024-001
    nom = db.Column(db.String(150), nullable=False)
    objectif = db.Column(db.Text)

    date_debut = db.Column(db.Date, nullable=False, index=True)
    date_fin_prevue = db.Column(db.Date)
    date_fin_reelle = db.Column(db.Date)

    zone_couverte = db.Column(db.String(200))
    responsable_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    equipe = db.Column(db.Text)           # JSON list des agents

    protocole = db.Column(db.Text)         # Protocole de collecte
    materiels = db.Column(db.Text)         # Équipements utilisés

    statut = db.Column(db.String(20), default='planifie')
    # planifie | en_cours | termine | annule

    rapport_terrain = db.Column(db.Text)
    observations_generales = db.Column(db.Text)
    fichiers_joints = db.Column(db.Text)   # JSON

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Observations liées
    observations = db.relationship('ObservationTerrain', backref='campagne', lazy='dynamic',
                                   cascade='all, delete-orphan')

    @property
    def count_observations(self):
        return self.observations.count()

    def __repr__(self):
        return f'<CampagneCollecte {self.reference} - {self.nom}>'


class ObservationTerrain(db.Model):
    """
    Observation individuelle collectée sur le terrain.
    Peut être liée à une campagne ou saisie de manière autonome.
    """
    __tablename__ = 'observations_terrain'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True)  # OBS-2024-001

    campagne_id = db.Column(db.Integer, db.ForeignKey('campagnes_collecte.id'))
    agent_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))

    date_observation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Localisation GPS
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude_m = db.Column(db.Float)
    precision_gps_m = db.Column(db.Float)   # Précision GPS en mètres
    zone = db.Column(db.String(120))

    # Type d'observation
    categorie = db.Column(db.String(40), nullable=False)
    # vegetation | faune | feu | sol | eau | infrastructure | braconnage | autre

    # Données collectées
    titre = db.Column(db.String(150))
    description = db.Column(db.Text, nullable=False)

    # Données quantitatives
    valeur_numerique = db.Column(db.Float)
    unite = db.Column(db.String(30))

    # Évaluation terrain
    etat_general = db.Column(db.String(20))   # Bon | Moyen | Dégradé | Très dégradé
    niveau_alerte = db.Column(db.String(20))  # Normal | Attention | Alerte | Urgence

    # Médias
    photos = db.Column(db.Text)    # JSON liste de chemins
    audio = db.Column(db.Text)
    video = db.Column(db.Text)

    # Données supplémentaires (JSON flexible)
    donnees_supplementaires = db.Column(db.Text)

    validee = db.Column(db.Boolean, default=False)
    valide_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    date_validation = db.Column(db.DateTime)
    commentaire_validation = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'date': self.date_observation.isoformat() if self.date_observation else None,
            'categorie': self.categorie,
            'titre': self.titre,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'zone': self.zone,
            'etat_general': self.etat_general,
            'niveau_alerte': self.niveau_alerte,
            'validee': self.validee,
            'type': 'observation'
        }

    def __repr__(self):
        return f'<ObservationTerrain {self.reference} - {self.categorie}>'
