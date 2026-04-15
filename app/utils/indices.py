"""
Calcul automatique des indices spectraux de télédétection via NumPy.

Toutes les valeurs de bandes sont attendues en réflectance normalisée [0.0 – 1.0].
Retourne float ou None si le calcul est impossible (division par zéro, racine négative…).
"""

import numpy as np


# ══════════════════════════════════════════════════════════
#  ONGLET VÉGÉTATION
# ══════════════════════════════════════════════════════════

def ndvi(nir: float, red: float) -> float | None:
    """
    NDVI — Normalized Difference Vegetation Index
    Formule : (NIR - Red) / (NIR + Red)
    Plage   : -1.0 → +1.0
    Usage   : indicateur général de l'état de la végétation
    """
    nir, red = np.float64(nir), np.float64(red)
    denom = nir + red
    if denom == 0:
        return None
    val = (nir - red) / denom
    return round(float(val), 4)


def savi(nir: float, red: float, L: float = 0.5) -> float | None:
    """
    SAVI — Soil Adjusted Vegetation Index
    Formule : ((NIR - Red) / (NIR + Red + L)) × (1 + L)
    L = 0.5  (recommandé zones semi-arides / Sahel)
    Plage   : ~-1.5 → +1.5
    Usage   : correction de l'effet du sol nu — indispensable en contexte sahélien
    """
    nir, red, L = np.float64(nir), np.float64(red), np.float64(L)
    denom = nir + red + L
    if denom == 0:
        return None
    val = ((nir - red) / denom) * (1.0 + L)
    return round(float(val), 4)


def evi(nir: float, red: float, blue: float,
        G: float = 2.5, C1: float = 6.0, C2: float = 7.5, L: float = 1.0) -> float | None:
    """
    EVI — Enhanced Vegetation Index
    Formule : G × (NIR - Red) / (NIR + C1×Red - C2×Blue + L)
    G=2.5, C1=6, C2=7.5, L=1  (coefficients MODIS standard)
    Plage   : -1.0 → +1.0 (pratiquement 0 → 0.8 sur végétation)
    Usage   : zones à forte biomasse, réduit la saturation atmosphérique
    """
    nir, red, blue = np.float64(nir), np.float64(red), np.float64(blue)
    denom = nir + C1 * red - C2 * blue + L
    if denom == 0:
        return None
    val = G * (nir - red) / denom
    return round(float(val), 4)


def msavi2(nir: float, red: float) -> float | None:
    """
    MSAVI2 — Modified Soil Adjusted Vegetation Index 2
    Formule : (2×NIR + 1 - √((2×NIR+1)² - 8×(NIR-Red))) / 2
    Plage   : ~-1.0 → +1.0
    Usage   : correction avancée de l'effet sol, sans facteur L empirique
    """
    nir, red = np.float64(nir), np.float64(red)
    discriminant = (2.0 * nir + 1.0) ** 2 - 8.0 * (nir - red)
    if discriminant < 0:
        return None
    val = (2.0 * nir + 1.0 - np.sqrt(discriminant)) / 2.0
    return round(float(val), 4)


# ══════════════════════════════════════════════════════════
#  ONGLET FEUX DE BROUSSE
# ══════════════════════════════════════════════════════════

def nbr(nir: float, swir: float) -> float | None:
    """
    NBR — Normalized Burn Ratio
    Formule : (NIR - SWIR) / (NIR + SWIR)
    SWIR    : bande moyen infrarouge (~2.2 µm, ex: Landsat Band 7 / Sentinel-2 Band 12)
    Plage   : -1.0 → +1.0
    Usage   : détection des zones brûlées (valeurs basses = zone brûlée)
    """
    nir, swir = np.float64(nir), np.float64(swir)
    denom = nir + swir
    if denom == 0:
        return None
    val = (nir - swir) / denom
    return round(float(val), 4)


def dnbr(nbr_pre: float, nbr_post: float) -> float:
    """
    dNBR — delta NBR (sévérité de brûlure)
    Formule : NBR_avant - NBR_après
    Plage   : -2.0 → +2.0
    Interprétation USGS :
      < -0.10  → repousse / revégétalisation
      -0.10–0.10 → non brûlé
       0.10–0.27 → faible sévérité
       0.27–0.44 → sévérité modérée
       0.44–0.66 → haute sévérité
      > 0.66   → très haute sévérité
    """
    val = np.float64(nbr_pre) - np.float64(nbr_post)
    return round(float(val), 4)


def bai(red: float, nir: float) -> float | None:
    """
    BAI — Burned Area Index
    Formule : 1 / ((0.1 - Red)² + (0.06 - NIR)²)
    Plage   : 0 → ∞  (valeurs élevées = zones fortement brûlées)
    Usage   : détection de précision des zones brûlées, robuste post-incendie
    """
    red, nir = np.float64(red), np.float64(nir)
    denom = (0.1 - red) ** 2 + (0.06 - nir) ** 2
    if denom == 0:
        return None
    val = 1.0 / denom
    return round(float(val), 2)


# ══════════════════════════════════════════════════════════
#  INTERPRÉTATION AUTOMATIQUE
# ══════════════════════════════════════════════════════════

def interprete_ndvi(v: float) -> dict:
    if v is None:
        return {}
    if v < 0:
        return {'classe': 'Eau / nuage', 'couleur': 'primary', 'icone': 'droplet'}
    if v < 0.10:
        return {'classe': 'Sol nu / sable', 'couleur': 'secondary', 'icone': 'circle'}
    if v < 0.20:
        return {'classe': 'Zone très dégradée', 'couleur': 'danger', 'icone': 'exclamation-triangle'}
    if v < 0.35:
        return {'classe': 'Végétation dégradée', 'couleur': 'warning', 'icone': 'exclamation-circle'}
    if v < 0.50:
        return {'classe': 'Végétation modérée', 'couleur': 'info', 'icone': 'check-circle'}
    if v < 0.65:
        return {'classe': 'Végétation bonne', 'couleur': 'success', 'icone': 'check-circle-fill'}
    return {'classe': 'Végétation dense', 'couleur': 'success', 'icone': 'tree-fill'}


def interprete_savi(v: float) -> dict:
    if v is None:
        return {}
    if v < 0.05:
        return {'classe': 'Sol nu / couvert minimal', 'couleur': 'secondary', 'icone': 'circle'}
    if v < 0.20:
        return {'classe': 'Couvert végétal faible', 'couleur': 'danger', 'icone': 'exclamation-triangle'}
    if v < 0.35:
        return {'classe': 'Couvert dégradé', 'couleur': 'warning', 'icone': 'exclamation-circle'}
    if v < 0.50:
        return {'classe': 'Couvert modéré (Sahel typique)', 'couleur': 'info', 'icone': 'check-circle'}
    return {'classe': 'Couvert végétal élevé', 'couleur': 'success', 'icone': 'check-circle-fill'}


def interprete_evi(v: float) -> dict:
    if v is None:
        return {}
    if v < 0.10:
        return {'classe': 'Sol nu / très faible biomasse', 'couleur': 'secondary', 'icone': 'circle'}
    if v < 0.20:
        return {'classe': 'Faible biomasse', 'couleur': 'warning', 'icone': 'exclamation-circle'}
    if v < 0.40:
        return {'classe': 'Biomasse modérée', 'couleur': 'info', 'icone': 'check-circle'}
    return {'classe': 'Forte biomasse', 'couleur': 'success', 'icone': 'tree-fill'}


def interprete_msavi2(v: float) -> dict:
    if v is None:
        return {}
    if v < 0.10:
        return {'classe': 'Sol très dominant', 'couleur': 'secondary', 'icone': 'circle'}
    if v < 0.25:
        return {'classe': 'Couvert faible, sol important', 'couleur': 'danger', 'icone': 'exclamation-triangle'}
    if v < 0.45:
        return {'classe': 'Couvert partiel', 'couleur': 'warning', 'icone': 'exclamation-circle'}
    if v < 0.60:
        return {'classe': 'Bon couvert végétal', 'couleur': 'info', 'icone': 'check-circle'}
    return {'classe': 'Couvert dense / biomasse élevée', 'couleur': 'success', 'icone': 'tree-fill'}


def interprete_nbr(v: float) -> dict:
    if v is None:
        return {}
    if v < -0.10:
        return {'classe': 'Zone fortement brûlée', 'couleur': 'danger', 'icone': 'fire'}
    if v < 0.10:
        return {'classe': 'Zone brûlée / sol dénudé', 'couleur': 'warning', 'icone': 'exclamation-triangle'}
    if v < 0.30:
        return {'classe': 'Végétation stressée', 'couleur': 'warning', 'icone': 'exclamation-circle'}
    if v < 0.50:
        return {'classe': 'Végétation modérée saine', 'couleur': 'info', 'icone': 'check-circle'}
    return {'classe': 'Végétation dense et saine', 'couleur': 'success', 'icone': 'tree-fill'}


def interprete_dnbr(v: float) -> dict:
    if v < -0.10:
        return {'classe': 'Repousse / revégétalisation', 'couleur': 'success', 'icone': 'arrow-up-circle', 'severite': '—'}
    if v < 0.10:
        return {'classe': 'Non brûlé', 'couleur': 'info', 'icone': 'check-circle', 'severite': 'Nulle'}
    if v < 0.27:
        return {'classe': 'Faible sévérité', 'couleur': 'warning', 'icone': 'exclamation-circle', 'severite': 'Faible'}
    if v < 0.44:
        return {'classe': 'Sévérité modérée', 'couleur': 'warning', 'icone': 'exclamation-triangle', 'severite': 'Modérée'}
    if v < 0.66:
        return {'classe': 'Haute sévérité', 'couleur': 'orange', 'icone': 'fire', 'severite': 'Haute'}
    return {'classe': 'Très haute sévérité', 'couleur': 'danger', 'icone': 'fire', 'severite': 'Très haute'}


def interprete_bai(v: float) -> dict:
    if v is None:
        return {}
    if v < 5:
        return {'classe': 'Zone non brûlée', 'couleur': 'success', 'icone': 'check-circle'}
    if v < 20:
        return {'classe': 'Légèrement brûlée', 'couleur': 'warning', 'icone': 'exclamation-circle'}
    if v < 100:
        return {'classe': 'Zone brûlée', 'couleur': 'danger', 'icone': 'fire'}
    return {'classe': 'Zone intensément brûlée', 'couleur': 'danger', 'icone': 'fire'}
