"""
Modèles Couverture Végétale / Occupation des terres (LULC)
"""

from datetime import datetime
from app import db


class ClasseCouverture(db.Model):
    """Nomenclature des classes d'occupation des terres"""
    __tablename__ = 'classes_couverture'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    label = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    couleur_hex = db.Column(db.String(7), default='#3388ff')  # couleur cartographique
    categorie = db.Column(db.String(50))  # Forêt | Prairie | Eau | Agriculture | Urbain | Autre
    ordre_affichage = db.Column(db.Integer, default=0)
    actif = db.Column(db.Boolean, default=True)

    couvertures = db.relationship('Couverture', backref='classe', lazy='dynamic')

    def __repr__(self):
        return f'<ClasseCouverture {self.code} - {self.label}>'


class Couverture(db.Model):
    """
    Données d'occupation des terres par unité spatiale et par année.
    Une ligne = une classe + une zone + une année.
    """
    __tablename__ = 'couvertures'

    id = db.Column(db.Integer, primary_key=True)
    annee = db.Column(db.Integer, nullable=False, index=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classes_couverture.id'), nullable=False)

    # Localisation
    zone = db.Column(db.String(120))           # Nom de l'unité administrative ou écologique
    latitude_centre = db.Column(db.Float)
    longitude_centre = db.Column(db.Float)
    geojson = db.Column(db.Text)               # GeoJSON de la géométrie polygone

    # Superficies
    superficie_ha = db.Column(db.Float, default=0.0)     # Surface en hectares
    superficie_km2 = db.Column(db.Float, default=0.0)

    # Variation (calculée par rapport à l'année précédente)
    variation_ha = db.Column(db.Float, default=0.0)
    taux_variation = db.Column(db.Float, default=0.0)   # en %

    # Source & méta
    source = db.Column(db.String(100))          # Landsat 7, Sentinel-2, Terrain…
    methode = db.Column(db.String(100))         # Télédétection, SIG, Enquête
    precision_pct = db.Column(db.Float)         # Précision de la classification (%)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'annee': self.annee,
            'classe': self.classe.label if self.classe else None,
            'code_classe': self.classe.code if self.classe else None,
            'couleur': self.classe.couleur_hex if self.classe else '#ccc',
            'zone': self.zone,
            'superficie_ha': self.superficie_ha,
            'superficie_km2': self.superficie_km2,
            'variation_ha': self.variation_ha,
            'taux_variation': self.taux_variation,
            'source': self.source,
            'latitude_centre': self.latitude_centre,
            'longitude_centre': self.longitude_centre,
        }

    def __repr__(self):
        return f'<Couverture {self.annee} - {self.zone}>'
