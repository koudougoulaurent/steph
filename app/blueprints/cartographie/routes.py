"""
Blueprint Cartographie - Cartes interactives et couches SIG
"""

from flask import render_template, jsonify, request
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.blueprints.cartographie import carto_bp
from app.models import (
    Couverture, FeuxBrousse, SiteVulnerable,
    IndicateurBraconnage, ObservationTerrain, ClasseCouverture
)


@carto_bp.route('/')
@login_required
def index():
    """Carte principale multi-couches"""
    classes = ClasseCouverture.query.filter_by(actif=True).order_by(
        ClasseCouverture.ordre_affichage).all()
    annees = db.session.query(
        Couverture.annee).distinct().order_by(Couverture.annee).all()
    annees = [a[0] for a in annees]

    return render_template('cartographie/index.html',
                           title='Cartographie - VégéSuivi Pro',
                           classes=classes,
                           annees=annees)


@carto_bp.route('/api/couverture/<int:annee>')
@login_required
def api_couverture_annee(annee):
    """GeoJSON de la couverture végétale pour une année donnée"""
    couvertures = Couverture.query.filter_by(annee=annee).all()
    features = []
    for c in couvertures:
        if c.latitude_centre and c.longitude_centre:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [c.longitude_centre, c.latitude_centre]
                },
                'properties': c.to_dict()
            })
    return jsonify({'type': 'FeatureCollection', 'features': features})


@carto_bp.route('/api/feux')
@login_required
def api_feux():
    """GeoJSON de tous les feux de brousse (filtrables par année)"""
    annee = request.args.get('annee', type=int)
    query = FeuxBrousse.query
    if annee:
        from datetime import date
        query = query.filter(
            func.extract('year', FeuxBrousse.date_debut) == annee
        )
    feux = query.all()
    features = []
    for f in feux:
        if f.latitude and f.longitude:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [f.longitude, f.latitude]
                },
                'properties': f.to_dict()
            })
    return jsonify({'type': 'FeatureCollection', 'features': features})


@carto_bp.route('/api/sites-vulnerables')
@login_required
def api_sites_vulnerables():
    """GeoJSON des sites vulnérables"""
    niveau = request.args.get('niveau')
    query = SiteVulnerable.query.filter_by(statut='actif')
    if niveau:
        query = query.filter_by(niveau_vulnerabilite=niveau)
    sites = query.all()
    features = []
    for s in sites:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [s.longitude, s.latitude]
            },
            'properties': s.to_dict()
        })
    return jsonify({'type': 'FeatureCollection', 'features': features})


@carto_bp.route('/api/braconnage')
@login_required
def api_braconnage():
    """GeoJSON des indicateurs de braconnage"""
    annee = request.args.get('annee', type=int)
    query = IndicateurBraconnage.query
    if annee:
        from datetime import date
        query = query.filter(
            func.extract('year', IndicateurBraconnage.date_constat) == annee
        )
    indicateurs = query.all()
    features = []
    for b in indicateurs:
        if b.latitude and b.longitude:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [b.longitude, b.latitude]
                },
                'properties': b.to_dict()
            })
    return jsonify({'type': 'FeatureCollection', 'features': features})


@carto_bp.route('/api/observations')
@login_required
def api_observations():
    """GeoJSON des observations terrain récentes"""
    limit = request.args.get('limit', 200, type=int)
    obs = ObservationTerrain.query.order_by(
        ObservationTerrain.date_observation.desc()).limit(limit).all()
    features = []
    for o in obs:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [o.longitude, o.latitude]
            },
            'properties': o.to_dict()
        })
    return jsonify({'type': 'FeatureCollection', 'features': features})


@carto_bp.route('/dynamique')
@login_required
def dynamique():
    """Vue comparaison temporelle - évolution 1990-2020"""
    annees = db.session.query(
        Couverture.annee).distinct().order_by(Couverture.annee).all()
    annees = [a[0] for a in annees]
    return render_template('cartographie/dynamique.html',
                           title='Dynamique d\'occupation des terres',
                           annees=annees)
