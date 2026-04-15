"""
Blueprint Collecte - Gestion des campagnes et observations terrain
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
import json

from app import db
from app.blueprints.collecte import collecte_bp
from app.models import CampagneCollecte, ObservationTerrain, User
from app.utils.helpers import generate_reference, paginate_query


# ──────────────── CAMPAGNES ────────────────

@collecte_bp.route('/campagnes')
@login_required
def campagnes_list():
    statut = request.args.get('statut', '')
    page = request.args.get('page', 1, type=int)
    query = CampagneCollecte.query.order_by(CampagneCollecte.date_debut.desc())
    if statut:
        query = query.filter_by(statut=statut)
    campagnes = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('collecte/campagnes_list.html',
                           title='Campagnes de collecte',
                           campagnes=campagnes,
                           statut=statut)


@collecte_bp.route('/campagnes/<int:id>')
@login_required
def campagne_detail(id):
    campagne = db.get_or_404(CampagneCollecte, id)
    observations = campagne.observations.order_by(
        ObservationTerrain.date_observation.desc()).all()
    return render_template('collecte/campagne_detail.html',
                           title=f'Campagne {campagne.reference}',
                           campagne=campagne,
                           observations=observations)


@collecte_bp.route('/campagnes/nouvelle', methods=['GET', 'POST'])
@login_required
def campagne_nouvelle():
    agents = User.query.filter_by(actif=True).order_by(User.nom).all()
    if request.method == 'POST':
        try:
            ref = generate_reference('CAM')
            camp = CampagneCollecte(
                reference=ref,
                nom=request.form.get('nom'),
                objectif=request.form.get('objectif'),
                date_debut=datetime.strptime(request.form.get('date_debut'), '%Y-%m-%d').date(),
                date_fin_prevue=datetime.strptime(request.form.get('date_fin_prevue'), '%Y-%m-%d').date()
                if request.form.get('date_fin_prevue') else None,
                zone_couverte=request.form.get('zone_couverte'),
                responsable_id=current_user.id,
                protocole=request.form.get('protocole'),
                materiels=request.form.get('materiels'),
                statut='planifie'
            )
            db.session.add(camp)
            db.session.commit()
            flash(f'Campagne {ref} créée avec succès.', 'success')
            return redirect(url_for('collecte.campagne_detail', id=camp.id))
        except (ValueError, KeyError) as e:
            db.session.rollback()
            flash('Données invalides. Vérifiez les champs obligatoires et les formats de dates.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la création de la campagne. Veuillez réessayer.', 'danger')
    return render_template('collecte/campagne_form.html',
                           title='Nouvelle campagne',
                           agents=agents)


# ──────────────── OBSERVATIONS ────────────────

@collecte_bp.route('/observations')
@login_required
def observations_list():
    page = request.args.get('page', 1, type=int)
    categorie = request.args.get('categorie', '')
    validee = request.args.get('validee', '')
    query = ObservationTerrain.query.order_by(
        ObservationTerrain.date_observation.desc())
    if categorie:
        query = query.filter_by(categorie=categorie)
    if validee == '1':
        query = query.filter_by(validee=True)
    elif validee == '0':
        query = query.filter_by(validee=False)
    observations = query.paginate(page=page, per_page=25, error_out=False)
    return render_template('collecte/observations_list.html',
                           title='Observations terrain',
                           observations=observations,
                           categorie=categorie,
                           validee=validee)


@collecte_bp.route('/observations/nouvelle', methods=['GET', 'POST'])
@login_required
def observation_nouvelle():
    campagnes = CampagneCollecte.query.filter_by(statut='en_cours').all()
    if request.method == 'POST':
        try:
            ref = generate_reference('OBS')
            obs = ObservationTerrain(
                reference=ref,
                campagne_id=request.form.get('campagne_id') or None,
                agent_id=current_user.id,
                date_observation=datetime.strptime(
                    request.form.get('date_observation'), '%Y-%m-%dT%H:%M'),
                latitude=float(request.form.get('latitude')),
                longitude=float(request.form.get('longitude')),
                altitude_m=float(request.form.get('altitude_m')) if request.form.get('altitude_m') else None,
                zone=request.form.get('zone'),
                categorie=request.form.get('categorie'),
                titre=request.form.get('titre'),
                description=request.form.get('description'),
                etat_general=request.form.get('etat_general'),
                niveau_alerte=request.form.get('niveau_alerte'),
                valeur_numerique=float(request.form.get('valeur_numerique')) if request.form.get('valeur_numerique') else None,
                unite=request.form.get('unite'),
            )
            db.session.add(obs)
            db.session.commit()
            flash(f'Observation {ref} enregistrée.', 'success')
            return redirect(url_for('collecte.observations_list'))
        except (ValueError, KeyError):
            db.session.rollback()
            flash('Données invalides. Vérifiez les coordonnées GPS et le format de la date.', 'danger')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de l\'enregistrement. Veuillez réessayer.', 'danger')
    return render_template('collecte/observation_form.html',
                           title='Nouvelle observation',
                           campagnes=campagnes)


@collecte_bp.route('/observations/<int:id>/valider', methods=['POST'])
@login_required
def valider_observation(id):
    if not current_user.has_role('admin', 'superviseur'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('collecte.observations_list'))
    obs = db.get_or_404(ObservationTerrain, id)
    obs.validee = True
    obs.valide_par = current_user.id
    obs.date_validation = datetime.utcnow()
    obs.commentaire_validation = request.form.get('commentaire', '')
    db.session.commit()
    flash('Observation validée.', 'success')
    return redirect(url_for('collecte.observations_list'))


# ──────────────── DONNÉES FEUX / SITES / BRACONNAGE ────────────────

@collecte_bp.route('/feux-brousse')
@login_required
def feux_list():
    page = request.args.get('page', 1, type=int)
    from app.models import FeuxBrousse
    feux = FeuxBrousse.query.order_by(
        FeuxBrousse.date_debut.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('collecte/feux_list.html',
                           title='Feux de brousse',
                           feux=feux)


@collecte_bp.route('/feux-brousse/nouveau', methods=['GET', 'POST'])
@login_required
def feu_nouveau():
    from app.models import FeuxBrousse
    if request.method == 'POST':
        try:
            ref = generate_reference('FEU')
            feu = FeuxBrousse(
                reference=ref,
                date_debut=datetime.strptime(request.form.get('date_debut'), '%Y-%m-%d').date(),
                zone=request.form.get('zone'),
                village_proche=request.form.get('village_proche'),
                latitude=float(request.form.get('latitude')) if request.form.get('latitude') else None,
                longitude=float(request.form.get('longitude')) if request.form.get('longitude') else None,
                superficie_brulee_ha=float(request.form.get('superficie_brulee_ha', 0)),
                intensite=request.form.get('intensite'),
                type_vegetation=request.form.get('type_vegetation'),
                cause=request.form.get('cause'),
                cause_detail=request.form.get('cause_detail'),
                impact_faune=request.form.get('impact_faune'),
                description_impact=request.form.get('description_impact'),
                signale_par=request.form.get('signale_par'),
                statut='en_cours',
                created_by=current_user.id
            )
            db.session.add(feu)
            db.session.commit()
            flash(f'Feu de brousse {ref} enregistré.', 'success')
            return redirect(url_for('collecte.feux_list'))
        except (ValueError, KeyError):
            db.session.rollback()
            flash('Données invalides. Vérifiez les champs obligatoires.', 'danger')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de l\'enregistrement. Veuillez réessayer.', 'danger')
    return render_template('collecte/feu_form.html', title='Nouveau feu de brousse')


@collecte_bp.route('/sites-vulnerables')
@login_required
def sites_list():
    page = request.args.get('page', 1, type=int)
    niveau = request.args.get('niveau', '')
    from app.models import SiteVulnerable
    query = SiteVulnerable.query.filter_by(statut='actif')
    if niveau:
        query = query.filter_by(niveau_vulnerabilite=niveau)
    sites = query.order_by(SiteVulnerable.score_vulnerabilite.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('collecte/sites_list.html',
                           title='Sites vulnérables',
                           sites=sites,
                           niveau=niveau)


@collecte_bp.route('/sites-vulnerables/nouveau', methods=['GET', 'POST'])
@login_required
def site_nouveau():
    from app.models import SiteVulnerable
    if request.method == 'POST':
        try:
            ref = generate_reference('SV')
            site = SiteVulnerable(
                reference=ref,
                nom=request.form.get('nom'),
                date_identification=datetime.strptime(
                    request.form.get('date_identification'), '%Y-%m-%d').date(),
                zone=request.form.get('zone'),
                localite=request.form.get('localite'),
                latitude=float(request.form.get('latitude')),
                longitude=float(request.form.get('longitude')),
                type_site=request.form.get('type_site'),
                superficie_ha=float(request.form.get('superficie_ha', 0)),
                niveau_vulnerabilite=request.form.get('niveau_vulnerabilite'),
                score_vulnerabilite=int(request.form.get('score_vulnerabilite', 0)),
                pressions=request.form.get('pressions'),
                especes_cles=request.form.get('especes_cles'),
                valeur_ecologique=request.form.get('valeur_ecologique'),
                mesures_protection=request.form.get('mesures_protection'),
                frequence_surveillance=request.form.get('frequence_surveillance'),
                observations=request.form.get('observations'),
                created_by=current_user.id
            )
            db.session.add(site)
            db.session.commit()
            flash(f'Site vulnérable {ref} enregistré.', 'success')
            return redirect(url_for('collecte.sites_list'))
        except (ValueError, KeyError):
            db.session.rollback()
            flash('Données invalides. Vérifiez les coordonnées GPS et les champs numériques.', 'danger')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de l\'enregistrement. Veuillez réessayer.', 'danger')
    return render_template('collecte/site_form.html', title='Nouveau site vulnérable')


@collecte_bp.route('/braconnage')
@login_required
def braconnage_list():
    page = request.args.get('page', 1, type=int)
    from app.models import IndicateurBraconnage
    indicateurs = IndicateurBraconnage.query.order_by(
        IndicateurBraconnage.date_constat.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('collecte/braconnage_list.html',
                           title='Indicateurs de braconnage',
                           indicateurs=indicateurs)


@collecte_bp.route('/braconnage/nouveau', methods=['GET', 'POST'])
@login_required
def braconnage_nouveau():
    from app.models import IndicateurBraconnage
    if request.method == 'POST':
        try:
            ref = generate_reference('BR')
            ind = IndicateurBraconnage(
                reference=ref,
                date_constat=datetime.strptime(request.form.get('date_constat'), '%Y-%m-%d').date(),
                zone=request.form.get('zone'),
                localite=request.form.get('localite'),
                latitude=float(request.form.get('latitude')) if request.form.get('latitude') else None,
                longitude=float(request.form.get('longitude')) if request.form.get('longitude') else None,
                type_indicateur=request.form.get('type_indicateur'),
                description=request.form.get('description'),
                especes_concernees=request.form.get('especes_concernees'),
                nombre_indices=int(request.form.get('nombre_indices', 1)),
                niveau_gravite=request.form.get('niveau_gravite'),
                activite_recente=bool(request.form.get('activite_recente')),
                alerte_emise=bool(request.form.get('alerte_emise')),
                saisies_effectuees=bool(request.form.get('saisies_effectuees')),
                detail_saisies=request.form.get('detail_saisies'),
                arrestations=int(request.form.get('arrestations', 0)),
                signale_par=request.form.get('signale_par'),
                source_info=request.form.get('source_info'),
                statut='nouveau',
                created_by=current_user.id
            )
            db.session.add(ind)
            db.session.commit()
            flash(f'Indicateur de braconnage {ref} enregistré.', 'success')
            return redirect(url_for('collecte.braconnage_list'))
        except (ValueError, KeyError):
            db.session.rollback()
            flash('Données invalides. Vérifiez les champs obligatoires.', 'danger')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de l\'enregistrement. Veuillez réessayer.', 'danger')
    return render_template('collecte/braconnage_form.html',
                           title='Nouvel indicateur de braconnage')


# ─── Changement de statut (AJAX/POST) ────────────────────────────────────────

@collecte_bp.route('/campagnes/<int:id>/statut', methods=['POST'])
@login_required
def campagne_changer_statut(id):
    """Change le statut d'une campagne : planifie → en_cours → termine / annule"""
    from app.models import CampagneCollecte
    campagne = db.get_or_404(CampagneCollecte, id)
    nouveau_statut = request.form.get('statut')
    statuts_valides = ['planifie', 'en_cours', 'termine', 'annule']
    if nouveau_statut not in statuts_valides:
        flash('Statut invalide.', 'danger')
        return redirect(url_for('collecte.campagne_detail', id=id))
    campagne.statut = nouveau_statut
    if nouveau_statut == 'termine' and not campagne.date_fin_reelle:
        campagne.date_fin_reelle = date.today()
    if nouveau_statut == 'en_cours' and not campagne.date_debut:
        campagne.date_debut = date.today()
    db.session.commit()
    flash(f'Statut mis à jour : « {nouveau_statut.replace("_", " ").title()} »', 'success')
    return redirect(url_for('collecte.campagne_detail', id=id))


@collecte_bp.route('/braconnage/<int:id>/statut', methods=['POST'])
@login_required
def braconnage_changer_statut(id):
    """Change le statut d'un indicateur de braconnage"""
    from app.models import IndicateurBraconnage
    ind = db.get_or_404(IndicateurBraconnage, id)
    nouveau_statut = request.form.get('statut')
    statuts_valides = ['nouveau', 'en_cours', 'traite', 'archive']
    if nouveau_statut not in statuts_valides:
        flash('Statut invalide.', 'danger')
        return redirect(url_for('collecte.braconnage_list'))
    ind.statut = nouveau_statut
    db.session.commit()
    flash(f'Statut mis à jour : « {nouveau_statut.replace("_", " ").title()} »', 'success')
    return redirect(url_for('collecte.braconnage_list'))


# ─── Détails incidents ────────────────────────────────────────────────────────

@collecte_bp.route('/braconnage/<int:id>')
@login_required
def braconnage_detail(id):
    """Page de détail d'un indicateur de braconnage"""
    from app.models import IndicateurBraconnage
    ind = db.get_or_404(IndicateurBraconnage, id)
    return render_template('collecte/braconnage_detail.html',
                           title=f'Braconnage {ind.reference}',
                           ind=ind)


@collecte_bp.route('/feux-brousse/<int:id>')
@login_required
def feu_detail(id):
    """Page de détail d'un feu de brousse"""
    from app.models import FeuxBrousse
    feu = db.get_or_404(FeuxBrousse, id)
    return render_template('collecte/feu_detail.html',
                           title=f'Feu {feu.reference}',
                           feu=feu)


@collecte_bp.route('/feux-brousse/<int:id>/statut', methods=['POST'])
@login_required
def feu_changer_statut(id):
    """Change le statut d'un feu de brousse"""
    from app.models import FeuxBrousse
    feu = db.get_or_404(FeuxBrousse, id)
    nouveau_statut = request.form.get('statut')
    statuts_valides = ['en_cours', 'surveille', 'éteint']
    if nouveau_statut not in statuts_valides:
        flash('Statut invalide.', 'danger')
        return redirect(url_for('collecte.feu_detail', id=id))
    feu.statut = nouveau_statut
    if nouveau_statut == 'éteint' and not feu.date_fin:
        feu.date_fin = date.today()
    db.session.commit()
    flash(f'Statut mis à jour : « {nouveau_statut.title()} »', 'success')
    return redirect(url_for('collecte.feu_detail', id=id))


@collecte_bp.route('/sites-vulnerables/<int:id>')
@login_required
def site_detail(id):
    """Page de détail d'un site vulnérable"""
    from app.models import SiteVulnerable
    site = db.get_or_404(SiteVulnerable, id)
    return render_template('collecte/site_detail.html',
                           title=f'Site {site.reference}',
                           site=site)


@collecte_bp.route('/sites-vulnerables/<int:id>/statut', methods=['POST'])
@login_required
def site_changer_statut(id):
    """Change le statut d'un site vulnérable"""
    from app.models import SiteVulnerable
    site = db.get_or_404(SiteVulnerable, id)
    nouveau_statut = request.form.get('statut')
    statuts_valides = ['actif', 'surveille', 'archive']
    if nouveau_statut not in statuts_valides:
        flash('Statut invalide.', 'danger')
        return redirect(url_for('collecte.site_detail', id=id))
    site.statut = nouveau_statut
    db.session.commit()
    flash(f'Statut mis à jour : « {nouveau_statut.title()} »', 'success')
    return redirect(url_for('collecte.site_detail', id=id))


@collecte_bp.route('/observations/<int:id>')
@login_required
def observation_detail(id):
    """Page de détail d'une observation terrain"""
    obs = db.get_or_404(ObservationTerrain, id)
    return render_template('collecte/observation_detail.html',
                           title=f'Observation {obs.reference}',
                           obs=obs)


# ─── Export PDF direct ────────────────────────────────────────────────────────

@collecte_bp.route('/feux-brousse/export.pdf')
@login_required
def feux_export_pdf():
    """Exporte la liste complète des feux en PDF"""
    from app.models import FeuxBrousse
    from app.utils.export_pdf import export_feux_pdf
    from flask import make_response
    feux = FeuxBrousse.query.order_by(FeuxBrousse.date_debut.desc()).all()
    pdf_bytes = export_feux_pdf(feux)
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=feux_export.pdf'
    return response


@collecte_bp.route('/sites-vulnerables/export.pdf')
@login_required
def sites_export_pdf():
    """Exporte la liste complète des sites vulnérables en PDF"""
    from app.models import SiteVulnerable
    from app.utils.export_pdf import export_sites_pdf
    from flask import make_response
    sites = SiteVulnerable.query.order_by(SiteVulnerable.score_vulnerabilite.desc()).all()
    pdf_bytes = export_sites_pdf(sites)
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=sites_export.pdf'
    return response


@collecte_bp.route('/braconnage/export.pdf')
@login_required
def braconnage_export_pdf():
    """Exporte la liste complète du braconnage en PDF"""
    from app.models import IndicateurBraconnage
    from app.utils.export_pdf import export_braconnage_pdf
    from flask import make_response
    indicateurs = IndicateurBraconnage.query.order_by(
        IndicateurBraconnage.date_constat.desc()).all()
    pdf_bytes = export_braconnage_pdf(indicateurs)
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=braconnage_export.pdf'
    return response


@collecte_bp.route('/observations/export.pdf')
@login_required
def observations_export_pdf():
    """Exporte la liste complète des observations en PDF"""
    from app.utils.export_pdf import export_observations_pdf
    from flask import make_response
    observations = ObservationTerrain.query.order_by(
        ObservationTerrain.date_observation.desc()).all()
    pdf_bytes = export_observations_pdf(observations)
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=observations_export.pdf'
    return response
