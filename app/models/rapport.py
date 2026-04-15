"""
Modèle Rapport
"""

from datetime import datetime
from app import db


class Rapport(db.Model):
    __tablename__ = 'rapports'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True)   # RPT-MENS-2024-03

    # Classification
    type_rapport = db.Column(db.String(30), nullable=False, index=True)
    # mensuel | trimestriel | semestriel | annuel | thematique | incident | campagne

    titre = db.Column(db.String(200), nullable=False)
    periode_debut = db.Column(db.Date, nullable=False)
    periode_fin = db.Column(db.Date, nullable=False)
    zone_couverte = db.Column(db.String(200))

    # Contenu
    resume_executif = db.Column(db.Text)
    contenu_json = db.Column(db.Text)   # Structure de données JSON du rapport
    observations_incluses = db.Column(db.Text)  # JSON list d'IDs

    # Module thématique (pour rapports thématiques)
    theme = db.Column(db.String(60))
    # vegetation | feux | braconnage | sites_vulnerables | terrain | general

    # Statistiques snapshot
    stats_json = db.Column(db.Text)

    # Fichiers générés
    fichier_pdf = db.Column(db.String(300))
    fichier_excel = db.Column(db.String(300))

    # Méta
    auteur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    statut = db.Column(db.String(20), default='brouillon')
    # brouillon | genere | valide | publie | archive

    valide_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    date_validation = db.Column(db.DateTime)
    date_publication = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    TYPE_LABELS = {
        'mensuel': 'Rapport Mensuel',
        'trimestriel': 'Rapport Trimestriel',
        'semestriel': 'Rapport Semestriel',
        'annuel': 'Rapport Annuel',
        'thematique': 'Rapport Thématique',
        'incident': 'Rapport d\'Incident',
        'campagne': 'Rapport de Campagne',
    }

    def get_type_label(self):
        return self.TYPE_LABELS.get(self.type_rapport, self.type_rapport)

    def __repr__(self):
        return f'<Rapport {self.reference} - {self.titre[:40]}>'
