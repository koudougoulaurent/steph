"""
Modèle ResultatAtlas — Valorisation des résultats de thèse
Évolution et projection de la couverture végétale (1986–2050)
"""

from datetime import datetime
from app import db


class ResultatAtlas(db.Model):
    """
    Résultats de thèse : occupation des terres par classe, par année et par scénario.
    Une ligne = une classe d'occupation × une année × un scénario.
    Couvre les données observées (télédétection) et les projections modélisées.
    """
    __tablename__ = 'resultats_atlas'

    id = db.Column(db.Integer, primary_key=True)
    annee = db.Column(db.Integer, nullable=False, index=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classes_couverture.id'), nullable=False)

    zone = db.Column(db.String(120), default="Zone d'étude")

    # Superficies
    superficie_ha  = db.Column(db.Float, default=0.0)
    superficie_pct = db.Column(db.Float, default=0.0)  # % de la superficie totale

    # Type de donnée : 'observe' | 'projete'
    type_donnee = db.Column(db.String(20), default='observe', index=True)

    # Scénario de projection : 'tendanciel' | 'optimiste' | 'pessimiste'
    # (pour type_donnee='observe', toujours 'tendanciel')
    scenario = db.Column(db.String(30), default='tendanciel', index=True)

    # Géométrie optionnelle — polygon GeoJSON de la classe pour cette année
    geojson          = db.Column(db.Text)
    latitude_centre  = db.Column(db.Float)
    longitude_centre = db.Column(db.Float)

    notes      = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation
    classe = db.relationship('ClasseCouverture', lazy='joined')

    # ──────────────────────────────────────────────────────────────
    def to_dict(self):
        return {
            'id':             self.id,
            'annee':          self.annee,
            'classe_id':      self.classe_id,
            'classe_label':   self.classe.label      if self.classe else '',
            'classe_couleur': self.classe.couleur_hex if self.classe else '#ccc',
            'zone':           self.zone,
            'superficie_ha':  round(self.superficie_ha,  2),
            'superficie_pct': round(self.superficie_pct, 2),
            'type_donnee':    self.type_donnee,
            'scenario':       self.scenario,
        }

    def __repr__(self):
        return f'<ResultatAtlas {self.annee} {self.classe_id} {self.scenario}>'
