# VégéSuivi Pro

**Plateforme de suivi de la couverture végétale et de collecte de données terrain**  
Direction Régionale de l'Environnement

---

## Présentation

VégéSuivi Pro est une application web modulaire développée en Python/Flask pour le suivi des dynamiques d'occupation des sols et de la couverture végétale de 1990 à 2020. Elle permet :

- La visualisation cartographique de l'évolution du couvert végétal (forêt, savane, agriculture, zones humides, zones urbaines, etc.)
- La collecte et le suivi des données terrain : feux de brousse, sites vulnérables, indicateurs de braconnage, observations & campagnes de collecte
- La génération de rapports formatés (PDF + Excel) : mensuels, trimestriels, semestriels, annuels, thématiques, incidents et campagnes
- La gestion des utilisateurs avec 4 niveaux d'accès : Administrateur, Superviseur, Agent, Lecteur

---

## Technologies utilisées

| Composant        | Technologie                      |
|------------------|----------------------------------|
| Backend          | Python 3.10+, Flask 3.x          |
| Base de données  | SQLite (dev) / PostgreSQL (prod) |
| ORM & Migrations | Flask-SQLAlchemy, Flask-Migrate  |
| Authentification | Flask-Login, Werkzeug            |
| Cartographie     | Leaflet.js 1.9.4, GeoJSON        |
| Graphiques       | Chart.js 4.4                     |
| PDF              | ReportLab 4.x                    |
| Excel            | openpyxl 3.x                     |
| Interface        | Bootstrap 5.3, Bootstrap Icons   |

---

## Installation

### 1. Cloner ou copier le projet

```bash
cd C:\Users\GAMER\Desktop\Steph
# Le dossier vegesuivi_pro est déjà présent
cd vegesuivi_pro
```

### 2. Créer un environnement virtuel Python

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# ou
source .venv/bin/activate     # Linux / macOS
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Initialiser la base de données

```bash
flask init-db
```

Cette commande crée toutes les tables SQLite et peuple la base avec des données de démonstration (4 utilisateurs, 6 feux, 5 sites vulnérables, etc.).

### 5. Lancer l'application

```bash
python run.py
```

L'application sera disponible à l'adresse : **http://127.0.0.1:5000**

---

## Comptes de démonstration

| Rôle          | Email                        | Mot de passe     |
|---------------|------------------------------|------------------|
| Administrateur | admin@vegesuivi.gov          | admin123         |
| Superviseur   | superviseur@vegesuivi.gov    | super123         |
| Agent 1       | agent1@vegesuivi.gov         | agent123         |
| Agent 2       | agent2@vegesuivi.gov         | agent123         |

> ⚠️ **Changer ces mots de passe dès la mise en production.**

---

## Structure du projet

```
vegesuivi_pro/
├── run.py                        # Point d'entrée
├── requirements.txt
├── README.md
└── app/
    ├── __init__.py               # Factory Flask
    ├── config.py                 # Configurations dev/prod/test
    ├── models/                   # Modèles SQLAlchemy
    │   ├── user.py
    │   ├── couverture.py
    │   ├── feux.py
    │   ├── sites_vulnerables.py
    │   ├── braconnage.py
    │   ├── collecte.py
    │   └── rapport.py
    ├── blueprints/               # Modules de l'application
    │   ├── auth/                 # Authentification
    │   ├── dashboard/            # Tableau de bord
    │   ├── cartographie/         # Cartes interactives
    │   ├── collecte/             # Saisie terrain
    │   ├── rapports/             # Génération rapports
    │   ├── admin/                # Administration
    │   └── api/                  # API REST v1
    ├── templates/                # Templates Jinja2
    │   ├── base.html
    │   ├── auth/
    │   ├── dashboard/
    │   ├── cartographie/
    │   ├── collecte/
    │   ├── rapports/
    │   └── admin/
    ├── static/
    │   ├── css/vegesuivi.css
    │   └── js/vegesuivi.js
    └── utils/
        ├── helpers.py
        ├── report_generator.py
        └── seed.py
```

---

## Modules fonctionnels

### Tableau de bord
- Indicateurs clés : feux signalés, sites vulnérables, incidents de braconnage, campagnes terrain
- Graphique d'évolution de la couverture végétale (1990–2020)
- Histogramme mensuel des feux de brousse
- Liste des alertes actives

### Cartographie
- **Carte multicouches** : couverture végétale, feux, sites vulnérables, braconnage, observations
- Basemaps : OpenStreetMap + Esri Satellite
- Filtres par année (1990–2020) et niveau de vulnérabilité
- **Analyse dynamique** : comparaison côte à côte de deux années

### Collecte terrain
- Campagnes de collecte (planification, suivi, rapport de mission)
- Observations terrain avec géolocalisation GPS et mini-carte Leaflet
- Feux de brousse (superficie, intensité, cause, impact faune)
- Sites vulnérables (score 0–100, pressions, espèces clés)
- Indicateurs de braconnage (type, gravité, saisies, N° PV)

### Rapports
- Types : mensuel, trimestriel, semestriel, annuel, thématique, incident, campagne
- Export PDF (mise en page professionnelle A4 via ReportLab)
- Export Excel (multi-onglets via openpyxl)
- Workflow : brouillon → généré → validé → publié

### Administration
- Gestion des utilisateurs (création, modification, activation/désactivation)
- Gestion des classes de couverture (nomenclature)
- Import de données de couverture par fichier CSV

---

## API REST (v1)

| Endpoint                              | Description                          |
|---------------------------------------|--------------------------------------|
| `GET /api/v1/status`                  | Statut de l'API et statistiques      |
| `GET /api/v1/couverture/resume`       | Résumé couverture par année/zone     |
| `GET /api/v1/feux/statistiques`       | Statistiques feux de brousse         |
| `GET /api/v1/braconnage/statistiques` | Statistiques braconnage              |
| `GET /api/v1/sites-vulnerables/liste` | Liste des sites vulnérables          |
| `GET /api/v1/observations/recentes`   | 10 dernières observations terrain    |

---

## Migration vers PostgreSQL (production)

1. Installer `psycopg2-binary`
2. Définir la variable d'environnement `DATABASE_URL` :
   ```
   postgresql://user:password@host:5432/vegesuivi_db
   ```
3. Lancer avec `FLASK_ENV=production python run.py`

---

## Crédits

Développé dans le cadre d'une thèse de doctorat en géographie —  
Dynamiques d'occupation des sols et couverture végétale, 1990–2020.

© Direction Régionale de l'Environnement — Usage interne.
