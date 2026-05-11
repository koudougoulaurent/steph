"""
Données de démonstration pour l'Atlas des résultats de thèse.
Couverture végétale — Boucle du Mouhoun · Superficie totale : 30 000 ha
5 grands groupes : Forêt-galerie, Savanes, Champs, Sols, Surface en eau
"""

from app import db
from app.models import ClasseCouverture
from app.models.atlas import ResultatAtlas


# Années des données observées (télédétection)
_ANNEES_OBS = [1986, 1990, 1995, 2000, 2005, 2010, 2014, 2020, 2024]

# 5 groupes — superficies en ha, une valeur par année observée
# FFG = Forêt galerie + Forêt sèche agrégées
# SAT = Savane arborée + Savane herbeuse agrégées
_OBSERVED = {
    'FFG': [10700, 10050, 9400, 8630, 7980, 7300, 6820, 6170, 5600],
    'SAT': [12000, 11950, 11800, 11600, 11420, 11280, 11100, 11000, 10800],
    'AGR': [ 3500,  4100,  4800,  5400,  5900,  6400,  6700,  7100,  7500],
    'SOL': [ 2800,  2900,  3000,  3370,  3700,  4070,  4380,  4730,  5200],
    'EAU': [ 1000,  1000,  1000,  1000,  1000,   950,   900,   900,   900],
}

# Projections 2030 · 2040 · 2050
_ANNEES_PROJ = [2030, 2040, 2050]

_PROJETE_TEND = {
    'FFG': [4900, 4150, 3300],
    'SAT': [10600, 10400, 10150],
    'AGR': [8000, 8700, 9350],
    'SOL': [5600, 5950, 6400],
    'EAU': [ 900,  800,  800],
}

_PROJETE_OPTI = {
    'FFG': [5350, 4800, 4300],
    'SAT': [10700, 10300, 9900],
    'AGR': [7400, 7800, 8100],
    'SOL': [4750, 4450, 4100],
    'EAU': [ 900,  850,  800],
}

_PROJETE_PESS = {
    'FFG': [4300, 3300, 2400],
    'SAT': [10300, 9700, 9300],
    'AGR': [8600, 9500, 10500],
    'SOL': [5900, 6700, 7000],
    'EAU': [ 900,  800,  800],
}

# Coordonnées représentatives (Boucle du Mouhoun, Burkina Faso)
_COORDS = {
    'FFG': (12.10, -4.22),
    'SAT': (12.02, -4.15),
    'AGR': (11.85, -4.30),
    'SOL': (12.05, -4.42),
    'EAU': (12.18, -4.20),
}

# Nouveaux libellés simplifiés pour l'Atlas
_LABELS_ATLAS = {
    'FFG': 'Forêt-galerie',
    'SAT': 'Savanes',
    'AGR': 'Champs',
    'SOL': 'Sols',
    'EAU': 'Surface en eau',
}

_ZONE = "Boucle du Mouhoun"
_TOTAL = 30000.0


def seed_atlas() -> int:
    """
    Peuple resultats_atlas avec les données de démonstration.
    Idempotente : efface d'abord les enregistrements existants.
    Retourne le nombre d'enregistrements créés.
    """
    all_classes = {c.code: c for c in ClasseCouverture.query.all()}

    codes_requis = set(_OBSERVED.keys())
    manquants = codes_requis - set(all_classes.keys())
    if manquants:
        raise ValueError(
            f"Classes manquantes dans classes_couverture : {manquants}. "
            "Lancez d'abord le seed principal (flask seed-db)."
        )

    # Mettre à jour les libellés dans ClasseCouverture pour l'Atlas
    for code, label in _LABELS_ATLAS.items():
        if code in all_classes:
            all_classes[code].label = label
    db.session.flush()

    # Nettoyage préalable
    ResultatAtlas.query.delete()
    db.session.flush()

    records = []

    # Données observées
    for code, superficies in _OBSERVED.items():
        classe = all_classes[code]
        lat, lng = _COORDS[code]
        for i, annee in enumerate(_ANNEES_OBS):
            sup_ha  = superficies[i]
            sup_pct = round(sup_ha / _TOTAL * 100, 2)
            records.append(ResultatAtlas(
                annee=annee,
                classe_id=classe.id,
                zone=_ZONE,
                superficie_ha=sup_ha,
                superficie_pct=sup_pct,
                type_donnee='observe',
                scenario='tendanciel',
                latitude_centre=lat,
                longitude_centre=lng,
            ))

    # Projections
    for scenario_key, scenario_data in [
        ('tendanciel', _PROJETE_TEND),
        ('optimiste',  _PROJETE_OPTI),
        ('pessimiste', _PROJETE_PESS),
    ]:
        for code, superficies in scenario_data.items():
            classe = all_classes[code]
            lat, lng = _COORDS[code]
            for i, annee in enumerate(_ANNEES_PROJ):
                sup_ha  = superficies[i]
                sup_pct = round(sup_ha / _TOTAL * 100, 2)
                records.append(ResultatAtlas(
                    annee=annee,
                    classe_id=classe.id,
                    zone=_ZONE,
                    superficie_ha=sup_ha,
                    superficie_pct=sup_pct,
                    type_donnee='projete',
                    scenario=scenario_key,
                    latitude_centre=lat,
                    longitude_centre=lng,
                ))

    db.session.add_all(records)
    db.session.commit()
    return len(records)
