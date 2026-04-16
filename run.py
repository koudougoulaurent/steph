"""
VégéSuivi Pro - Point d'entrée de l'application
Plateforme de suivi de la dynamique d'occupation des terres
Direction Régionale de l'Environnement
"""

from app import create_app, db
from app.models import User, Couverture, FeuxBrousse, SiteVulnerable, IndicateurBraconnage, Rapport, CampagneCollecte
import os

config_name = os.environ.get('FLASK_CONFIG', 'default')
app = create_app(config_name)

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Couverture': Couverture,
        'FeuxBrousse': FeuxBrousse,
        'SiteVulnerable': SiteVulnerable,
        'IndicateurBraconnage': IndicateurBraconnage,
        'Rapport': Rapport,
        'CampagneCollecte': CampagneCollecte,
    }

@app.cli.command("init-db")
def init_db():
    """Initialise la base de données avec les données de démo."""
    from app.utils.seed import seed_database
    seed_database()
    print("Base de données initialisée avec succès.")

@app.cli.command("create-admin")
def create_admin():
    """Crée un utilisateur administrateur."""
    from app.models import User
    import getpass
    nom = input("Nom complet : ")
    email = input("Email : ")
    password = getpass.getpass("Mot de passe : ")
    user = User(nom=nom, email=email, role='admin')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Administrateur '{nom}' créé avec succès.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
