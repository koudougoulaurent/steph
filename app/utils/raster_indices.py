"""
Traitement des images satellites GeoTIFF pour le calcul d'indices spectraux.

Supporte :
  - TIF multi-bandes (ex. produit Sentinel-2, Landsat stack)
  - TIF mono-bande (un fichier par bande)

Bibliothèques : tifffile (lecture TIF), numpy (calcul raster), matplotlib (visualisation).
Pas de dépendance GDAL / rasterio → fonctionne nativement sur Windows.
"""

import os
import uuid
import base64
from io import BytesIO

import numpy as np

# matplotlib doit utiliser le backend non-interactif (serveur Flask)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap


# ══════════════════════════════════════════════════════════════════════════════
#  Lecture des bandes TIF
# ══════════════════════════════════════════════════════════════════════════════

def lire_bande(filepath: str, numero_bande: int = 1) -> np.ndarray:
    """
    Lit une bande depuis un fichier TIF.

    :param filepath:     Chemin absolu vers le fichier .tif / .tiff
    :param numero_bande: Numéro de bande 1-indexé :
                         - TIF multi-bandes : sélectionne la bande correspondante
                         - TIF mono-bande   : toujours 1
    :return: Array 2D float32 normalisé en réflectance [0.0 – 1.0]
             (si les valeurs dépassent 1.0, détection automatique et normalisation)
    """
    import tifffile

    with tifffile.TiffFile(filepath) as tif:
        data = tif.asarray()   # shape : (H, W) ou (B, H, W) ou (H, W, B)

    # ── Normalisation des axes ─────────────────────────────────────────────
    if data.ndim == 2:
        # Mono-bande — H × W
        arr = data.astype(np.float32)
    elif data.ndim == 3:
        # Déterminer si (B, H, W) ou (H, W, B)
        if data.shape[0] <= 20 and data.shape[0] < data.shape[1]:
            # (B, H, W) — nombre de bandes en premier
            b_idx = numero_bande - 1          # 0-indexé
            if b_idx >= data.shape[0]:
                raise ValueError(
                    f"La bande {numero_bande} n'existe pas. "
                    f"Ce fichier contient {data.shape[0]} bande(s)."
                )
            arr = data[b_idx].astype(np.float32)
        else:
            # (H, W, B) — bandes en dernier
            b_idx = numero_bande - 1
            if b_idx >= data.shape[2]:
                raise ValueError(
                    f"La bande {numero_bande} n'existe pas. "
                    f"Ce fichier contient {data.shape[2]} bande(s)."
                )
            arr = data[:, :, b_idx].astype(np.float32)
    else:
        raise ValueError(f"Format TIF non supporté : {data.ndim} dimensions.")

    # ── Normalisation en réflectance [0, 1] ────────────────────────────────
    # Données 16-bit entières (ex. Sentinel-2 L2A : 0–10000)
    max_val = arr.max()
    if max_val > 10.0:
        if max_val <= 10000:
            arr = arr / 10000.0    # Sentinel-2 / Landsat quantification factor
        elif max_val <= 65535:
            arr = arr / 65535.0    # 16-bit générique
        else:
            arr = arr / max_val    # fallback

    # ── Masquer les nodata (valeurs <0 ou >1 après normalisation) ──────────
    arr = np.where((arr < 0) | (arr > 1.5), np.nan, arr)
    arr = np.clip(arr, 0.0, 1.0)

    return arr


def nombre_bandes(filepath: str) -> int:
    """Retourne le nombre de bandes d'un fichier TIF."""
    import tifffile
    with tifffile.TiffFile(filepath) as tif:
        data = tif.asarray()
    if data.ndim == 2:
        return 1
    elif data.ndim == 3:
        return data.shape[0] if data.shape[0] <= 20 else data.shape[2]
    return 1


# ══════════════════════════════════════════════════════════════════════════════
#  Calcul des indices sur array numpy (pixel par pixel)
# ══════════════════════════════════════════════════════════════════════════════

def _safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Division sécurisée — met NaN là où le dénominateur est nul."""
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(b == 0, np.nan, a / b)
    return result.astype(np.float32)


def calc_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return _safe_div(nir - red, nir + red)


def calc_savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
    return _safe_div((nir - red) * (1 + L), nir + red + L)


def calc_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray,
             G=2.5, C1=6.0, C2=7.5, L=1.0) -> np.ndarray:
    denom = nir + C1 * red - C2 * blue + L
    return _safe_div(G * (nir - red), denom)


def calc_msavi2(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    inner = (2 * nir + 1) ** 2 - 8 * (nir - red)
    sqrt_inner = np.where(inner < 0, np.nan, np.sqrt(np.maximum(inner, 0)))
    return ((2 * nir + 1 - sqrt_inner) / 2).astype(np.float32)


def calc_nbr(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    return _safe_div(nir - swir, nir + swir)


def calc_dnbr(nbr_pre: np.ndarray, nbr_post: np.ndarray) -> np.ndarray:
    return (nbr_pre - nbr_post).astype(np.float32)


def calc_bai(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    denom = (0.1 - red) ** 2 + (0.06 - nir) ** 2
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(denom == 0, np.nan, 1.0 / denom)
    return result.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
#  Statistiques
# ══════════════════════════════════════════════════════════════════════════════

def statistiques(arr: np.ndarray) -> dict:
    """Calcule les statistiques d'un array d'indice (ignore NaN)."""
    valid = arr[~np.isnan(arr)]
    total = arr.size
    n_valid = valid.size
    n_nodata = total - n_valid

    if n_valid == 0:
        return {
            'min': None, 'max': None, 'mean': None, 'std': None,
            'mediane': None, 'n_pixels': total, 'n_valides': 0,
            'pct_nodata': 100.0, 'resolution': f'{arr.shape[1]} × {arr.shape[0]} px'
        }

    return {
        'min':        round(float(valid.min()), 4),
        'max':        round(float(valid.max()), 4),
        'mean':       round(float(valid.mean()), 4),
        'std':        round(float(valid.std()), 4),
        'mediane':    round(float(np.median(valid)), 4),
        'n_pixels':   total,
        'n_valides':  n_valid,
        'pct_nodata': round(100.0 * n_nodata / total, 1),
        'resolution': f'{arr.shape[1]} × {arr.shape[0]} px',
    }


def distribution_ndvi(arr: np.ndarray) -> list:
    """Distribution par classes NDVI."""
    valid = arr[~np.isnan(arr)]
    total = max(valid.size, 1)
    classes = [
        ('Eau / nuage',           '#2166ac', valid < 0),
        ('Sol nu / zone brûlée',  '#d73027', (valid >= 0)    & (valid < 0.1)),
        ('Végétation très faible','#fdae61', (valid >= 0.1)  & (valid < 0.2)),
        ('Végétation faible',     '#fee08b', (valid >= 0.2)  & (valid < 0.3)),
        ('Végétation modérée',    '#d9ef8b', (valid >= 0.3)  & (valid < 0.5)),
        ('Végétation dense',      '#91cf60', (valid >= 0.5)  & (valid < 0.7)),
        ('Végétation très dense', '#1a9850', valid >= 0.7),
    ]
    return [{'label': lbl, 'color': col, 'pct': round(100 * mask.sum() / total, 1)}
            for lbl, col, mask in classes]


def distribution_nbr(arr: np.ndarray) -> list:
    """Distribution par classes USGS dNBR (ou NBR)."""
    valid = arr[~np.isnan(arr)]
    total = max(valid.size, 1)
    classes = [
        ('Régénération post-feu', '#1a9850', valid < -0.25),
        ('Non brûlé',             '#91cf60', (valid >= -0.25) & (valid < 0.1)),
        ('Zone non brûlée',       '#fee08b', (valid >= 0.1)  & (valid < 0.27)),
        ('Faible sévérité',       '#fdae61', (valid >= 0.27) & (valid < 0.44)),
        ('Sévérité modérée basse','#f46d43', (valid >= 0.44) & (valid < 0.66)),
        ('Sévérité modérée élevée','#d73027',(valid >= 0.66) & (valid < 1.3)),
        ('Haute sévérité',        '#740000', valid >= 1.3),
    ]
    return [{'label': lbl, 'color': col, 'pct': round(100 * mask.sum() / total, 1)}
            for lbl, col, mask in classes]


def distribution_bai(arr: np.ndarray) -> list:
    """Distribution par plages BAI."""
    valid = arr[~np.isnan(arr)]
    total = max(valid.size, 1)
    classes = [
        ('Non brûlé (BAI < 5)',       '#1a9850', valid < 5),
        ('Probablement brûlé (5–15)',  '#fdae61', (valid >= 5)  & (valid < 15)),
        ('Zone brûlée (15–30)',        '#f46d43', (valid >= 15) & (valid < 30)),
        ('Feu actif / Brûlé sévère (≥30)', '#740000', valid >= 30),
    ]
    return [{'label': lbl, 'color': col, 'pct': round(100 * mask.sum() / total, 1)}
            for lbl, col, mask in classes]


# ══════════════════════════════════════════════════════════════════════════════
#  Visualisation — génère une image PNG base64
# ══════════════════════════════════════════════════════════════════════════════

# Colormaps personnalisées
_CMAP_NDVI  = LinearSegmentedColormap.from_list(
    'ndvi_veg', ['#d73027','#fdae61','#ffffbf','#d9ef8b','#91cf60','#1a9850'], N=256)
_CMAP_FIRE  = LinearSegmentedColormap.from_list(
    'fire_nbr',  ['#1a9850','#91cf60','#fee08b','#fdae61','#f46d43','#d73027','#740000'], N=256)
_CMAP_BAI   = LinearSegmentedColormap.from_list(
    'bai_burn',  ['#d9ef8b','#fdae61','#f46d43','#a50026','#4d0000'], N=256)
_CMAP_EVI   = LinearSegmentedColormap.from_list(
    'evi_veg',   ['#fff5eb','#fee6ce','#a6d96a','#1a9850'], N=256)


def _redim_pour_affichage(arr: np.ndarray, max_px: int = 800) -> np.ndarray:
    """Réduit la résolution pour l'affichage si l'image est très grande."""
    h, w = arr.shape
    if max(h, w) <= max_px:
        return arr
    factor = max(h, w) // max_px + 1
    return arr[::factor, ::factor]


def generer_visualisation(
    arr: np.ndarray,
    titre: str,
    cmap,
    vmin: float,
    vmax: float,
    label_barre: str = '',
    dpi: int = 120,
) -> str:
    """
    Génère une visualisation colorimétrique de l'indice.
    :return: Chaîne base64 PNG prête pour <img src="data:image/png;base64,…">
    """
    arr_aff = _redim_pour_affichage(arr)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=dpi)
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    im = ax.imshow(arr_aff, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')

    # Barre de couleur
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.ax.yaxis.set_tick_params(color='white', labelsize=8)
    cbar.set_label(label_barre, color='white', fontsize=9)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
    cbar.outline.set_edgecolor('#555577')

    ax.set_title(titre, color='white', fontsize=11, pad=10, fontweight='bold')
    ax.axis('off')

    plt.tight_layout(pad=0.5)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight',
                facecolor=fig.get_facecolor(), dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


# ══════════════════════════════════════════════════════════════════════════════
#  Pipeline complet par indice
# ══════════════════════════════════════════════════════════════════════════════

def pipeline_ndvi(nir_path, red_path, nir_bande=1, red_bande=1) -> dict:
    nir = lire_bande(nir_path, nir_bande)
    red = lire_bande(red_path, red_bande)
    arr = calc_ndvi(nir, red)
    return {
        'nom': 'NDVI',
        'array': arr,
        'image_b64': generer_visualisation(arr, 'NDVI — Indice de végétation', _CMAP_NDVI, -1, 1, 'NDVI'),
        'stats': statistiques(arr),
        'distribution': distribution_ndvi(arr),
        'vmin': -1, 'vmax': 1,
    }


def pipeline_savi(nir_path, red_path, nir_bande=1, red_bande=1, L=0.5) -> dict:
    nir = lire_bande(nir_path, nir_bande)
    red = lire_bande(red_path, red_bande)
    arr = calc_savi(nir, red, L)
    return {
        'nom': 'SAVI',
        'array': arr,
        'image_b64': generer_visualisation(arr, f'SAVI (L={L}) — Végétation corrigée sol', _CMAP_NDVI, -1, 1, 'SAVI'),
        'stats': statistiques(arr),
        'distribution': distribution_ndvi(arr),
        'vmin': -1, 'vmax': 1,
    }


def pipeline_evi(nir_path, red_path, blue_path, nir_b=1, red_b=1, blue_b=1) -> dict:
    nir  = lire_bande(nir_path, nir_b)
    red  = lire_bande(red_path, red_b)
    blue = lire_bande(blue_path, blue_b)
    arr  = calc_evi(nir, red, blue)
    arr  = np.clip(arr, -1, 2)    # EVI peut exploser sur certaines zones
    return {
        'nom': 'EVI',
        'array': arr,
        'image_b64': generer_visualisation(arr, 'EVI — Enhanced Vegetation Index', _CMAP_EVI, 0, 0.8, 'EVI'),
        'stats': statistiques(arr),
        'distribution': distribution_ndvi(arr),
        'vmin': 0, 'vmax': 0.8,
    }


def pipeline_msavi2(nir_path, red_path, nir_bande=1, red_bande=1) -> dict:
    nir = lire_bande(nir_path, nir_bande)
    red = lire_bande(red_path, red_bande)
    arr = calc_msavi2(nir, red)
    return {
        'nom': 'MSAVI2',
        'array': arr,
        'image_b64': generer_visualisation(arr, 'MSAVI2 — Correction sol avancée', _CMAP_NDVI, -1, 1, 'MSAVI2'),
        'stats': statistiques(arr),
        'distribution': distribution_ndvi(arr),
        'vmin': -1, 'vmax': 1,
    }


def pipeline_nbr(nir_path, swir_path, nir_bande=1, swir_bande=1) -> dict:
    nir  = lire_bande(nir_path, nir_bande)
    swir = lire_bande(swir_path, swir_bande)
    arr  = calc_nbr(nir, swir)
    return {
        'nom': 'NBR',
        'array': arr,
        'image_b64': generer_visualisation(arr, 'NBR — Normalized Burn Ratio', _CMAP_FIRE, -1, 1, 'NBR'),
        'stats': statistiques(arr),
        'distribution': distribution_nbr(arr),
        'vmin': -1, 'vmax': 1,
    }


def pipeline_dnbr(pre_nir_path, pre_swir_path, post_nir_path, post_swir_path,
                   pre_nir_b=1, pre_swir_b=1, post_nir_b=1, post_swir_b=1) -> dict:
    nbr_pre  = calc_nbr(lire_bande(pre_nir_path, pre_nir_b),
                        lire_bande(pre_swir_path, pre_swir_b))
    nbr_post = calc_nbr(lire_bande(post_nir_path, post_nir_b),
                        lire_bande(post_swir_path, post_swir_b))
    arr = calc_dnbr(nbr_pre, nbr_post)
    return {
        'nom': 'dNBR',
        'array': arr,
        'image_b64': generer_visualisation(arr, 'dNBR — Sévérité de brûlure', _CMAP_FIRE, -0.5, 1.3, 'dNBR'),
        'stats': statistiques(arr),
        'distribution': distribution_nbr(arr),
        'vmin': -0.5, 'vmax': 1.3,
    }


def pipeline_bai(red_path, nir_path, red_bande=1, nir_bande=1) -> dict:
    red = lire_bande(red_path, red_bande)
    nir = lire_bande(nir_path, nir_bande)
    arr = calc_bai(red, nir)
    arr_clip   = np.where(np.isnan(arr), np.nan, np.clip(arr, 0, 50))
    return {
        'nom': 'BAI',
        'array': arr,
        'image_b64': generer_visualisation(arr_clip, 'BAI — Index Zone Brûlée', _CMAP_BAI, 0, 50, 'BAI'),
        'stats': statistiques(arr),
        'distribution': distribution_bai(arr),
        'vmin': 0, 'vmax': 50,
    }
