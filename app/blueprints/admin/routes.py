"""
Blueprint Admin - Gestion des utilisateurs, données de référence, imports
"""

from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import csv
import io

from app import db
from app.blueprints.admin import admin_bp
from app.models import User, ClasseCouverture, Couverture
from app.utils.helpers import generate_reference


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def index():
    stats = {
        'users': User.query.count(),
        'classes': ClasseCouverture.query.count(),
        'couvertures': Couverture.query.count(),
    }
    return render_template('admin/index.html',
                           title='Administration',
                           stats=stats)


# ───── Gestion des utilisateurs ─────

@admin_bp.route('/utilisateurs')
@login_required
@admin_required
def utilisateurs():
    users = User.query.order_by(User.nom).all()
    return render_template('admin/utilisateurs.html',
                           title='Utilisateurs',
                           users=users)


@admin_bp.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def utilisateur_nouveau():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'warning')
            return redirect(url_for('admin.utilisateurs'))
        u = User(
            nom=request.form.get('nom'),
            email=email,
            role=request.form.get('role', 'agent'),
            structure=request.form.get('structure'),
            telephone=request.form.get('telephone'),
        )
        u.set_password(request.form.get('password'))
        db.session.add(u)
        db.session.commit()
        flash(f'Utilisateur {u.nom} créé.', 'success')
        return redirect(url_for('admin.utilisateurs'))
    return render_template('admin/utilisateur_form.html', title='Nouvel utilisateur', user=None)


@admin_bp.route('/utilisateurs/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@admin_required
def utilisateur_modifier(id):
    user = db.get_or_404(User, id)
    if request.method == 'POST':
        user.nom = request.form.get('nom', user.nom)
        user.role = request.form.get('role', user.role)
        user.structure = request.form.get('structure', user.structure)
        user.telephone = request.form.get('telephone', user.telephone)
        user.actif = bool(request.form.get('actif'))
        new_pass = request.form.get('password', '').strip()
        if new_pass:
            user.set_password(new_pass)
        db.session.commit()
        flash('Utilisateur mis à jour.', 'success')
        return redirect(url_for('admin.utilisateurs'))
    return render_template('admin/utilisateur_form.html',
                           title='Modifier utilisateur',
                           user=user)


# ───── Classes de couverture ─────

@admin_bp.route('/classes-couverture')
@login_required
@admin_required
def classes_couverture():
    classes = ClasseCouverture.query.order_by(ClasseCouverture.ordre_affichage).all()
    return render_template('admin/classes_couverture.html',
                           title='Classes de couverture',
                           classes=classes)


@admin_bp.route('/classes-couverture/nouvelle', methods=['POST'])
@login_required
@admin_required
def classe_couverture_nouvelle():
    c = ClasseCouverture(
        code=request.form.get('code'),
        label=request.form.get('label'),
        description=request.form.get('description'),
        couleur_hex=request.form.get('couleur_hex', '#3388ff'),
        categorie=request.form.get('categorie'),
        ordre_affichage=int(request.form.get('ordre_affichage', 0))
    )
    db.session.add(c)
    db.session.commit()
    flash('Classe ajoutée.', 'success')
    return redirect(url_for('admin.classes_couverture'))


# ───── Import CSV de données de végétation ─────

@admin_bp.route('/import-couverture', methods=['GET', 'POST'])
@login_required
@admin_required
def import_couverture():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash('Veuillez sélectionner un fichier CSV valide.', 'warning')
            return redirect(url_for('admin.import_couverture'))
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'), newline=None)
        reader = csv.DictReader(stream)
        count = 0
        errors = []
        for i, row in enumerate(reader, 1):
            try:
                classe = ClasseCouverture.query.filter_by(
                    code=row.get('code_classe', '').strip()).first()
                if not classe:
                    errors.append(f"Ligne {i} : classe '{row.get('code_classe')}' introuvable.")
                    continue
                c = Couverture(
                    annee=int(row['annee']),
                    classe_id=classe.id,
                    zone=row.get('zone', ''),
                    superficie_ha=float(row.get('superficie_ha', 0)),
                    superficie_km2=float(row.get('superficie_km2', 0)),
                    variation_ha=float(row.get('variation_ha', 0)),
                    taux_variation=float(row.get('taux_variation', 0)),
                    source=row.get('source', ''),
                    methode=row.get('methode', ''),
                )
                db.session.add(c)
                count += 1
            except Exception as e:
                errors.append(f"Ligne {i} : {e}")
        db.session.commit()
        flash(f'{count} enregistrement(s) importé(s).', 'success')
        if errors:
            flash(f'{len(errors)} erreur(s) : ' + ' | '.join(errors[:5]), 'warning')
        return redirect(url_for('admin.import_couverture'))
    return render_template('admin/import_couverture.html', title='Importer données de couverture')
