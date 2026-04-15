"""
Modèle Utilisateur - Gestion des comptes et authentification
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(30), default='agent')  # admin | superviseur | agent | lecteur
    structure = db.Column(db.String(150))            # Service/Bureau d'appartenance
    telephone = db.Column(db.String(20))
    actif = db.Column(db.Boolean, default=True)
    photo = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relations
    observations = db.relationship(
        'ObservationTerrain',
        foreign_keys='ObservationTerrain.agent_id',
        backref='agent',
        lazy='dynamic'
    )
    observations_validees = db.relationship(
        'ObservationTerrain',
        foreign_keys='ObservationTerrain.valide_par',
        backref='validateur',
        lazy='dynamic'
    )
    campagnes = db.relationship('CampagneCollecte', backref='responsable', lazy='dynamic')
    rapports = db.relationship(
        'Rapport',
        foreign_keys='Rapport.auteur_id',
        backref='auteur',
        lazy='dynamic'
    )
    rapports_valides = db.relationship(
        'Rapport',
        foreign_keys='Rapport.valide_par',
        backref='validateur_rapport',
        lazy='dynamic'
    )

    ROLES = {
        'admin': 'Administrateur',
        'superviseur': 'Superviseur',
        'agent': 'Agent de terrain',
        'lecteur': 'Lecteur'
    }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

    def get_role_label(self):
        return self.ROLES.get(self.role, self.role)

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
