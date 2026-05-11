"""
Blueprint Atlas — Valorisation des résultats de thèse
Carte temporelle 2024-2050, comparaison avant/après, graphiques dynamiques,
requêtes spatiales, téléchargement des résultats.
"""

import io
import csv
import json
from datetime import datetime

from flask import render_template, jsonify, request, send_file
from flask_login import login_required

from app import db
from app.blueprints.atlas import atlas_bp
from app.models import ClasseCouverture
from app.models.atlas import ResultatAtlas


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers internes
# ══════════════════════════════════════════════════════════════════════════════

def _annees_liste():
    rows = (db.session.query(ResultatAtlas.annee)
            .distinct()
            .order_by(ResultatAtlas.annee)
            .all())
    return [r[0] for r in rows]


def _get_by_annee_scenario(annee, scenario='tendanciel'):
    rows = ResultatAtlas.query.filter_by(annee=annee, scenario=scenario).all()
    if not rows:
        rows = ResultatAtlas.query.filter_by(annee=annee).all()
    return rows


# ══════════════════════════════════════════════════════════════════════════════
#  Page principale
# ══════════════════════════════════════════════════════════════════════════════

@atlas_bp.route('/')
@login_required
def index():
    """Tableau de bord Atlas des résultats de thèse."""
    annees   = _annees_liste()
    classes  = (ClasseCouverture.query
                .filter_by(actif=True)
                .order_by(ClasseCouverture.ordre_affichage)
                .all())
    scenarios = [s[0] for s in
                 db.session.query(ResultatAtlas.scenario).distinct().all()]

    annee_obs_min = min((a for a in annees if a <= 2024), default=None)
    annee_obs_max = max((a for a in annees if a <= 2024), default=None)
    annee_proj_max = max(annees) if annees else 2050

    # ── KPI ──────────────────────────────────────────────────────────────────
    superficie_totale = 0
    pct_foret         = 0
    deforestation_ha  = 0

    if annee_obs_max:
        rows_fin = _get_by_annee_scenario(annee_obs_max, 'tendanciel')
        superficie_totale = sum(r.superficie_ha for r in rows_fin)
        foret_fin = sum(r.superficie_ha for r in rows_fin
                        if r.classe and r.classe.categorie == 'Forêt')
        pct_foret = round(foret_fin / superficie_totale * 100, 1) if superficie_totale else 0

    if annee_obs_min and annee_obs_max and annee_obs_min != annee_obs_max:
        rows_debut = _get_by_annee_scenario(annee_obs_min, 'tendanciel')
        foret_debut = sum(r.superficie_ha for r in rows_debut
                          if r.classe and r.classe.categorie == 'Forêt')
        foret_fin2  = sum(r.superficie_ha for r in _get_by_annee_scenario(annee_obs_max, 'tendanciel')
                          if r.classe and r.classe.categorie == 'Forêt')
        deforestation_ha = foret_debut - foret_fin2

    # Projection 2050 (forêt restante, scénario tendanciel)
    foret_2050 = 0
    if 2050 in annees:
        rows_2050 = _get_by_annee_scenario(2050, 'tendanciel')
        foret_2050 = sum(r.superficie_ha for r in rows_2050
                         if r.classe and r.classe.categorie == 'Forêt')

    return render_template(
        'atlas/index.html',
        title='Atlas des Résultats — VégéSuivi Pro',
        annees=annees,
        classes=classes,
        scenarios=scenarios,
        annee_obs_min=annee_obs_min,
        annee_obs_max=annee_obs_max,
        annee_proj_max=annee_proj_max,
        superficie_totale=round(superficie_totale),
        pct_foret=pct_foret,
        deforestation_ha=round(deforestation_ha),
        foret_2050=round(foret_2050),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  API JSON — données pour les composants JS
# ══════════════════════════════════════════════════════════════════════════════

@atlas_bp.route('/api/annees')
@login_required
def api_annees():
    """Liste des années disponibles par type (observées / projetées)."""
    obs  = [r[0] for r in db.session.query(ResultatAtlas.annee)
            .filter_by(type_donnee='observe')
            .distinct().order_by(ResultatAtlas.annee).all()]
    proj = [r[0] for r in db.session.query(ResultatAtlas.annee)
            .filter_by(type_donnee='projete')
            .distinct().order_by(ResultatAtlas.annee).all()]
    return jsonify({'observees': obs, 'projetees': proj,
                    'toutes': sorted(set(obs + proj))})


@atlas_bp.route('/api/statistiques')
@login_required
def api_statistiques():
    """Statistiques de couverture pour une année + scénario donnés."""
    annee    = request.args.get('annee', type=int)
    scenario = request.args.get('scenario', 'tendanciel')
    if not annee:
        return jsonify({'error': 'Paramètre annee requis'}), 400

    rows  = _get_by_annee_scenario(annee, scenario)
    total = sum(r.superficie_ha for r in rows)
    return jsonify({
        'annee':               annee,
        'scenario':            scenario,
        'superficie_totale_ha': round(total, 2),
        'type_donnee':         rows[0].type_donnee if rows else 'observe',
        'resultats':           [r.to_dict() for r in rows],
    })


@atlas_bp.route('/api/evolution')
@login_required
def api_evolution():
    """Série temporelle de l'évolution de chaque classe."""
    scenario  = request.args.get('scenario', 'tendanciel')
    annee_min = request.args.get('annee_min', 1986, type=int)
    annee_max = request.args.get('annee_max', 2050, type=int)

    rows = (ResultatAtlas.query
            .filter(ResultatAtlas.annee >= annee_min,
                    ResultatAtlas.annee <= annee_max,
                    ResultatAtlas.scenario == scenario)
            .order_by(ResultatAtlas.annee, ResultatAtlas.classe_id)
            .all())

    annees_set = sorted(set(r.annee for r in rows))
    types_par_annee = {r.annee: r.type_donnee for r in rows}

    classes_dict: dict = {}
    for r in rows:
        cid = r.classe_id
        if cid not in classes_dict:
            classes_dict[cid] = {
                'id':      cid,
                'label':   r.classe.label      if r.classe else f'Classe {cid}',
                'couleur': r.classe.couleur_hex if r.classe else '#888',
                'data':    {},
            }
        classes_dict[cid]['data'][r.annee] = r.superficie_ha

    return jsonify({
        'annees':   annees_set,
        'types':    types_par_annee,
        'classes':  list(classes_dict.values()),
        'scenario': scenario,
    })


@atlas_bp.route('/api/geojson/<int:annee>')
@login_required
def api_geojson(annee):
    """GeoJSON de la couverture végétale pour une année donnée."""
    scenario = request.args.get('scenario', 'tendanciel')
    rows = _get_by_annee_scenario(annee, scenario)

    features = []
    for r in rows:
        geom = None
        if r.geojson:
            try:
                geom = json.loads(r.geojson)
            except (json.JSONDecodeError, ValueError):
                geom = None
        if geom is None and r.latitude_centre and r.longitude_centre:
            geom = {
                'type': 'Point',
                'coordinates': [r.longitude_centre, r.latitude_centre],
            }
        if geom:
            features.append({
                'type':       'Feature',
                'geometry':   geom,
                'properties': r.to_dict(),
            })

    return jsonify({'type': 'FeatureCollection', 'features': features})


@atlas_bp.route('/api/comparaison')
@login_required
def api_comparaison():
    """Données de comparaison entre deux années."""
    annee1   = request.args.get('annee1',   type=int)
    annee2   = request.args.get('annee2',   type=int)
    scenario = request.args.get('scenario', 'tendanciel')

    if not annee1 or not annee2:
        return jsonify({'error': 'annee1 et annee2 sont requis'}), 400

    def get_map(annee):
        return {r.classe_id: r for r in _get_by_annee_scenario(annee, scenario)}

    data1  = get_map(annee1)
    data2  = get_map(annee2)
    classe = (ClasseCouverture.query
              .filter_by(actif=True)
              .order_by(ClasseCouverture.ordre_affichage)
              .all())

    comparaison = []
    for c in classe:
        r1 = data1.get(c.id)
        r2 = data2.get(c.id)
        s1 = r1.superficie_ha if r1 else 0.0
        s2 = r2.superficie_ha if r2 else 0.0
        variation = s2 - s1
        taux      = ((s2 - s1) / s1 * 100) if s1 > 0 else 0.0
        comparaison.append({
            'classe_id':        c.id,
            'classe_label':     c.label,
            'classe_couleur':   c.couleur_hex,
            'superficie_an1':   round(s1, 2),
            'superficie_an2':   round(s2, 2),
            'variation_ha':     round(variation, 2),
            'taux_variation':   round(taux, 2),
        })

    total1 = sum(d['superficie_an1'] for d in comparaison)
    total2 = sum(d['superficie_an2'] for d in comparaison)

    return jsonify({
        'annee1':      annee1,
        'annee2':      annee2,
        'scenario':    scenario,
        'total1':      round(total1, 2),
        'total2':      round(total2, 2),
        'comparaison': comparaison,
    })


@atlas_bp.route('/api/requete')
@login_required
def api_requete():
    """Requête filtrée sur les résultats (pseudo-requête spatiale)."""
    annee       = request.args.get('annee',       type=int)
    classe_id   = request.args.get('classe_id',   type=int)
    scenario    = request.args.get('scenario')
    type_donnee = request.args.get('type_donnee')
    sup_min     = request.args.get('sup_min',     type=float)
    sup_max     = request.args.get('sup_max',     type=float)

    q = ResultatAtlas.query
    if annee:
        q = q.filter_by(annee=annee)
    if classe_id:
        q = q.filter_by(classe_id=classe_id)
    if scenario:
        q = q.filter_by(scenario=scenario)
    if type_donnee:
        q = q.filter_by(type_donnee=type_donnee)
    if sup_min is not None:
        q = q.filter(ResultatAtlas.superficie_ha >= sup_min)
    if sup_max is not None:
        q = q.filter(ResultatAtlas.superficie_ha <= sup_max)

    rows = q.order_by(ResultatAtlas.annee, ResultatAtlas.classe_id).limit(500).all()
    return jsonify({'count': len(rows), 'resultats': [r.to_dict() for r in rows]})


# ══════════════════════════════════════════════════════════════════════════════
#  Téléchargements
# ══════════════════════════════════════════════════════════════════════════════

@atlas_bp.route('/telecharger/csv')
@login_required
def telecharger_csv():
    """Export CSV de tous les résultats (ou filtrés par année / scénario)."""
    annee    = request.args.get('annee',    type=int)
    scenario = request.args.get('scenario', 'tendanciel')

    q = ResultatAtlas.query
    if annee:
        q = q.filter_by(annee=annee)
    if scenario:
        q = q.filter_by(scenario=scenario)
    rows = q.order_by(ResultatAtlas.annee, ResultatAtlas.classe_id).all()

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['Année', 'Classe', 'Zone', 'Superficie (ha)',
                'Superficie (%)', 'Type de données', 'Scénario'])
    for r in rows:
        w.writerow([
            r.annee,
            r.classe.label if r.classe else '',
            r.zone,
            r.superficie_ha,
            r.superficie_pct,
            r.type_donnee,
            r.scenario,
        ])
    buf.seek(0)
    fname = f'atlas_{scenario}_{datetime.now().strftime("%Y%m%d")}.csv'
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=fname,
    )


@atlas_bp.route('/telecharger/geojson/<int:annee>')
@login_required
def telecharger_geojson(annee):
    """Export GeoJSON pour une année et un scénario."""
    scenario = request.args.get('scenario', 'tendanciel')
    rows     = _get_by_annee_scenario(annee, scenario)

    features = []
    for r in rows:
        geom = None
        if r.geojson:
            try:
                geom = json.loads(r.geojson)
            except (json.JSONDecodeError, ValueError):
                geom = None
        if geom is None and r.latitude_centre and r.longitude_centre:
            geom = {
                'type': 'Point',
                'coordinates': [r.longitude_centre, r.latitude_centre],
            }
        if geom:
            features.append({
                'type':       'Feature',
                'geometry':   geom,
                'properties': r.to_dict(),
            })

    fc    = json.dumps({'type': 'FeatureCollection', 'features': features},
                       ensure_ascii=False, indent=2)
    fname = f'atlas_{annee}_{scenario}.geojson'
    return send_file(
        io.BytesIO(fc.encode('utf-8')),
        mimetype='application/geo+json',
        as_attachment=True,
        download_name=fname,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Seed de démonstration (admin uniquement)
# ══════════════════════════════════════════════════════════════════════════════

@atlas_bp.route('/admin/seed-demo', methods=['POST'])
@login_required
def seed_demo():
    """Peuple la base avec les données de démonstration de thèse."""
    from flask_login import current_user
    if current_user.role not in ('admin', 'superviseur'):
        return jsonify({'error': 'Accès refusé'}), 403

    from app.utils.seed_atlas import seed_atlas as _seed_atlas
    try:
        nb = _seed_atlas()
        return jsonify({'ok': True, 'message': f'{nb} enregistrements insérés.'})
    except (ValueError, RuntimeError) as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'message': str(exc)}), 500
