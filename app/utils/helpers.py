"""
Utilitaires généraux de l'application
"""

from datetime import datetime
from app import db


def generate_reference(prefix: str) -> str:
    """
    Génère une référence unique du type PREFIX-YYYY-NNN
    Ex: FEU-2024-042
    """
    year = datetime.now().year
    # On cherche le dernier ID de la table via un compteur simple
    import random
    rand_part = random.randint(100, 999)
    timestamp = datetime.now().strftime('%H%M%S')
    return f"{prefix}-{year}-{timestamp}{rand_part % 100:02d}"


def paginate_query(query, page, per_page=20):
    """Helper de pagination"""
    return query.paginate(page=page, per_page=per_page, error_out=False)


def format_superficie(ha: float) -> str:
    """Formate une superficie en ha/km²"""
    if ha >= 100:
        return f"{ha/100:.1f} km²"
    return f"{ha:.1f} ha"


def get_alert_color(niveau: str) -> str:
    """Retourne la couleur Bootstrap pour un niveau d'alerte"""
    colors = {
        'Normal': 'success',
        'Attention': 'warning',
        'Alerte': 'orange',
        'Urgence': 'danger',
        'Faible': 'success',
        'Moyen': 'warning',
        'Élevé': 'danger',
        'Critique': 'danger',
        'Fort': 'danger',
        'Grave': 'danger',
    }
    return colors.get(niveau, 'secondary')
