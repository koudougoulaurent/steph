"""
VégéSuivi Pro - Configuration de l'application
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vegesuivi-pro-secret-key-dre-2024-dev-only'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Cookies de session sécurisés ──────────────────────────────
    SESSION_COOKIE_HTTPONLY = True        # Interdit l'accès JS au cookie
    SESSION_COOKIE_SAMESITE = 'Lax'      # Protection CSRF navigateur
    SESSION_COOKIE_SECURE = False         # True en HTTPS production
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=1)
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # Upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff', 'geojson', 'shp', 'zip', 'csv', 'xlsx'}

    # Rapports
    RAPPORTS_FOLDER = os.path.join(BASE_DIR, 'rapports_generes')

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Brute-force login
    LOGIN_MAX_ATTEMPTS = 5               # Tentatives avant blocage
    LOGIN_LOCKOUT_MINUTES = 15           # Durée de blocage (minutes)

    # Application
    APP_NAME = "VégéSuivi Pro"
    APP_VERSION = "1.0.0"
    ORGANISATION = "Direction Régionale de l'Environnement"
    REGION = "À configurer"

    # Pagination
    ITEMS_PER_PAGE = 20

    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['RAPPORTS_FOLDER'], exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'vegesuivi_dev.db')}"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True          # Exige HTTPS en production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'vegesuivi_prod.db')}"
    # Pour PostgreSQL/PostGIS : changer pour :
    # postgresql://user:password@localhost/vegesuivi_db

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Forcer une SECRET_KEY non triviale en production
        if app.config['SECRET_KEY'] == 'vegesuivi-pro-secret-key-dre-2024-dev-only':
            import warnings
            warnings.warn(
                'AVERTISSEMENT SECURITE : Définissez la variable d\'environnement '
                'SECRET_KEY avant de déployer en production !',
                stacklevel=2
            )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
