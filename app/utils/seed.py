"""
Données de démonstration - Seed de la base de données
"""

from datetime import date, datetime
from app import db
from app.models import (
    User, ClasseCouverture, Couverture,
    FeuxBrousse, SiteVulnerable, IndicateurBraconnage,
    CampagneCollecte, ObservationTerrain
)


def seed_database():
    """Initialise la base avec des données d'exemple réalistes"""

    # ──── Utilisateurs ────
    # Compte de test simplifié (email: admin, mdp: admin123)
    admin_test = User(nom='Admin Test', email='admin',
                      role='admin', structure='Direction Régionale de l\'Environnement', actif=True)
    admin_test.set_password('admin123')

    admin = User(nom='Dr. Administrateur DRE', email='admin@dre.gov',
                 role='admin', structure='Direction Régionale de l\'Environnement')
    admin.set_password('admin123')

    superviseur = User(nom='Chef de Service Suivi', email='superviseur@dre.gov',
                       role='superviseur', structure='Service de Suivi Écologique')
    superviseur.set_password('super123')

    agent1 = User(nom='Jean-Pierre Kouamé', email='agent1@dre.gov',
                  role='agent', structure='Brigade de Surveillance')
    agent1.set_password('agent123')

    agent2 = User(nom='Amina Traoré', email='agent2@dre.gov',
                  role='agent', structure='Brigade de Surveillance')
    agent2.set_password('agent123')

    db.session.add_all([admin_test, admin, superviseur, agent1, agent2])
    db.session.flush()

    # ──── Classes de couverture ────
    classes_data = [
        ('FFG', 'Forêt galerie', '#1a5c1a', 'Forêt', 0),
        ('FSA', 'Forêt sèche arbustive', '#2ecc71', 'Forêt', 1),
        ('SAT', 'Savane arborée / arbustive', '#f39c12', 'Prairie', 2),
        ('SHE', 'Savane herbeuse', '#f7dc6f', 'Prairie', 3),
        ('AGR', 'Zone agricole / cultures', '#e67e22', 'Agriculture', 4),
        ('ZHU', 'Zone humide / marécage', '#2980b9', 'Eau', 5),
        ('EAU', 'Plans d\'eau / cours d\'eau', '#3498db', 'Eau', 6),
        ('URB', 'Zone urbaine / bâti', '#95a5a6', 'Urbain', 7),
        ('SOL', 'Sol nu / dégradé / latérite', '#c0392b', 'Autre', 8),
        ('REB', 'Reboisement / plantation', '#27ae60', 'Forêt', 9),
    ]
    classes = {}
    for code, label, couleur, cat, ordre in classes_data:
        c = ClasseCouverture(code=code, label=label, couleur_hex=couleur,
                             categorie=cat, ordre_affichage=ordre, actif=True)
        db.session.add(c)
        db.session.flush()
        classes[code] = c

    # ──── Données de couverture 1990-2020 ────
    couverture_data = {
        # (code, zone, superficies par année)
        'FFG': [('Zone Nord', 45230, 42100, 38900, 35200, 31000, 27500, 24800),
                ('Zone Sud', 32100, 30200, 28500, 26800, 25000, 23200, 21500)],
        'FSA': [('Zone Nord', 38500, 36200, 33800, 30500, 27200, 24000, 21000),
                ('Zone Sud', 28400, 26800, 25100, 23500, 21900, 20300, 18700)],
        'SAT': [('Zone Nord', 52000, 54500, 57200, 60100, 63200, 66500, 69800),
                ('Zone Sud', 42000, 44200, 46500, 48900, 51400, 53900, 56500)],
        'SHE': [('Zone Nord', 18000, 19200, 20600, 22100, 23700, 25400, 27200),
                ('Zone Sud', 15500, 16400, 17400, 18500, 19600, 20800, 22100)],
        'AGR': [('Zone Nord', 22000, 25300, 28900, 33100, 38000, 43500, 49800),
                ('Zone Sud', 18500, 21200, 24300, 27900, 32000, 36800, 42200)],
        'ZHU': [('Zone Nord', 8500, 8200, 7900, 7500, 7100, 6800, 6400),
                ('Zone Sud', 6800, 6600, 6300, 6000, 5700, 5400, 5100)],
        'EAU': [('Zone Nord', 5200, 5100, 5000, 4900, 4700, 4600, 4400),
                ('Zone Sud', 4100, 4000, 3900, 3800, 3700, 3600, 3500)],
        'URB': [('Zone Nord', 3200, 3700, 4400, 5200, 6200, 7400, 8900),
                ('Zone Sud', 2600, 3000, 3500, 4100, 4800, 5600, 6600)],
        'SOL': [('Zone Nord', 4800, 5500, 6300, 7200, 8300, 9500, 11000),
                ('Zone Sud', 3800, 4400, 5100, 5900, 6800, 7900, 9100)],
        'REB': [('Zone Nord', 1200, 1400, 1700, 2100, 2700, 3500, 4500),
                ('Zone Sud', 900, 1100, 1300, 1600, 2000, 2600, 3300)],
    }
    annees = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
    for code, zones in couverture_data.items():
        for zone_nom, *superficies in zones:
            prev = None
            for annee, sup in zip(annees, superficies):
                variation = (sup - prev) if prev else 0
                taux = round((variation / prev * 100), 2) if prev else 0
                c = Couverture(
                    annee=annee,
                    classe_id=classes[code].id,
                    zone=zone_nom,
                    superficie_ha=float(sup),
                    superficie_km2=round(sup / 100, 2),
                    variation_ha=float(variation),
                    taux_variation=taux,
                    source='Landsat TM/ETM+/OLI' if annee <= 2015 else 'Sentinel-2',
                    methode='Classification supervisée par télédétection',
                    precision_pct=85.0 + (annee - 1990) * 0.3,
                )
                db.session.add(c)
                prev = sup

    # ──── Feux de brousse ────
    feux_data = [
        ('FEU-2023-001', date(2023, 1, 15), date(2023, 1, 17), 'Zone Nord',
         'Kouroumba', 9.45, -2.12, 450.5, 'Fort', 'Savane arbustive',
         'Pastorale', 'Moyen', 'éteint'),
        ('FEU-2023-002', date(2023, 2, 8), None, 'Zone Sud',
         'Diébougou', 10.85, -3.25, 215.0, 'Moyen', 'Savane herbeuse',
         'Agricole', 'Faible', 'éteint'),
        ('FEU-2023-003', date(2023, 3, 22), date(2023, 3, 24), 'Zone Nord',
         'Tenkodogo', 11.78, -0.36, 880.0, 'Très fort', 'Forêt galerie',
         'Criminel', 'Sévère', 'éteint'),
        ('FEU-2024-001', date(2024, 1, 5), None, 'Zone Centrale',
         'Manga', 11.65, -1.07, 320.0, 'Fort', 'Savane arborée',
         'Inconnu', 'Moyen', 'éteint'),
        ('FEU-2024-002', date(2024, 2, 14), None, 'Zone Nord',
         'Bogandé', 12.98, 0.14, 560.0, 'Fort', 'Savane herbeuse',
         'Pastorale', 'Faible', 'éteint'),
        ('FEU-2024-003', date(2024, 3, 1), None, 'Zone Sud',
         'Gaoua', 10.32, -3.17, 1250.0, 'Très fort', 'Forêt sèche',
         'Criminel', 'Sévère', 'surveille'),
    ]
    for ref, d_debut, d_fin, zone, village, lat, lon, sup, intens, veg, cause, impact, statut in feux_data:
        f = FeuxBrousse(
            reference=ref, date_debut=d_debut, date_fin=d_fin,
            zone=zone, village_proche=village,
            latitude=lat, longitude=lon,
            superficie_brulee_ha=sup, intensite=intens,
            type_vegetation=veg, cause=cause,
            impact_faune=impact, statut=statut,
            signale_par='Équipe de surveillance', created_by=agent1.id
        )
        db.session.add(f)

    # ──── Sites vulnérables ────
    sites_data = [
        ('SV-001', 'Forêt Classée de Nazinon', date(2020, 6, 1),
         'Zone Nord', 'Koudougou', 12.25, -2.36,
         'Forêt classée', 18500.0, 'Critique', 92,
         'Défrichement,Coupe illégale,Pâturage excessif', 'Mensuelle'),
        ('SV-002', 'Corridor faunique Sahel', date(2021, 3, 15),
         'Zone Nord', 'Dori', 14.03, -0.03,
         'Corridor faunique', 45000.0, 'Élevé', 75,
         'Mines artisanales,Braconnage,Urbanisation', 'Trimestrielle'),
        ('SV-003', 'Bas-fond de Gampela', date(2019, 11, 20),
         'Zone Centrale', 'Ouagadougou', 12.35, -1.22,
         'Zone humide', 3200.0, 'Critique', 88,
         'Pollution,Drainage agricole,Empiètement', 'Mensuelle'),
        ('SV-004', 'Reboisement Tenkodogo', date(2022, 5, 5),
         'Zone Centre-Est', 'Tenkodogo', 11.78, -0.36,
         'Reboisement', 850.0, 'Moyen', 45,
         'Pâturage excessif,Feux non contrôlés', 'Trimestrielle'),
        ('SV-005', 'Site Ramsar de Oursi', date(2018, 8, 12),
         'Zone Sahélienne', 'Gorom-Gorom', 14.44, -0.23,
         'Site Ramsar', 8900.0, 'Élevé', 78,
         'Assèchement,Pression agricole,Surpâturage', 'Mensuelle'),
    ]
    for ref, nom, d_id, zone, localite, lat, lon, type_s, sup, niveau, score, pressions, freq in sites_data:
        s = SiteVulnerable(
            reference=ref, nom=nom, date_identification=d_id,
            zone=zone, localite=localite,
            latitude=lat, longitude=lon,
            type_site=type_s, superficie_ha=sup,
            niveau_vulnerabilite=niveau, score_vulnerabilite=score,
            pressions=pressions,
            valeur_ecologique='Très haute',
            frequence_surveillance=freq,
            statut='actif', created_by=admin.id
        )
        db.session.add(s)

    # ──── Indicateurs de braconnage ────
    braconnage_data = [
        ('BR-2024-001', date(2024, 1, 20), 'Zone Nord', 'Bogandé',
         13.97, 0.14, 'Piège/Collet', 'Piège à câble — 12 collets relevés',
         'Phacochères,Gazelles', 12, 'Grave', True),
        ('BR-2024-002', date(2024, 2, 5), 'Zone Sud', 'Gaoua',
         10.32, -3.17, 'Camp de braconnier', 'Camp abandonné avec restes animaux',
         'Buffles,Hippotragues', 1, 'Critique', False),
        ('BR-2024-003', date(2024, 3, 10), 'Zone Nord', 'Fada N\'Gourma',
         12.06, 0.36, 'Cadavre animal', 'Carcasse d\'hippotrague',
         'Hippotrague', 1, 'Grave', False),
        ('BR-2023-001', date(2023, 11, 15), 'Zone Centrale', 'Kaya',
         13.08, -1.08, 'Coupe illégale', 'Zone de coupe non autorisée — 3 ha',
         'Karité,Neem', 1, 'Moyen', True),
        ('BR-2023-002', date(2023, 12, 22), 'Zone Sud', 'Diébougou',
         10.96, -3.26, 'Trafic espèce', 'Saisie de 8 reptiles en cage',
         'Varans,Pythons', 8, 'Grave', True),
    ]
    for ref, d_c, zone, loc, lat, lon, type_ind, desc, especes, nb, gravite, saisie in braconnage_data:
        b = IndicateurBraconnage(
            reference=ref, date_constat=d_c, zone=zone, localite=loc,
            latitude=lat, longitude=lon,
            type_indicateur=type_ind, description=desc,
            especes_concernees=especes, nombre_indices=nb,
            niveau_gravite=gravite, activite_recente=True,
            saisies_effectuees=saisie,
            alerte_emise=True,
            source_info='Patrouille', statut='en_cours',
            created_by=agent1.id
        )
        db.session.add(b)

    # ──── Campagne de collecte ────
    camp = CampagneCollecte(
        reference='CAM-2024-001',
        nom='Inventaire végétation Zone Nord - Q1 2024',
        objectif='Mise à jour de l\'état de la couverture végétale en Zone Nord',
        date_debut=date(2024, 1, 15),
        date_fin_prevue=date(2024, 2, 28),
        zone_couverte='Zone Nord - Secteur Sahélien',
        responsable_id=superviseur.id,
        statut='termine',
        protocole='Transects + points GPS + photos géoréférencées',
        materiels='GPS Garmin, Tablettes, Fiches terrain'
    )
    db.session.add(camp)
    db.session.flush()

    # Observations terrain
    obs_data = [
        (12.25, -2.36, 'Zone Nord', 'vegetation', 'Dégradation forêt galerie',
         'Forêt galerie très dégradée sur 500m, souches fraîches visibles.', 'Très dégradé', 'Alerte'),
        (13.97, 0.14, 'Zone Nord', 'faune', 'Observation gazelles dama',
         'Groupe de 8 gazelles dama observées en pâturage.', 'Bon', 'Normal'),
        (14.03, -0.03, 'Zone Sahélienne', 'braconnage', 'Collets relevés en patrouille',
         '4 collets métalliques retrouvés, désactivés sur place.', None, 'Urgence'),
        (11.78, -0.36, 'Zone Centre-Est', 'feu', 'Traces de feux récents',
         'Savane sur 200 ha brûlée récemment, recouvrement en cours.', 'Dégradé', 'Attention'),
        (12.35, -1.22, 'Zone Centrale', 'eau', 'Niveau bas-fond Gampela',
         'Niveau d\'eau en baisse de 40 cm par rapport à l\'année précédente.', 'Moyen', 'Attention'),
    ]
    for lat, lon, zone, cat, titre, desc, etat, alerte in obs_data:
        o = ObservationTerrain(
            reference=f'OBS-2024-{obs_data.index((lat, lon, zone, cat, titre, desc, etat, alerte)) + 1:03d}',
            campagne_id=camp.id,
            agent_id=agent1.id,
            date_observation=datetime(2024, 1, 20, 9, 30),
            latitude=lat, longitude=lon, zone=zone,
            categorie=cat, titre=titre, description=desc,
            etat_general=etat, niveau_alerte=alerte,
            validee=True, valide_par=superviseur.id,
            date_validation=datetime(2024, 1, 25)
        )
        db.session.add(o)

    db.session.commit()
    print("Base de données peuplée avec succès.")
    print("Comptes créés :")
    print("  admin@dre.gov / admin123")
    print("  superviseur@dre.gov / super123")
    print("  agent1@dre.gov / agent123")
