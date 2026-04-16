"""
Blueprint Indices — Calculateur automatique d'indices spectraux

Mode 1 : Saisie manuelle de valeurs de réflectance ponctuelles
Mode 2 : Upload d'images satellites GeoTIFF → calcul raster pixel par pixel
         + visualisation colorimétrique + statistiques

Végétation : NDVI, SAVI, EVI, MSAVI2
Feux        : NBR, dNBR, BAI
"""

import os
import shutil
import uuid

from flask import render_template, request, current_app, jsonify
from flask_login import login_required

from app.blueprints.indices import indices_bp
from app.utils import indices as idx


# ══════════════════════════════════════════════════════════════════════════════
#  Store in-memory des TIF assemblés (token → chemin fichier)
# ══════════════════════════════════════════════════════════════════════════════

_TIF_TOKENS: dict[str, str] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers communs
# ══════════════════════════════════════════════════════════════════════════════

def _sauver_tif(fichier_upload) -> str | None:
    """Sauvegarde un fichier TIF uploadé dans uploads/indices/. Retourne le chemin ou None."""
    if not fichier_upload or fichier_upload.filename == '':
        return None
    ext = os.path.splitext(fichier_upload.filename)[1].lower()
    if ext not in ('.tif', '.tiff'):
        return None
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'indices')
    os.makedirs(upload_dir, exist_ok=True)
    nom_securise = f"{uuid.uuid4().hex}{ext}"
    chemin = os.path.join(upload_dir, nom_securise)
    fichier_upload.save(chemin)
    return chemin


def _get_tif(key: str) -> str | None:
    """Résout un TIF depuis un token (chunked) ou un upload direct."""
    token = request.form.get(f'tif_token_{key}')
    if token:
        path = _TIF_TOKENS.pop(token, None)
        return path if path and os.path.exists(path) else None
    return _sauver_tif(request.files.get(key))


# ══════════════════════════════════════════════════════════════════════════════
#  Upload TIF par fragments (chunked — contourne MAX_CONTENT_LENGTH)
# ══════════════════════════════════════════════════════════════════════════════

@indices_bp.route('/chunk-tif', methods=['POST'])
@login_required
def chunk_tif():
    """Reçoit un fragment de TIF et le sauvegarde dans un dossier temporaire."""
    upload_id   = request.form.get('upload_id', '')
    file_key    = request.form.get('file_key', '')
    chunk_index = request.form.get('chunk_index', '0')
    chunk_file  = request.files.get('chunk_data')

    if not upload_id or not file_key or not chunk_file:
        return jsonify({'ok': False, 'message': 'Paramètres manquants'}), 400

    chunk_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'tif_chunks', upload_id, file_key
    )
    os.makedirs(chunk_dir, exist_ok=True)
    chunk_file.save(os.path.join(chunk_dir, f'chunk_{int(chunk_index):05d}'))
    return jsonify({'ok': True})


@indices_bp.route('/tif-finaliser', methods=['POST'])
@login_required
def tif_finaliser():
    """Assemble les fragments d'un TIF, stocke le chemin sous un token, le retourne."""
    data      = request.get_json(force=True)
    upload_id = data.get('upload_id', '')
    file_key  = data.get('file_key', '')
    extension = data.get('extension', '.tif')

    chunk_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'tif_chunks', upload_id, file_key
    )
    if not os.path.isdir(chunk_dir):
        return jsonify({'ok': False, 'message': 'Fragments introuvables'}), 400

    out_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'indices')
    os.makedirs(out_dir, exist_ok=True)
    chemin_final = os.path.join(out_dir, f"{uuid.uuid4().hex}{extension}")

    chunks = sorted(os.listdir(chunk_dir))
    with open(chemin_final, 'wb') as out_f:
        for c in chunks:
            with open(os.path.join(chunk_dir, c), 'rb') as cf:
                out_f.write(cf.read())

    shutil.rmtree(chunk_dir, ignore_errors=True)

    token = uuid.uuid4().hex
    _TIF_TOKENS[token] = chemin_final
    return jsonify({'ok': True, 'token': token})



# ══════════════════════════════════════════════════════════════════════════════
#  Végétation  NDVI / SAVI / EVI / MSAVI2
# ══════════════════════════════════════════════════════════════════════════════

@indices_bp.route('/vegetation', methods=['GET', 'POST'])
@login_required
def vegetation():
    resultats      = None   # mode manuel : liste scalaires
    raster_results = None   # mode raster : liste (image, stats, distrib)
    valeurs        = {}
    mode           = 'manual'
    erreur         = None

    if request.method == 'POST':
        mode = request.form.get('mode', 'manual')

        # ── Mode MANUEL ────────────────────────────────────────────────────
        if mode == 'manual':
            try:
                nir  = float(request.form.get('nir', 0))
                red  = float(request.form.get('red', 0))
                blue = float(request.form.get('blue', 0))
                L    = float(request.form.get('L_savi', 0.5))
                valeurs = {'nir': nir, 'red': red, 'blue': blue, 'L_savi': L}

                v_ndvi   = idx.ndvi(nir, red)
                v_savi   = idx.savi(nir, red, L)
                v_evi    = idx.evi(nir, red, blue)
                v_msavi2 = idx.msavi2(nir, red)

                resultats = [
                    {
                        'nom': 'NDVI',
                        'nom_long': 'Normalized Difference Vegetation Index',
                        'formule': '(NIR − Red) / (NIR + Red)',
                        'valeur': v_ndvi,
                        'plage': '−1.0 → +1.0',
                        'usage': 'Indicateur général de l\'état de la végétation',
                        'interpretation': idx.interprete_ndvi(v_ndvi),
                        'bandes': 'NIR, Red',
                        'badge_color': 'success',
                    },
                    {
                        'nom': 'SAVI',
                        'nom_long': 'Soil Adjusted Vegetation Index',
                        'formule': '((NIR − Red) / (NIR + Red + L)) × (1 + L)',
                        'valeur': v_savi,
                        'plage': '~−1.5 → +1.5',
                        'usage': 'Correction de l\'effet sol — indispensable en zone sahélienne',
                        'interpretation': idx.interprete_savi(v_savi),
                        'bandes': 'NIR, Red  (L = facteur sol)',
                        'badge_color': 'warning',
                        'sahel': True,
                    },
                    {
                        'nom': 'EVI',
                        'nom_long': 'Enhanced Vegetation Index',
                        'formule': '2.5 × (NIR − Red) / (NIR + 6·Red − 7.5·Blue + 1)',
                        'valeur': v_evi,
                        'plage': '0 → ~0.8 sur végétation',
                        'usage': 'Zones à forte biomasse — réduit la saturation atmosphérique',
                        'interpretation': idx.interprete_evi(v_evi),
                        'bandes': 'NIR, Red, Blue',
                        'badge_color': 'info',
                    },
                    {
                        'nom': 'MSAVI2',
                        'nom_long': 'Modified Soil Adjusted Vegetation Index 2',
                        'formule': '(2·NIR + 1 − √((2·NIR+1)² − 8·(NIR−Red))) / 2',
                        'valeur': v_msavi2,
                        'plage': '~−1.0 → +1.0',
                        'usage': 'Correction avancée effet sol, sans facteur L empirique',
                        'interpretation': idx.interprete_msavi2(v_msavi2),
                        'bandes': 'NIR, Red',
                        'badge_color': 'primary',
                        'sahel': True,
                    },
                ]
            except (ValueError, TypeError) as e:
                erreur = f'Valeurs invalides : {e}'

        # ── Mode RASTER ────────────────────────────────────────────────────
        else:
            from app.utils import raster_indices as ri
            try:
                L      = float(request.form.get('L_savi', 0.5))
                nir_b  = int(request.form.get('nir_bande',  1))
                red_b  = int(request.form.get('red_bande',  1))
                blue_b = int(request.form.get('blue_bande', 1))

                nir_tif  = _get_tif('nir_tif')
                red_tif  = _get_tif('red_tif')
                blue_tif = _get_tif('blue_tif')

                if not nir_tif or not red_tif:
                    raise ValueError('Les bandes NIR et Red sont obligatoires.')

                indices_demandes = request.form.getlist('indices_vegetation')
                if not indices_demandes:
                    indices_demandes = ['NDVI', 'SAVI']

                raster_results = []

                if 'NDVI' in indices_demandes:
                    raster_results.append(ri.pipeline_ndvi(nir_tif, red_tif, nir_b, red_b))

                if 'SAVI' in indices_demandes:
                    raster_results.append(ri.pipeline_savi(nir_tif, red_tif, nir_b, red_b, L))

                if 'MSAVI2' in indices_demandes:
                    raster_results.append(ri.pipeline_msavi2(nir_tif, red_tif, nir_b, red_b))

                if 'EVI' in indices_demandes:
                    if not blue_tif:
                        raise ValueError('La bande Blue est requise pour le calcul EVI.')
                    raster_results.append(ri.pipeline_evi(nir_tif, red_tif, blue_tif, nir_b, red_b, blue_b))

            except Exception as e:
                erreur = str(e)
                raster_results = None

    return render_template(
        'indices/vegetation.html',
        title='Indices de végétation',
        resultats=resultats,
        raster_results=raster_results,
        valeurs=valeurs,
        mode=mode,
        erreur=erreur,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Feux  NBR / dNBR / BAI
# ══════════════════════════════════════════════════════════════════════════════

@indices_bp.route('/feux', methods=['GET', 'POST'])
@login_required
def feux():
    resultats      = None
    raster_results = None
    valeurs        = {}
    mode           = 'manual'
    erreur         = None

    if request.method == 'POST':
        mode = request.form.get('mode', 'manual')

        # ── Mode MANUEL ────────────────────────────────────────────────────
        if mode == 'manual':
            try:
                nir      = float(request.form.get('nir', 0))
                swir     = float(request.form.get('swir', 0))
                red      = float(request.form.get('red', 0))
                nbr_pre  = request.form.get('nbr_pre', '').strip()
                nbr_post = request.form.get('nbr_post', '').strip()

                valeurs = {'nir': nir, 'swir': swir, 'red': red,
                           'nbr_pre': nbr_pre, 'nbr_post': nbr_post}

                v_nbr = idx.nbr(nir, swir)
                v_bai = idx.bai(red, nir)

                v_dnbr    = None
                dnbr_info = None
                if nbr_pre and nbr_post:
                    v_dnbr    = idx.dnbr(float(nbr_pre), float(nbr_post))
                    dnbr_info = idx.interprete_dnbr(v_dnbr)
                elif nbr_post and v_nbr is not None:
                    v_dnbr    = idx.dnbr(v_nbr, float(nbr_post))
                    dnbr_info = idx.interprete_dnbr(v_dnbr)

                resultats = [
                    {
                        'nom': 'NBR',
                        'nom_long': 'Normalized Burn Ratio',
                        'formule': '(NIR − SWIR) / (NIR + SWIR)',
                        'valeur': v_nbr,
                        'plage': '−1.0 → +1.0',
                        'usage': 'Détection des zones brûlées — valeurs basses = zone brûlée',
                        'interpretation': idx.interprete_nbr(v_nbr),
                        'bandes': 'NIR, SWIR (~2.2 µm)',
                        'badge_color': 'warning',
                    },
                    {
                        'nom': 'dNBR',
                        'nom_long': 'Delta NBR — Sévérité de brûlure',
                        'formule': 'NBR_avant − NBR_après',
                        'valeur': v_dnbr,
                        'plage': '−2.0 → +2.0',
                        'usage': 'Mesure la sévérité selon la classification USGS',
                        'interpretation': dnbr_info or {},
                        'bandes': 'NBR pré-feu & post-feu',
                        'badge_color': 'danger',
                        'note': 'Laissez NBR pré-feu vide pour utiliser le NBR calculé comme référence.',
                    },
                    {
                        'nom': 'BAI',
                        'nom_long': 'Burned Area Index',
                        'formule': '1 / ((0.1 − Red)² + (0.06 − NIR)²)',
                        'valeur': v_bai,
                        'plage': '0 → ∞  (élevé = brûlé)',
                        'usage': 'Détection de précision des zones brûlées, robuste en post-incendie',
                        'interpretation': idx.interprete_bai(v_bai),
                        'bandes': 'Red, NIR',
                        'badge_color': 'danger',
                    },
                ]
            except (ValueError, TypeError) as e:
                erreur = f'Valeurs invalides : {e}'

        # ── Mode RASTER ────────────────────────────────────────────────────
        else:
            from app.utils import raster_indices as ri
            try:
                nir_b  = int(request.form.get('nir_bande',  1))
                swir_b = int(request.form.get('swir_bande', 1))
                red_b  = int(request.form.get('red_bande',  1))

                nir_tif  = _get_tif('nir_tif')
                swir_tif = _get_tif('swir_tif')
                red_tif  = _get_tif('red_tif')

                pre_nir_tif   = _get_tif('pre_nir_tif')
                pre_swir_tif  = _get_tif('pre_swir_tif')
                post_nir_tif  = _get_tif('post_nir_tif')
                post_swir_tif = _get_tif('post_swir_tif')

                if not nir_tif or not swir_tif:
                    raise ValueError('Les bandes NIR et SWIR sont obligatoires.')

                indices_demandes = request.form.getlist('indices_feux')
                if not indices_demandes:
                    indices_demandes = ['NBR', 'BAI']

                raster_results = []

                if 'NBR' in indices_demandes:
                    raster_results.append(ri.pipeline_nbr(nir_tif, swir_tif, nir_b, swir_b))

                if 'BAI' in indices_demandes:
                    if not red_tif:
                        raise ValueError('La bande Red est requise pour le BAI.')
                    raster_results.append(ri.pipeline_bai(red_tif, nir_tif, red_b, nir_b))

                if 'dNBR' in indices_demandes:
                    pre_nir_b  = int(request.form.get('pre_nir_bande',  1))
                    pre_swir_b = int(request.form.get('pre_swir_bande', 1))
                    post_nir_b  = int(request.form.get('post_nir_bande',  1))
                    post_swir_b = int(request.form.get('post_swir_bande', 1))
                    if pre_nir_tif and pre_swir_tif and post_nir_tif and post_swir_tif:
                        raster_results.append(ri.pipeline_dnbr(
                            pre_nir_tif, pre_swir_tif,
                            post_nir_tif, post_swir_tif,
                            pre_nir_b, pre_swir_b,
                            post_nir_b, post_swir_b,
                        ))
                    else:
                        raise ValueError(
                            'Le dNBR nécessite 4 images : NIR pré-feu, SWIR pré-feu, '
                            'NIR post-feu, SWIR post-feu.'
                        )

            except Exception as e:
                erreur = str(e)
                raster_results = None

    return render_template(
        'indices/feux.html',
        title='Indices feux de brousse',
        resultats=resultats,
        raster_results=raster_results,
        valeurs=valeurs,
        mode=mode,
        erreur=erreur,
    )
