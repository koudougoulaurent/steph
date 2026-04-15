"""
Blueprint Dashboard - Tableau de bord principal
"""

from flask import render_template, jsonify
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, date, timedelta

from app import db
from app.blueprints.dashboard import dashboard_bp
from app.models import (
    Couverture, FeuxBrousse, SiteVulnerable,
    IndicateurBraconnage, CampagneCollecte, Rapport, ClasseCouverture
)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Tableau de bord principal avec KPI et résumés"""
    today = date.today()
    debut_annee = today.replace(month=1, day=1)
    debut_trimestre = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)

    # KPI généraux
    stats = {
        'feux_annee': FeuxBrousse.query.filter(
            FeuxBrousse.date_debut >= debut_annee).count(),
        'superficie_brulee': db.session.query(
            func.coalesce(func.sum(FeuxBrousse.superficie_brulee_ha), 0)
        ).filter(FeuxBrousse.date_debut >= debut_annee).scalar(),
        'sites_critiques': SiteVulnerable.query.filter_by(
            niveau_vulnerabilite='Critique', statut='actif').count(),
        'sites_eleves': SiteVulnerable.query.filter_by(
            niveau_vulnerabilite='Élevé', statut='actif').count(),
        'braconnage_mois': IndicateurBraconnage.query.filter(
            IndicateurBraconnage.date_constat >= today.replace(day=1)).count(),
        'braconnage_grave': IndicateurBraconnage.query.filter_by(
            statut='nouveau', niveau_gravite='Critique').count(),
        'campagnes_cours': CampagneCollecte.query.filter_by(statut='en_cours').count(),
        'rapports_generes': Rapport.query.filter(
            Rapport.created_at >= debut_annee).count(),
    }

    # Évolution végétation (dernières années disponibles)
    annees_dispo = db.session.query(
        Couverture.annee).distinct().order_by(Couverture.annee).all()
    annees_dispo = [a[0] for a in annees_dispo]

    # Feux récents (10 derniers)
    feux_recents = FeuxBrousse.query.order_by(
        FeuxBrousse.date_debut.desc()).limit(10).all()

    # Alertes actives (braconnage non traité)
    alertes = IndicateurBraconnage.query.filter(
        IndicateurBraconnage.statut.in_(['nouveau', 'en_cours']),
        IndicateurBraconnage.niveau_gravite.in_(['Grave', 'Critique'])
    ).order_by(IndicateurBraconnage.date_constat.desc()).limit(8).all()

    # Campagnes en cours
    campagnes = CampagneCollecte.query.filter_by(
        statut='en_cours').order_by(
        CampagneCollecte.date_debut.desc()).limit(5).all()

    return render_template('dashboard/index.html',
                           title='Tableau de bord',
                           stats=stats,
                           annees_dispo=annees_dispo,
                           feux_recents=feux_recents,
                           alertes=alertes,
                           campagnes=campagnes)


@dashboard_bp.route('/api/stats-evolution')
@login_required
def api_stats_evolution():
    """API : Évolution des superficies par classe sur toutes les années"""
    classes = ClasseCouverture.query.filter_by(actif=True).all()
    annees = db.session.query(Couverture.annee).distinct().order_by(Couverture.annee).all()
    annees = [a[0] for a in annees]

    datasets = []
    for classe in classes:
        data_pts = []
        for annee in annees:
            total = db.session.query(
                func.coalesce(func.sum(Couverture.superficie_ha), 0)
            ).filter_by(classe_id=classe.id, annee=annee).scalar()
            data_pts.append(round(float(total), 1))
        datasets.append({
            'label': classe.label,
            'data': data_pts,
            'borderColor': classe.couleur_hex,
            'backgroundColor': classe.couleur_hex + '33',
            'tension': 0.4
        })

    return jsonify({'labels': annees, 'datasets': datasets})


@dashboard_bp.route('/api/stats-feux-mensuel')
@login_required
def api_stats_feux():
    """API : Nombre de feux par mois cette année"""
    today = date.today()
    mois_labels = []
    mois_data = []
    for m in range(1, today.month + 1):
        debut = date(today.year, m, 1)
        if m < 12:
            fin = date(today.year, m + 1, 1) - timedelta(days=1)
        else:
            fin = date(today.year, 12, 31)
        count = FeuxBrousse.query.filter(
            FeuxBrousse.date_debut >= debut,
            FeuxBrousse.date_debut <= fin
        ).count()
        import calendar
        mois_labels.append(calendar.month_abbr[m])
        mois_data.append(count)

    return jsonify({'labels': mois_labels, 'data': mois_data})
