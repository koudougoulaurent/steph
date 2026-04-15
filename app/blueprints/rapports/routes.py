"""
Blueprint Rapports - Génération de rapports PDF / Excel
"""

from flask import render_template, redirect, url_for, flash, request, send_file, abort
from flask_login import login_required, current_user
from datetime import datetime, date
import json
import os

from app import db
from app.blueprints.rapports import rapports_bp
from app.models import Rapport, User
from app.utils.report_generator import ReportGenerator
from app.utils.helpers import generate_reference


@rapports_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    type_r = request.args.get('type', '')
    statut = request.args.get('statut', '')

    query = Rapport.query.order_by(Rapport.created_at.desc())
    if type_r:
        query = query.filter_by(type_rapport=type_r)
    if statut:
        query = query.filter_by(statut=statut)
    rapports = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('rapports/index.html',
                           title='Rapports',
                           rapports=rapports,
                           type_r=type_r,
                           statut=statut)


@rapports_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    if request.method == 'POST':
        ref = generate_reference('RPT')
        type_rapport = request.form.get('type_rapport')
        periode_debut = datetime.strptime(request.form.get('periode_debut'), '%Y-%m-%d').date()
        periode_fin = datetime.strptime(request.form.get('periode_fin'), '%Y-%m-%d').date()

        rapport = Rapport(
            reference=ref,
            type_rapport=type_rapport,
            titre=request.form.get('titre') or _auto_titre(type_rapport, periode_debut, periode_fin),
            periode_debut=periode_debut,
            periode_fin=periode_fin,
            zone_couverte=request.form.get('zone_couverte', 'Région entière'),
            theme=request.form.get('theme', 'general'),
            resume_executif=request.form.get('resume_executif', ''),
            auteur_id=current_user.id,
            statut='brouillon'
        )
        db.session.add(rapport)
        db.session.commit()
        flash(f'Rapport {ref} créé.', 'success')
        return redirect(url_for('rapports.detail', id=rapport.id))

    return render_template('rapports/nouveau.html', title='Nouveau rapport')


@rapports_bp.route('/<int:id>')
@login_required
def detail(id):
    rapport = db.get_or_404(Rapport, id)
    return render_template('rapports/detail.html',
                           title=f'Rapport {rapport.reference}',
                           rapport=rapport)


@rapports_bp.route('/<int:id>/generer-pdf')
@login_required
def generer_pdf(id):
    rapport = db.get_or_404(Rapport, id)
    try:
        gen = ReportGenerator(rapport)
        pdf_path = gen.generate_pdf()
        rapport.fichier_pdf = pdf_path
        rapport.statut = 'genere'
        db.session.commit()
        flash('Rapport PDF généré avec succès.', 'success')
        return send_file(pdf_path, as_attachment=True,
                         download_name=os.path.basename(pdf_path))
    except Exception as e:
        flash(f'Erreur lors de la génération : {str(e)}', 'danger')
        return redirect(url_for('rapports.detail', id=id))


@rapports_bp.route('/<int:id>/generer-excel')
@login_required
def generer_excel(id):
    rapport = db.get_or_404(Rapport, id)
    try:
        gen = ReportGenerator(rapport)
        xlsx_path = gen.generate_excel()
        rapport.fichier_excel = xlsx_path
        rapport.statut = 'genere'
        db.session.commit()
        flash('Rapport Excel généré avec succès.', 'success')
        return send_file(xlsx_path, as_attachment=True,
                         download_name=os.path.basename(xlsx_path))
    except Exception as e:
        flash(f'Erreur lors de la génération : {str(e)}', 'danger')
        return redirect(url_for('rapports.detail', id=id))


@rapports_bp.route('/<int:id>/publier', methods=['POST'])
@login_required
def publier(id):
    if not current_user.has_role('admin', 'superviseur'):
        abort(403)
    rapport = db.get_or_404(Rapport, id)
    rapport.statut = 'publie'
    rapport.date_publication = datetime.utcnow()
    db.session.commit()
    flash('Rapport publié.', 'success')
    return redirect(url_for('rapports.detail', id=id))


def _auto_titre(type_rapport, debut, fin):
    """Génère automatiquement un titre si non renseigné"""
    labels = {
        'mensuel': 'Rapport mensuel',
        'trimestriel': 'Rapport trimestriel',
        'semestriel': 'Rapport semestriel',
        'annuel': f'Rapport annuel {debut.year}',
        'thematique': 'Rapport thématique',
        'incident': 'Rapport d\'incident',
    }
    base = labels.get(type_rapport, 'Rapport')
    return f"{base} - {debut.strftime('%d/%m/%Y')} au {fin.strftime('%d/%m/%Y')}"
