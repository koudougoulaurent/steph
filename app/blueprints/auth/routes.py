"""
Blueprint Auth - Routes d'authentification
"""

from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta

from app import db
from app.blueprints.auth import auth_bp
from app.models import User


def _get_login_attempts():
    """Retourne (nb_tentatives, heure_premiere_tentative) depuis la session."""
    return session.get('_login_attempts', 0), session.get('_login_first_attempt')


def _is_locked_out():
    """Vérifie si l'IP/session est bloquée suite à trop de tentatives."""
    attempts, first = _get_login_attempts()
    max_attempts = current_app.config.get('LOGIN_MAX_ATTEMPTS', 5)
    lockout_min = current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15)
    if attempts >= max_attempts and first:
        lockout_until = datetime.fromisoformat(first) + timedelta(minutes=lockout_min)
        if datetime.utcnow() < lockout_until:
            return True, lockout_until
        # Délai écoulé, réinitialiser
        session.pop('_login_attempts', None)
        session.pop('_login_first_attempt', None)
    return False, None


def _record_failed_attempt():
    attempts, first = _get_login_attempts()
    if attempts == 0:
        session['_login_first_attempt'] = datetime.utcnow().isoformat()
    session['_login_attempts'] = attempts + 1


def _reset_login_attempts():
    session.pop('_login_attempts', None)
    session.pop('_login_first_attempt', None)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    locked, until = _is_locked_out()
    if locked:
        flash(
            f'Trop de tentatives échouées. Réessayez après {until.strftime("%H:%M")}.',
            'danger'
        )
        return render_template('auth/login.html', title='Connexion - VégéSuivi Pro')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.actif:
            _reset_login_attempts()
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            current_app.logger.info('Connexion : %s', user.email)
            next_page = request.args.get('next')
            # Sécurité : éviter les redirections ouvertes
            if next_page and not next_page.startswith('/'):
                next_page = None
            flash(f'Bienvenue, {user.nom} !', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            _record_failed_attempt()
            attempts, _ = _get_login_attempts()
            max_attempts = current_app.config.get('LOGIN_MAX_ATTEMPTS', 5)
            remaining = max(0, max_attempts - attempts)
            if remaining > 0:
                flash(
                    f'Identifiant ou mot de passe incorrect. '
                    f'{remaining} tentative(s) restante(s) avant blocage.',
                    'danger'
                )
            else:
                lockout_min = current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15)
                flash(
                    f'Compte temporairement bloqué ({lockout_min} min) '
                    f'suite à plusieurs tentatives échouées.',
                    'danger'
                )
            current_app.logger.warning('Échec connexion : identifiant=%s', email)

    return render_template('auth/login.html', title='Connexion - VégéSuivi Pro')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        action = request.form.get('action', 'profil')

        if action == 'profil':
            # Mise à jour des informations personnelles
            nom = request.form.get('nom', '').strip()
            email = request.form.get('email', '').strip().lower()
            structure = request.form.get('structure', '').strip()

            if not nom:
                flash('Le nom complet est obligatoire.', 'warning')
                return redirect(url_for('auth.profil'))

            # Vérifier unicité email si modifié
            if email and email != current_user.email:
                existing = User.query.filter(
                    User.email == email,
                    User.id != current_user.id
                ).first()
                if existing:
                    flash('Cette adresse email est déjà utilisée par un autre compte.', 'danger')
                    return redirect(url_for('auth.profil'))
                current_user.email = email

            current_user.nom = nom
            current_user.structure = structure or current_user.structure
            db.session.commit()
            flash('Profil mis à jour avec succès.', 'success')

        elif action == 'password':
            # Changement de mot de passe
            mdp_actuel = request.form.get('mdp_actuel', '')
            new_password = request.form.get('mdp_nouveau', '').strip()
            confirm_password = request.form.get('mdp_confirm', '').strip()

            if not current_user.check_password(mdp_actuel):
                flash('Le mot de passe actuel est incorrect.', 'danger')
                return redirect(url_for('auth.profil'))

            if len(new_password) < 8:
                flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'warning')
                return redirect(url_for('auth.profil'))

            if new_password != confirm_password:
                flash('Les deux mots de passe ne correspondent pas.', 'warning')
                return redirect(url_for('auth.profil'))

            current_user.set_password(new_password)
            db.session.commit()
            flash('Mot de passe modifié avec succès.', 'success')

        return redirect(url_for('auth.profil'))

    return render_template('auth/profil.html', title='Mon Profil')

