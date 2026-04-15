"""
Modèle : Couche de données terrain importée (Shapefile)
"""

from datetime import datetime
from app import db


class CoucheDonneesTerrain(db.Model):
    """
    Couche SIG importée depuis un Shapefile.
    Stocke les métadonnées, le chemin des fichiers originaux
    et un aperçu GeoJSON (limité à 500 entités).
    """
    __tablename__ = 'couches_donnees_terrain'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False)
    # CTR-2024-001

    # ── Métadonnées utilisateur ──────────────────────────────────
    nom = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    source = db.Column(db.String(200))       # Ex: "Mission terrain Mars 2024"
    date_acquisition = db.Column(db.Date)    # Date de collecte terrain

    # ── Métadonnées SIG (remplies automatiquement) ───────────────
    type_geometrie = db.Column(db.String(30))  # Point, Polygone, Polyligne...
    icone_geometrie = db.Column(db.String(40), default='bi-geo')
    nombre_entites = db.Column(db.Integer, default=0)
    bbox_json = db.Column(db.Text)            # JSON [xmin,ymin,xmax,ymax]
    attributs_json = db.Column(db.Text)       # JSON [{nom,type,longueur}]
    srid = db.Column(db.Integer)              # EPSG code ex: 4326
    geojson_apercu = db.Column(db.Text)       # GeoJSON partiel (500 entités max)

    # ── Fichiers ─────────────────────────────────────────────────
    dossier_shp = db.Column(db.String(500))   # chemin absolu dossier extrait
    nom_fichier_shp = db.Column(db.String(200))  # nom.shp sans chemin
    taille_octets = db.Column(db.BigInteger, default=0)

    # ── Traçabilité ──────────────────────────────────────────────
    uploaded_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    date_upload = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    statut = db.Column(db.String(20), default='valide')
    # valide | erreur | en_traitement

    notes_erreur = db.Column(db.Text)

    # Relation
    uploader = db.relationship('User', foreign_keys=[uploaded_by],
                               backref='couches_terrain')

    # ── Propriétés calculées ─────────────────────────────────────

    @property
    def bbox(self) -> list | None:
        import json
        if self.bbox_json:
            try:
                return json.loads(self.bbox_json)
            except Exception:
                return None
        return None

    @property
    def attributs(self) -> list:
        import json
        if self.attributs_json:
            try:
                return json.loads(self.attributs_json)
            except Exception:
                return []
        return []

    @property
    def srid_label(self) -> str:
        return f'EPSG:{self.srid}' if self.srid else 'Inconnu'

    @property
    def taille_lisible(self) -> str:
        if not self.taille_octets:
            return '—'
        if self.taille_octets < 1024:
            return f'{self.taille_octets} o'
        if self.taille_octets < 1024 ** 2:
            return f'{self.taille_octets / 1024:.1f} Ko'
        return f'{self.taille_octets / 1024 ** 2:.1f} Mo'

    @property
    def chemin_shp(self) -> str | None:
        if self.dossier_shp and self.nom_fichier_shp:
            import os
            return os.path.join(self.dossier_shp, self.nom_fichier_shp)
        return None

    def couleur_badge(self) -> str:
        mapping = {
            'Point':     'primary',
            'PointZ':    'primary',
            'Polyligne': 'info',
            'PolyligneZ':'info',
            'Polygone':  'success',
            'PolygoneZ': 'success',
            'MultiPoint':'secondary',
        }
        return mapping.get(self.type_geometrie, 'secondary')

    def __repr__(self):
        return f'<CoucheDonneesTerrain {self.reference} — {self.nom}>'
