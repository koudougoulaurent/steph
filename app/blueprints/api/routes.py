"""
Blueprint API REST v1 - Endpoints JSON pour usage externe et exports
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, datetime

from app import db
from app.blueprints.api import api_bp
from app.models import (
    Couverture, FeuxBrousse, SiteVulnerable,
    IndicateurBraconnage, ObservationTerrain, ClasseCouverture,
    CampagneCollecte, Rapport
)


@api_bp.route('/status')
def status():
    return jsonify({
        'status': 'ok',
        'app': 'VégéSuivi Pro',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@api_bp.route('/kpis')
@login_required
def kpis():
    """KPIs temps réel pour le dashboard — rafraîchissement automatique"""
    today = date.today()
    debut_annee = today.replace(month=1, day=1)
    debut_mois = today.replace(day=1)

    feux_annee = FeuxBrousse.query.filter(
        FeuxBrousse.date_debut >= debut_annee).count()
    superficie = db.session.query(
        func.coalesce(func.sum(FeuxBrousse.superficie_brulee_ha), 0)
    ).filter(FeuxBrousse.date_debut >= debut_annee).scalar()
    sites_critiques = SiteVulnerable.query.filter_by(
        niveau_vulnerabilite='Critique', statut='actif').count()
    sites_eleves = SiteVulnerable.query.filter_by(
        niveau_vulnerabilite='Élevé', statut='actif').count()
    braconnage_mois = IndicateurBraconnage.query.filter(
        IndicateurBraconnage.date_constat >= debut_mois).count()
    braconnage_grave = IndicateurBraconnage.query.filter_by(
        statut='nouveau', niveau_gravite='Critique').count()
    campagnes_cours = CampagneCollecte.query.filter_by(statut='en_cours').count()
    rapports_annee = Rapport.query.filter(
        Rapport.created_at >= debut_annee).count()
    obs_mois = ObservationTerrain.query.filter(
        ObservationTerrain.date_observation >= datetime.combine(debut_mois, datetime.min.time())
    ).count()

    return jsonify({
        'feux_annee': feux_annee,
        'superficie_brulee': round(float(superficie), 0),
        'sites_critiques': sites_critiques,
        'sites_eleves': sites_eleves,
        'sites_total': sites_critiques + sites_eleves,
        'braconnage_mois': braconnage_mois,
        'braconnage_grave': braconnage_grave,
        'campagnes_cours': campagnes_cours,
        'rapports_annee': rapports_annee,
        'obs_mois': obs_mois,
        'refreshed_at': datetime.utcnow().strftime('%H:%M:%S')
    })


@api_bp.route('/campagnes/<int:id>/observations')
@login_required
def campagne_observations_geojson(id):
    """GeoJSON des observations d'une campagne (pour mini-carte)"""
    campagne = db.get_or_404(CampagneCollecte, id)
    obs = campagne.observations.filter(
        ObservationTerrain.latitude.isnot(None),
        ObservationTerrain.longitude.isnot(None)
    ).all()
    features = []
    for o in obs:
        color = {
            'vegetation': '#27ae60', 'faune': '#2980b9',
            'feu': '#e74c3c', 'eau': '#16a085', 'sol': '#8e6b3e',
            'braconnage': '#8e44ad', 'infrastructure': '#95a5a6', 'autre': '#7f8c8d'
        }.get(o.categorie, '#7f8c8d')
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [o.longitude, o.latitude]},
            'properties': {
                'reference': o.reference,
                'titre': o.titre or o.description[:50] if o.description else o.reference,
                'categorie': o.categorie,
                'date': o.date_observation.strftime('%d/%m/%Y %H:%M'),
                'validee': o.validee,
                'niveau_alerte': o.niveau_alerte,
                'color': color
            }
        })
    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'campagne': {
            'reference': campagne.reference,
            'nom': campagne.nom,
            'zone': campagne.zone or ''
        }
    })


@api_bp.route('/couverture/resume')
@login_required
def couverture_resume():
    """Résumé des superficies par classe et par année"""
    annees = db.session.query(Couverture.annee).distinct().order_by(Couverture.annee).all()
    annees = [a[0] for a in annees]
    classes = ClasseCouverture.query.filter_by(actif=True).all()
    result = {}
    for annee in annees:
        result[annee] = {}
        for classe in classes:
            total = db.session.query(
                func.coalesce(func.sum(Couverture.superficie_ha), 0)
            ).filter_by(classe_id=classe.id, annee=annee).scalar()
            result[annee][classe.code] = round(float(total), 2)
    return jsonify(result)


@api_bp.route('/feux/statistiques')
@login_required
def feux_stats():
    """Statistiques des feux par année"""
    rows = db.session.query(
        func.extract('year', FeuxBrousse.date_debut).label('annee'),
        func.count(FeuxBrousse.id).label('nombre'),
        func.coalesce(func.sum(FeuxBrousse.superficie_brulee_ha), 0).label('superficie')
    ).group_by('annee').order_by('annee').all()
    return jsonify([{
        'annee': int(r.annee),
        'nombre': r.nombre,
        'superficie_ha': round(float(r.superficie), 1)
    } for r in rows])


@api_bp.route('/braconnage/statistiques')
@login_required
def braconnage_stats():
    """Statistiques des indicateurs de braconnage"""
    rows = db.session.query(
        IndicateurBraconnage.type_indicateur,
        func.count(IndicateurBraconnage.id).label('count')
    ).group_by(IndicateurBraconnage.type_indicateur).all()
    return jsonify([{'type': r.type_indicateur, 'count': r.count} for r in rows])


@api_bp.route('/sites-vulnerables/liste')
@login_required
def sites_liste():
    """Liste simplifiée des sites vulnérables pour export"""
    sites = SiteVulnerable.query.filter_by(statut='actif').all()
    return jsonify([s.to_dict() for s in sites])


@api_bp.route('/observations/recentes')
@login_required
def observations_recentes():
    """50 dernières observations validées"""
    obs = ObservationTerrain.query.filter_by(validee=True).order_by(
        ObservationTerrain.date_observation.desc()).limit(50).all()
    return jsonify([o.to_dict() for o in obs])
