"""
VégéSuivi Pro — Lecteur de données terrain Shapefile
-----------------------------------------------------
Prend en charge :
  • Dossier contenant le bundle SHP (shp + dbf + shx)
  • Fichier ZIP encapsulant le bundle
  • Upload multi-fichiers (composants SHP individuels)

Dépendances : pyshp (shapefile), zipfile (stdlib), json (stdlib)
"""

import os
import io
import json
import uuid
import zipfile
import logging

import shapefile  # pyshp

logger = logging.getLogger(__name__)

# ── Types de géométrie shapefile ──────────────────────────────────────────────
_GEOM_TYPES = {
    0:  'Null Shape',
    1:  'Point',
    3:  'Polyligne',
    5:  'Polygone',
    8:  'MultiPoint',
    11: 'PointZ',
    13: 'PolyligneZ',
    15: 'PolygoneZ',
    18: 'MultiPointZ',
    21: 'PointM',
    23: 'PolyligneM',
    25: 'PolygoneM',
    28: 'MultiPointM',
    31: 'MultiPatch',
}

_GEOM_ICONS = {
    'Point':     'bi-circle-fill',
    'PointZ':    'bi-circle-fill',
    'Polyligne': 'bi-slash-lg',
    'PolyligneZ':'bi-slash-lg',
    'Polygone':  'bi-pentagon',
    'PolygoneZ': 'bi-pentagon',
    'MultiPoint':'bi-circle',
}

_TYPE_CHAMP = {
    'C': 'Texte',
    'N': 'Numérique',
    'F': 'Décimal',
    'D': 'Date',
    'L': 'Booléen',
    'M': 'Mémo',
}


# ══════════════════════════════════════════════════════════════════════════════
#  Extraction ZIP
# ══════════════════════════════════════════════════════════════════════════════

def extraire_zip(chemin_zip: str, dossier_dest: str) -> str:
    """
    Extrait un fichier ZIP dans dossier_dest.
    Aplatit un éventuel sous-dossier unique.
    Retourne le dossier d'extraction.
    """
    os.makedirs(dossier_dest, exist_ok=True)
    with zipfile.ZipFile(chemin_zip, 'r') as z:
        # Sécurité : rejeter les chemins qui sortent du dossier
        for member in z.infolist():
            member_path = os.path.realpath(os.path.join(dossier_dest, member.filename))
            if not member_path.startswith(os.path.realpath(dossier_dest)):
                raise ValueError(f'Chemin ZIP suspect : {member.filename}')
        z.extractall(dossier_dest)
    return dossier_dest


def sauver_fichiers_multiples(fichiers_upload: list, dossier_dest: str) -> str:
    """
    Sauvegarde une liste de fichiers Flask (request.files.getlist)
    dans dossier_dest. Retourne le dossier.
    """
    os.makedirs(dossier_dest, exist_ok=True)
    for f in fichiers_upload:
        if f and f.filename:
            nom = os.path.basename(f.filename)  # protection path traversal
            f.save(os.path.join(dossier_dest, nom))
    return dossier_dest


def trouver_shp(dossier: str) -> str | None:
    """Trouve le premier fichier .shp dans dossier (1 niveau de récursion)."""
    for root, _, files in os.walk(dossier):
        for f in sorted(files):
            if f.lower().endswith('.shp'):
                return os.path.join(root, f)
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  Analyse métadonnées
# ══════════════════════════════════════════════════════════════════════════════

def analyser_shp(chemin_shp: str) -> dict:
    """
    Lit un fichier .shp et retourne un dictionnaire de métadonnées :
    type_geometrie, nombre_entites, attributs, bbox, srid.
    """
    sf = shapefile.Reader(chemin_shp, encoding='utf-8')

    type_geom = _GEOM_TYPES.get(sf.shapeType, f'Type {sf.shapeType}')
    n_entites = len(sf)

    # Champs attributaires (ignorer champ DeletionFlag en index 0)
    champs = []
    for f in sf.fields[1:]:
        champs.append({
            'nom': f[0],
            'type': _TYPE_CHAMP.get(f[1], f[1]),
            'longueur': f[2],
            'decimales': f[3] if len(f) > 3 else 0,
        })

    # Bounding box [xmin, ymin, xmax, ymax]
    bbox = list(sf.bbox) if sf.shapeType != 0 else None

    # SRID depuis .prj
    srid = _lire_srid(chemin_shp)

    nom_fichier = os.path.splitext(os.path.basename(chemin_shp))[0]

    sf.close()

    return {
        'nom_fichier': nom_fichier,
        'type_geometrie': type_geom,
        'icone_geometrie': _GEOM_ICONS.get(type_geom, 'bi-geo'),
        'nombre_entites': n_entites,
        'attributs': champs,
        'bbox': bbox,
        'srid': srid,
        'srid_label': f'EPSG:{srid}' if srid else 'Inconnu',
    }


def _lire_srid(chemin_shp: str) -> int | None:
    """Lit le SRID depuis le .prj (détection heuristique)."""
    prj = os.path.splitext(chemin_shp)[0] + '.prj'
    if not os.path.exists(prj):
        return None
    try:
        with open(prj, 'r', encoding='utf-8', errors='ignore') as f:
            wkt = f.read()
        if 'WGS_1984' in wkt or 'WGS 1984' in wkt or 'EPSG:4326' in wkt:
            return 4326
        if 'RGF93' in wkt or 'EPSG:2154' in wkt:
            return 2154
        if 'WGS_84_UTM' in wkt or 'UTM zone' in wkt.lower():
            # Cherche numéro EPSG explicite
            import re
            m = re.search(r'AUTHORITY\["EPSG","(\d+)"\]', wkt)
            if m:
                return int(m.group(1))
        return None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  Conversion GeoJSON
# ══════════════════════════════════════════════════════════════════════════════

def shp_to_geojson(chemin_shp: str, max_features: int = 500) -> dict:
    """
    Convertit un Shapefile en FeatureCollection GeoJSON.
    Limité à max_features entités pour la performance (aperçu carte).
    Retourne: {type, features, total_features, truncated}
    """
    sf = shapefile.Reader(chemin_shp, encoding='utf-8')
    champs = [f[0] for f in sf.fields[1:]]
    total = len(sf)
    features = []

    for i, sr in enumerate(sf.iterShapeRecords()):
        if i >= max_features:
            break
        try:
            geom = sr.shape.__geo_interface__
        except Exception:
            continue

        props = {}
        for k, v in zip(champs, sr.record):
            # Sérialisation JSON-safe
            if hasattr(v, 'isoformat'):
                props[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, type(None))):
                props[k] = v
            else:
                props[k] = str(v)

        features.append({
            'type': 'Feature',
            'geometry': geom,
            'properties': props,
        })

    sf.close()

    return {
        'type': 'FeatureCollection',
        'features': features,
        'total_features': total,
        'truncated': total > max_features,
    }


def shp_to_geojson_json(chemin_shp: str, max_features: int = 500) -> str:
    """Retourne la chaîne JSON du GeoJSON (pour stocker en DB ou répondre en HTTP)."""
    return json.dumps(shp_to_geojson(chemin_shp, max_features), ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
#  Validation du bundle
# ══════════════════════════════════════════════════════════════════════════════

def valider_bundle(dossier: str) -> tuple[bool, str]:
    """
    Vérifie qu'un dossier contient un bundle SHP valide (.shp + .dbf).
    Retourne (True, '') ou (False, message_erreur).
    """
    shp = trouver_shp(dossier)
    if not shp:
        return False, 'Aucun fichier .shp trouvé dans le ZIP.'
    base = os.path.splitext(shp)[0]
    if not os.path.exists(base + '.dbf') and not os.path.exists(base + '.DBF'):
        return False, 'Fichier .dbf manquant (requis avec .shp).'
    if not os.path.exists(base + '.shx') and not os.path.exists(base + '.SHX'):
        return False, 'Fichier .shx manquant (requis avec .shp).'
    return True, ''
