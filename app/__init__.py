"""
VégéSuivi Pro - Initialisation de l'application Flask
"""

import secrets
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from flask import Flask, session, request, abort, render_template, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def _generate_csrf():
    """Retourne le token CSRF de session, en le créant si besoin."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def create_app(config_name='default'):
    app = Flask(__name__)

    from app.config import config
    app.config.from_object(config[config_name])

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    # ── Protection CSRF (tous les formulaires POST) ────────────────
    @app.before_request
    def csrf_protect():
        if request.method == 'POST':
            # Bypass en mode test (test_client)
            if current_app.testing:
                return
            # Exclure les endpoints API (tokens Bearer)
            if request.path.startswith('/api/'):
                return
            token = session.get('_csrf_token')
            form_token = (request.form.get('csrf_token') or
                          request.headers.get('X-CSRFToken'))
            if not token or token != form_token:
                abort(403)

    # ── Headers HTTP de sécurité ───────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(self), camera=(), microphone=()'
        # En production avec HTTPS, ajouter HSTS
        # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.cartographie import carto_bp
    from app.blueprints.collecte import collecte_bp
    from app.blueprints.rapports import rapports_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp
    from app.blueprints.indices import indices_bp
    from app.blueprints.donnees_terrain import donnees_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(carto_bp, url_prefix='/cartographie')
    app.register_blueprint(collecte_bp, url_prefix='/collecte')
    app.register_blueprint(rapports_bp, url_prefix='/rapports')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(indices_bp, url_prefix='/indices')
    app.register_blueprint(donnees_bp, url_prefix='/donnees-terrain')

    # ── Context processors ─────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow,
            'app_name': 'VégéSuivi Pro',
            'csrf_token': _generate_csrf,
        }

    # ── Gestionnaires d'erreurs ────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    with app.app_context():
        db.create_all()

    # ── Logging ───────────────────────────────────────────────────
    if not app.debug:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'vegesuivi.log'),
            maxBytes=2 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(module)s] %(message)s'
        ))
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.WARNING)

    return app
