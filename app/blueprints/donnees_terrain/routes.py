"""
Blueprint Données Terrain — Routes
===================================
GET  /donnees-terrain/           → liste des couches importées
GET  /donnees-terrain/importer   → formulaire d'import
POST /donnees-terrain/importer   → traitement upload (ZIP ou multi-fichiers)
GET  /donnees-terrain/<id>       → détail + carte Leaflet
GET  /donnees-terrain/<id>/geojson → GeoJSON complet (retéléchargement)
POST /donnees-terrain/<id>/supprimer → suppression
"""

import os
import json
import shutil
import uuid as _uuid
from datetime import datetime, date

from flask import (render_template, redirect, url_for, flash,
                   request, jsonify, current_app, send_file, abort)
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from app.blueprints.donnees_terrain import donnees_bp
from app.models.donnees_shp import CoucheDonneesTerrain
from app.utils import shp_reader as sr
from app.utils.helpers import generate_reference


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _dossier_upload(uid: str) -> str:
    base = os.path.join(current_app.config['UPLOAD_FOLDER'], 'shp', uid)
    os.makedirs(base, exist_ok=True)
    return base


def _taille_dossier(dossier: str) -> int:
    total = 0
    try:
        for root, _, files in os.walk(dossier):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
    except Exception:
        pass
    return total


# ══════════════════════════════════════════════════════════════════════════════
#  Liste
# ══════════════════════════════════════════════════════════════════════════════

@donnees_bp.route('/')
@login_required
def index():
    type_filtre = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)

    query = CoucheDonneesTerrain.query.filter_by(statut='valide').order_by(
        desc(CoucheDonneesTerrain.date_upload))

    if type_filtre:
        query = query.filter_by(type_geometrie=type_filtre)

    couches = query.paginate(page=page, per_page=20, error_out=False)

    # Types disponibles pour le filtre
    types_disponibles = db.session.query(
        CoucheDonneesTerrain.type_geometrie
    ).filter(
        CoucheDonneesTerrain.statut == 'valide',
        CoucheDonneesTerrain.type_geometrie.isnot(None)
    ).distinct().order_by(CoucheDonneesTerrain.type_geometrie).all()
    types_disponibles = [t[0] for t in types_disponibles]

    return render_template('donnees_terrain/index.html',
                           title='Données terrain',
                           couches=couches,
                           type_filtre=type_filtre,
                           types_disponibles=types_disponibles)


# ══════════════════════════════════════════════════════════════════════════════
#  Import
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  Import
# ══════════════════════════════════════════════════════════════════════════════

@donnees_bp.route('/importer/chunk', methods=['POST'])
@login_required
def importer_chunk():
    """
    Reçoit un fragment (chunk) d'un fichier en upload.
    Paramètres FormData :
      - upload_id  : identifiant unique de la session d'upload (uuid hex)
      - chunk_index: numéro du fragment (0-based)
      - total_chunks: nombre total de fragments
      - filename   : nom du fichier original
      - chunk      : blob binaire du fragment
    """
    upload_id    = request.form.get('upload_id', '').strip()
    chunk_index  = int(request.form.get('chunk_index', 0))
    total_chunks = int(request.form.get('total_chunks', 1))
    filename     = request.form.get('filename', 'upload.bin')
    chunk_file   = request.files.get('chunk')

    if not upload_id or not chunk_file:
        return jsonify({'ok': False, 'error': 'Paramètres manquants'}), 400

    # Dossier temporaire dédié à cet upload
    tmp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'shp_chunks', upload_id)
    os.makedirs(tmp_dir, exist_ok=True)

    # Sauvegarder le fragment
    chunk_path = os.path.join(tmp_dir, f'chunk_{chunk_index:05d}')
    chunk_file.save(chunk_path)

    return jsonify({
        'ok': True,
        'chunk_index': chunk_index,
        'total_chunks': total_chunks,
        'done': (chunk_index + 1) >= total_chunks
    })


@donnees_bp.route('/importer/finaliser', methods=['POST'])
@login_required
def importer_finaliser():
    """
    Appelé après le dernier chunk : assemble le fichier, traite le SHP,
    enregistre en base et retourne l'URL de détail.
    """
    data      = request.get_json(force=True) or {}
    upload_id = data.get('upload_id', '').strip()
    filename  = data.get('filename', 'upload.bin')
    nom_saisi = data.get('nom', '').strip()
    description = data.get('description', '').strip()
    source    = data.get('source', '').strip()
    date_acq_str = data.get('date_acquisition', '').strip()

    if not upload_id:
        return jsonify({'ok': False, 'error': 'upload_id manquant'}), 400

    tmp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'shp_chunks', upload_id)
    if not os.path.isdir(tmp_dir):
        return jsonify({'ok': False, 'error': 'Session upload introuvable'}), 404

    uid     = _uuid.uuid4().hex
    dossier = _dossier_upload(uid)

    try:
        # 1. Assembler les chunks en fichier complet
        chunks = sorted(
            [f for f in os.listdir(tmp_dir) if f.startswith('chunk_')],
            key=lambda x: int(x.split('_')[1])
        )
        if not chunks:
            raise ValueError('Aucun fragment reçu.')

        assembled_path = os.path.join(tmp_dir, filename)
        with open(assembled_path, 'wb') as out:
            for ch in chunks:
                with open(os.path.join(tmp_dir, ch), 'rb') as inp:
                    shutil.copyfileobj(inp, out)

        # 2. Extraire si ZIP ou copier directement
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.zip':
            sr.extraire_zip(assembled_path, dossier)
        else:
            shutil.copy(assembled_path, os.path.join(dossier, filename))

        # 3. Nettoyer dossier temporaire
        shutil.rmtree(tmp_dir, ignore_errors=True)

        # 4. Valider et analyser
        ok, msg = sr.valider_bundle(dossier)
        if not ok:
            raise ValueError(msg)

        chemin_shp = sr.trouver_shp(dossier)
        meta       = sr.analyser_shp(chemin_shp)
        geojson_str = sr.shp_to_geojson_json(chemin_shp, max_features=500)

        # 5. Persister
        ref = generate_reference('CTR')
        date_acq = None
        if date_acq_str:
            try:
                date_acq = datetime.strptime(date_acq_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        couche = CoucheDonneesTerrain(
            reference=ref,
            nom=nom_saisi or meta['nom_fichier'],
            description=description or None,
            source=source or None,
            date_acquisition=date_acq,
            type_geometrie=meta['type_geometrie'],
            icone_geometrie=meta['icone_geometrie'],
            nombre_entites=meta['nombre_entites'],
            bbox_json=json.dumps(meta['bbox']) if meta['bbox'] else None,
            attributs_json=json.dumps(meta['attributs']),
            srid=meta['srid'],
            geojson_apercu=geojson_str,
            dossier_shp=dossier,
            nom_fichier_shp=os.path.basename(chemin_shp),
            taille_octets=_taille_dossier(dossier),
            uploaded_by=current_user.id,
            statut='valide',
        )
        db.session.add(couche)
        db.session.commit()

        return jsonify({
            'ok': True,
            'message': (f'Couche « {couche.nom} » importée — '
                        f'{couche.nombre_entites:,} entités ({meta["type_geometrie"]}).'),
            'redirect': url_for('donnees_terrain.detail', id=couche.id)
        })

    except Exception as e:
        shutil.rmtree(dossier, ignore_errors=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        current_app.logger.warning(f'Finalisation SHP échouée: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 422


@donnees_bp.route('/importer', methods=['GET', 'POST'])
@login_required
def importer():
    if request.method == 'GET':
        return render_template('donnees_terrain/importer.html',
                               title='Importer des données terrain')

    # ── Traitement POST ────────────────────────────────────────────────────────
    uid = _uuid.uuid4().hex
    dossier = _dossier_upload(uid)
    erreur = None
    mode = request.form.get('mode_upload', 'zip')  # 'zip' ou 'fichiers'

    try:
        # 1. Réception des fichiers
        if mode == 'zip':
            zip_file = request.files.get('fichier_zip')
            if not zip_file or zip_file.filename == '':
                raise ValueError('Aucun fichier ZIP sélectionné.')
            ext = os.path.splitext(zip_file.filename)[1].lower()
            if ext != '.zip':
                raise ValueError('Le fichier doit être un archive .zip.')

            chemin_zip = os.path.join(dossier, 'upload.zip')
            zip_file.save(chemin_zip)
            sr.extraire_zip(chemin_zip, dossier)
            os.remove(chemin_zip)  # Nettoyage du ZIP

        else:  # multi-fichiers
            fichiers = request.files.getlist('fichiers_shp')
            if not fichiers or all(f.filename == '' for f in fichiers):
                raise ValueError('Aucun fichier sélectionné.')
            sr.sauver_fichiers_multiples(fichiers, dossier)

        # 2. Valider le bundle
        ok, msg = sr.valider_bundle(dossier)
        if not ok:
            raise ValueError(msg)

        # 3. Trouver le .shp
        chemin_shp = sr.trouver_shp(dossier)

        # 4. Analyser
        meta = sr.analyser_shp(chemin_shp)

        # 5. Convertir en GeoJSON (aperçu)
        geojson_str = sr.shp_to_geojson_json(chemin_shp, max_features=500)

        # 6. Sauvegarder en DB
        ref = generate_reference('CTR')
        nom_saisi = request.form.get('nom', '').strip() or meta['nom_fichier']
        date_acq_str = request.form.get('date_acquisition', '').strip()
        date_acq = None
        if date_acq_str:
            try:
                date_acq = datetime.strptime(date_acq_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        couche = CoucheDonneesTerrain(
            reference=ref,
            nom=nom_saisi,
            description=request.form.get('description', '').strip() or None,
            source=request.form.get('source', '').strip() or None,
            date_acquisition=date_acq,
            type_geometrie=meta['type_geometrie'],
            icone_geometrie=meta['icone_geometrie'],
            nombre_entites=meta['nombre_entites'],
            bbox_json=json.dumps(meta['bbox']) if meta['bbox'] else None,
            attributs_json=json.dumps(meta['attributs']),
            srid=meta['srid'],
            geojson_apercu=geojson_str,
            dossier_shp=dossier,
            nom_fichier_shp=os.path.basename(chemin_shp),
            taille_octets=_taille_dossier(dossier),
            uploaded_by=current_user.id,
            statut='valide',
        )
        db.session.add(couche)
        db.session.commit()

        flash(f'Couche « {couche.nom} » importée avec succès — '
              f'{couche.nombre_entites:,} entités ({meta["type_geometrie"]}).', 'success')
        return redirect(url_for('donnees_terrain.detail', id=couche.id))

    except Exception as e:
        # Nettoyage du dossier en cas d'erreur
        try:
            shutil.rmtree(dossier, ignore_errors=True)
        except Exception:
            pass
        erreur = str(e)
        current_app.logger.warning(f'Import SHP échoué: {e}')

    return render_template('donnees_terrain/importer.html',
                           title='Importer des données terrain',
                           erreur=erreur)


# ══════════════════════════════════════════════════════════════════════════════
#  Détail
# ══════════════════════════════════════════════════════════════════════════════

@donnees_bp.route('/<int:id>')
@login_required
def detail(id):
    couche = db.get_or_404(CoucheDonneesTerrain, id)
    return render_template('donnees_terrain/detail.html',
                           title=f'Couche {couche.nom}',
                           couche=couche)


# ══════════════════════════════════════════════════════════════════════════════
#  GeoJSON — aperçu (pour Leaflet)
# ══════════════════════════════════════════════════════════════════════════════

@donnees_bp.route('/<int:id>/geojson')
@login_required
def geojson(id):
    couche = db.get_or_404(CoucheDonneesTerrain, id)

    # Toujours lire depuis le fichier SHP sur disque → aucune limite d'entités
    if couche.chemin_shp and os.path.exists(couche.chemin_shp):
        data = sr.shp_to_geojson(couche.chemin_shp)  # max_features=None → tout
        return jsonify(data)

    # Fallback : aperçu stocké en base (si fichier supprimé après redémarrage)
    if couche.geojson_apercu:
        return current_app.response_class(
            couche.geojson_apercu,
            content_type='application/json; charset=utf-8'
        )
    return jsonify({'type': 'FeatureCollection', 'features': []})


# ══════════════════════════════════════════════════════════════════════════════
#  Télécharger ZIP
# ══════════════════════════════════════════════════════════════════════════════

@donnees_bp.route('/<int:id>/telecharger')
@login_required
def telecharger(id):
    couche = db.get_or_404(CoucheDonneesTerrain, id)

    if not couche.dossier_shp or not os.path.isdir(couche.dossier_shp):
        flash('Fichiers source introuvables sur le serveur.', 'warning')
        return redirect(url_for('donnees_terrain.detail', id=id))

    import tempfile, zipfile as zf
    nom_zip = f"{couche.reference}_{couche.nom[:30].replace(' ','_')}.zip"

    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        chemin_tmp = tmp.name

    with zf.ZipFile(chemin_tmp, 'w', compression=zf.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(couche.dossier_shp):
            for f in files:
                fullpath = os.path.join(root, f)
                z.write(fullpath, arcname=f)

    return send_file(chemin_tmp, as_attachment=True,
                     download_name=nom_zip,
                     mimetype='application/zip')


# ══════════════════════════════════════════════════════════════════════════════
#  Suppression
# ══════════════════════════════════════════════════════════════════════════════

@donnees_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer(id):
    couche = db.get_or_404(CoucheDonneesTerrain, id)

    # Supprimer les fichiers physiques
    if couche.dossier_shp and os.path.isdir(couche.dossier_shp):
        shutil.rmtree(couche.dossier_shp, ignore_errors=True)

    nom = couche.nom
    db.session.delete(couche)
    db.session.commit()

    flash(f'Couche « {nom} » supprimée.', 'success')
    return redirect(url_for('donnees_terrain.index'))
