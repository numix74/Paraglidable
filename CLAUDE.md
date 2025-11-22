# CLAUDE.md - Guide de Développement pour Paraglidable

## Vue d'Ensemble du Projet

**Paraglidable** est un système de prévision des conditions de vol pour le parapente basé sur l'intelligence artificielle. L'application combine des réseaux de neurones (entraînés sur des données historiques de vols et des conditions météorologiques) avec une interface cartographique web pour prédire les conditions favorables au vol dans des zones spécifiques, particulièrement concentrées sur la région des Alpes.

- **Site en production** : https://paraglidable.com
- **Dépôt GitHub** : https://github.com/AntoineMeler/Paraglidable
- **Licence** : GPLv3

---

## Architecture Générale

Le projet se compose de **quatre modules principaux** qui fonctionnent ensemble :

```
Données Météo GFS → Réseau de Neurones → Prédictions → Tiler → Tuiles Carte → Interface Web
```

### Modules

| Module | Répertoire | Technologie | Description |
|--------|------------|-------------|-------------|
| Réseau de Neurones | `/neural_network/` | Python + TensorFlow | Prédit les conditions de vol |
| Tiler | `/tiler/` | C++ + Qt5 | Génère les tuiles cartographiques |
| Application Web | `/www/` | HTML/JS + PHP | Interface utilisateur et API REST |
| Scripts | `/scripts/` | Python + Bash | Traitement des données et maintenance |

---

## Structure des Répertoires

```
/Paraglidable/
├── docker/                          # Configuration Docker
│   ├── Dockerfile                   # Image de développement
│   └── python_requirements.txt      # Dépendances Python
│
├── neural_network/                  # Moteur de prédiction IA
│   ├── README.md                    # Documentation technique détaillée
│   ├── train.py                     # Script d'entraînement
│   ├── forecast.py                  # Génération des prévisions (10 jours)
│   ├── generate_anl_tiles.py        # Tuiles d'analyse (données passées)
│   ├── plot_training.py             # Visualisation de l'entraînement
│   ├── bin/
│   │   ├── models/                  # Modèles entraînés
│   │   │   └── CLASSIFICATION_1.0.0/
│   │   │       └── weights/         # Poids des réseaux
│   │   └── data/                    # Données d'entraînement (pickle)
│   ├── inc/                         # Modules Python
│   │   ├── model.py                 # Architecture du réseau de neurones
│   │   ├── dataset.py               # Chargement des données (25KB)
│   │   ├── trained_model.py         # Gestion des modèles entraînés
│   │   ├── predict.py               # Moteur d'inférence
│   │   ├── forecast_data.py         # Gestion données météo
│   │   ├── grib_reader.py           # Lecture fichiers GRIB (pygrib)
│   │   ├── grib.py                  # Utilitaires GRIB
│   │   ├── grid_latlon.py           # Opérations grille géographique
│   │   ├── tiles_maths.py           # Mathématiques des tuiles
│   │   ├── utils.py                 # Utilitaires généraux
│   │   ├── verbose.py               # Journalisation
│   │   └── bin_obj.py               # Sérialisation pickle
│   └── docs/
│       ├── documentation.ipynb      # Documentation interactive Jupyter
│       └── imgs/                    # Images et diagrammes
│
├── tiler/                           # Génération des tuiles (C++/Qt)
│   ├── README.md                    # Documentation du tiler
│   ├── Tiler/                       # Code source
│   │   ├── Tiler.pro                # Fichier projet Qt
│   │   ├── main.cpp                 # Logique principale (51KB)
│   │   ├── arguments.cpp            # Parsing des arguments
│   │   ├── elevation.cpp            # Traitement des élévations
│   │   ├── flights.cpp              # Visualisation des vols
│   │   └── tilesmath.cpp            # Calculs de coordonnées
│   ├── data/                        # Données pour génération
│   │   ├── Europe_africa_med_red.geo.json  # Frontières géographiques
│   │   └── skippedTiles.txt         # Tuiles à ignorer
│   └── _cache/                      # Cache des tuiles
│
├── www/                             # Interface web et API
│   ├── index.html                   # Application web principale (110KB)
│   ├── mobile.html                  # Version mobile optimisée
│   ├── mobileAndroid.html           # Interface app Android
│   ├── css/
│   │   ├── paraglidable.css         # Feuille de style (26KB)
│   │   ├── paraglidable.sass        # Source SASS (36KB)
│   │   ├── paraglidable_mobile.css  # Styles mobile (11KB)
│   │   └── paraglidable_mobile.sass
│   ├── js/
│   │   ├── paraglidable_lib.js      # Utilitaires partagés (7KB)
│   │   ├── paraglidable_mobile.js   # Logique mobile (20KB)
│   │   └── third_parties/           # Bibliothèques externes
│   │       ├── leaflet/             # Bibliothèque cartographique
│   │       ├── jquery-3.3.1.min.js
│   │       ├── moment-with-locales.min.js
│   │       ├── autocomplete.js
│   │       ├── tinycolor-min.js
│   │       └── prism/               # Coloration syntaxique
│   ├── apps/
│   │   ├── search.php               # Recherche de lieux
│   │   ├── gtag.php                 # Google Analytics
│   │   ├── sendMessage.php          # Formulaire de contact
│   │   └── api/
│   │       ├── get.php              # Point d'entrée API principal
│   │       ├── getAnalysisData.php  # Données d'analyse historique
│   │       ├── generateApiKey.php   # Génération clé API + email
│   │       ├── bdd.php              # Connexion base de données
│   │       ├── math.php             # Maths coordonnées tuiles
│   │       └── banned.txt.php       # Liste noire IP
│   ├── data/
│   │   ├── tiles/                   # Tuiles de prévision générées
│   │   └── elevation/               # Tuiles d'élévation
│   └── imgs/                        # Ressources visuelles
│       ├── logo/
│       ├── icons/
│       ├── favicon/
│       ├── legend/
│       └── vignettes/
│
├── scripts/                         # Scripts utilitaires
│   ├── download_data.py             # Télécharge données entraînement
│   ├── download_GFS.py              # Télécharge fichiers météo GRIB
│   ├── download_elevation_tiles.py  # Télécharge données d'élévation
│   ├── download_background_tiles.py # Télécharge fonds de carte
│   ├── build_tiler.sh               # Compile le tiler C++
│   ├── start_server.sh              # Démarre Apache
│   ├── start_jupyter.sh             # Démarre Jupyter
│   ├── update_nn_README.py          # Met à jour documentation NN
│   ├── cron_tasks/
│   │   ├── update_forecasts.sh      # Mise à jour quotidienne
│   │   ├── check_server.py          # Vérifications de santé
│   │   ├── clean.py                 # Nettoyage
│   │   ├── set_current_commit.py    # Suivi de version
│   │   ├── crontab.txt              # Planning cron
│   │   └── renew_certificates.sh    # Renouvellement SSL
│   └── inc/
│       └── google_drive_downloader.py
│
├── README.md                        # Présentation du projet
├── privacy_policy.md                # Politique de confidentialité
└── LICENSE                          # Licence GPLv3
```

---

## Technologies et Frameworks

### Frontend
| Technologie | Version | Usage |
|-------------|---------|-------|
| HTML5 | - | Structure de l'application |
| Leaflet.js | 1.x | Bibliothèque cartographique interactive |
| JavaScript | ES6 | Logique client |
| jQuery | 3.3.1 | Manipulation DOM |
| Moment.js | - | Gestion dates/heures |
| TinyColor | - | Manipulation des couleurs |
| SASS | - | Préprocesseur CSS |

### Backend
| Technologie | Version | Usage |
|-------------|---------|-------|
| PHP | 7+ | API REST et traitement serveur |
| Apache | 2.x | Serveur HTTP |
| MySQL | 5.7+ | Base de données (clés API) |

### Machine Learning
| Technologie | Version | Usage |
|-------------|---------|-------|
| Python | 3.x | Langage principal ML |
| TensorFlow | 2.0.0 | Framework d'apprentissage profond |
| NumPy | 1.17.2 | Calcul numérique |
| Pandas | 0.25.3 | Manipulation de données |
| Matplotlib | 3.1.2 | Visualisation |
| Basemap | 1.2.1 | Cartographie scientifique |
| PyGrib | 2.0.4 | Lecture fichiers météo GRIB |
| Jupyter | 1.0.0 | Documentation interactive |

### Génération de Tuiles
| Technologie | Version | Usage |
|-------------|---------|-------|
| C++ | C++11 | Performances |
| Qt | 5.x | Framework multiplateforme |

### DevOps
| Technologie | Usage |
|-------------|-------|
| Docker | Environnement de développement |
| Bash | Automatisation |
| Cron | Tâches planifiées |

---

## Installation et Configuration

### Prérequis
- Docker installé sur la machine
- Git pour cloner le dépôt
- ~1GB d'espace disque pour les données

### Installation Complète

```bash
# 1. Cloner le dépôt
git clone https://github.com/AntoineMeler/Paraglidable.git
cd Paraglidable

# 2. Construire le conteneur Docker
docker build -t paraglidable docker/
docker run -it -p 8001:80 -p 8888:8888 \
  -v $(pwd):/workspaces/Paraglidable paraglidable

# 3. Télécharger les données (configuration initiale)
cd /workspaces/Paraglidable/scripts/
python download_data.py              # ~200MB données d'entraînement
python download_elevation_tiles.py   # ~260MB élévation
python download_background_tiles.py  # ~180MB (optionnel)

# 4. Compiler le tiler C++
sh build_tiler.sh

# 5. (Optionnel) Télécharger les données météo brutes
python download_GFS.py
```

---

## Commandes de Développement

### Entraînement du Réseau de Neurones

```bash
cd /workspaces/Paraglidable/neural_network/

# Entraîner les modèles CELLS et SPOTS
python train.py

# Visualiser l'entraînement
python plot_training.py
```

### Génération des Prévisions

```bash
cd /workspaces/Paraglidable/neural_network/

# Générer les prévisions 10 jours
python forecast.py

# Générer les tuiles d'analyse (données passées)
python generate_anl_tiles.py
```

### Serveur de Développement

```bash
# Démarrer Apache (port 8001)
sh /workspaces/Paraglidable/scripts/start_server.sh

# Démarrer Jupyter (port 8888)
sh /workspaces/Paraglidable/scripts/start_jupyter.sh

# Accéder à l'application
# http://localhost:8001/
```

### Compilation du Tiler

```bash
cd /workspaces/Paraglidable/scripts/
sh build_tiler.sh

# Exécuter le tiler manuellement
cd /workspaces/Paraglidable/tiler/Tiler/
./Tiler --help
```

---

## Architecture du Réseau de Neurones

### Approche Hybride

Le modèle utilise une **approche hybride** combinant plusieurs blocs spécialisés :

1. **Population Block** : Modélise la probabilité qu'un pilote décide de voler
2. **Wind Block** : Quantifie le vent en 8 directions, applique le facteur de montagnosité
3. **Flyability Block** : Réseau de neurones prédisant les conditions favorables
4. **Crossability Block** : Prédit le potentiel de vol cross-country
5. **Indicateurs** : Sous-modèles vent-flyabilité et humidité-flyabilité

### Données d'Entraînement

| Métrique | Valeur |
|----------|--------|
| Points de décollage | ~9 966 spots, 8 342 fusionnés |
| Nombre de vols | 1M+ vols |
| Données météo | Analyse GFS 1°x1°x100hPa |
| Heures UTC | 06:00, 12:00, 18:00 quotidien |
| Zone d'entraînement | Lat 31.95°-66.5°, Lon -10.55°-33.75° |
| Période historique | 9.6 ans (3 281 jours) |
| Paramètres météo | 195 paramètres sur 5 niveaux d'altitude |

### Paramètres Météorologiques Utilisés

- Vitesse verticale (1000-200 hPa)
- Hauteur géopotentielle (1000-200 hPa)
- Vorticité absolue (1000-200 hPa)
- Température (1000-200 hPa)
- Humidité relative (1000-200 hPa)
- Composantes vent U/V (1000-200 hPa)
- Eau précipitable, Eau nuageuse

### Processus d'Entraînement

1. **Initialisations multiples** : 20 entraînements avec sélection du meilleur
2. **Arrêt précoce** : Surveillance de la perte de validation
3. **Affinage** : Ré-entraînement sur l'ensemble complet
4. **Schedule du learning rate** : Décroissance exponentielle
5. **Poids séparés** : Pour chaque cellule et spot

---

## API REST

### Point d'Entrée Principal
`https://paraglidable.com/apps/api/get.php`

### Endpoints Disponibles

#### 1. Prédiction de Tuile (`getPrediction()`)
Obtient les prédictions de vol pour une tuile cartographique spécifique.

**Paramètres** :
| Paramètre | Type | Description |
|-----------|------|-------------|
| `date` | string | Date de prévision (YYYY-MM-DD) |
| `zoom` | int | Niveau de zoom (5-9) |
| `tx` | int | Coordonnée X de la tuile |
| `ty` | int | Coordonnée Y de la tuile |
| `x` | int | Pixel X dans la tuile (0-255) |
| `y` | int | Pixel Y dans la tuile (0-255) |

**Réponse** : Tableau de valeurs de prédiction (0.0-1.0 pour la flyabilité)

#### 2. Prédiction de Spot (`getSpotPrediction()`)
Obtient la flyabilité pour des points de décollage spécifiques.

**Paramètres** :
| Paramètre | Type | Description |
|-----------|------|-------------|
| `date` | string | Date de prévision |
| `spotId` | string | Identifiant du spot |

**Réponse** : Objet JSON avec propriété `flyability`

#### 3. Données d'Élévation (`getElevation()`)
Obtient l'élévation du terrain pour le rendu cartographique.

**Paramètres** : Mêmes coordonnées de tuile (zoom, tx, ty, x, y)

**Réponse** : Valeur d'élévation en mètres

#### 4. Génération de Clé API (`generateApiKey.php`)
Génère des clés API pour les utilisateurs.

**Paramètres** :
| Paramètre | Type | Description |
|-----------|------|-------------|
| `email` | string | Email utilisateur (validé) |
| `lat_0`, `lon_0`, `name_0` | mixed | Liste des emplacements |

---

## Base de Données

### Schéma MySQL (inféré du code)

```sql
-- Base de données : paraglidable

-- Table : Accounts (utilisateurs API)
CREATE TABLE Accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table : ApiKeys (clés d'accès API)
CREATE TABLE ApiKeys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account INT NOT NULL,
    apiKey VARCHAR(32) UNIQUE NOT NULL,
    latLonName LONGTEXT,  -- Tableau PHP sérialisé des emplacements
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account) REFERENCES Accounts(id)
);
```

### Configuration de Connexion
Fichier : `/www/apps/api/bdd.php`
- **Hôte** : `localhost`
- **Utilisateur** : `root`
- **Mot de passe** : `paraglidable`
- **Base** : `paraglidable`

---

## Système de Tuiles Cartographiques

### Format des Tuiles
- **Taille** : 256×256 pixels
- **Niveaux de zoom** : 5-9
- **Format** : PNG avec transparence
- **Projection** : Web Mercator (EPSG:3857)

### Calcul des Coordonnées
Le système utilise les fonctions définies dans `/www/apps/api/math.php` :

```
Lat/Lon → Mètres → Pixels → Coordonnées tuile + offset pixel
```

### Structure des Fichiers de Tuiles

```
/www/data/tiles/
├── [YYYY-MM-DD]/
│   ├── 256/
│   │   ├── 5/                       # Zoom level 5
│   │   │   ├── [tx]/
│   │   │   │   ├── [ty].data        # Données binaires
│   │   │   │   └── [ty]_transpa.png # Image PNG
│   │   ├── 6/
│   │   ├── 7/
│   │   ├── 8/
│   │   └── 9/
│   └── spots.json                   # GeoJSON des spots
```

---

## Sécurité

### Mesures Implémentées

1. **Liste Noire IP** (`banned.txt.php`)
   - Suit les requêtes suspectes
   - Bannissement permanent des IP
   - Déclencheurs : paramètres invalides, mauvais référent, cookies manquants

2. **Validation du Référent**
   - Autorise uniquement : `paraglidable.com`, `fufu-map.com`
   - Retourne des données factices pour les autres

3. **Vérification des Cookies**
   - Requiert le cookie `view=`
   - Empêche le scraping automatisé

4. **Limitation de Débit** (implicite)
   - Blocage basé sur l'IP après activité suspecte

---

## Tâches Automatisées (Cron)

### Configuration (`/scripts/cron_tasks/crontab.txt`)

| Tâche | Script | Description |
|-------|--------|-------------|
| Mise à jour quotidienne | `update_forecasts.sh` | Génère nouvelles prévisions 10 jours |
| Vérification santé | `check_server.py` | Vérifie disponibilité services |
| Nettoyage | `clean.py` | Supprime anciennes données |
| Renouvellement SSL | `renew_certificates.sh` | Met à jour certificats HTTPS |
| Suivi version | `set_current_commit.py` | Enregistre commit actuel |

---

## Conventions de Code

### Python (Réseau de Neurones)
- **Style** : PEP 8
- **Docstrings** : Format Google
- **Nommage** : snake_case pour fonctions et variables
- **Imports** : Groupés (stdlib, third-party, local)

### C++ (Tiler)
- **Style** : Qt conventions
- **Nommage** : camelCase pour fonctions, PascalCase pour classes
- **Headers** : Guards avec `#ifndef`

### PHP (API)
- **Style** : PSR-12
- **Nommage** : camelCase pour fonctions
- **Variables** : $camelCase

### JavaScript (Frontend)
- **Style** : ES6+
- **Nommage** : camelCase
- **Modules** : Fonctions globales dans `paraglidable_lib.js`

### CSS/SASS
- **Style** : BEM-like
- **Variables** : Définies en haut des fichiers SASS
- **Responsive** : Mobile-first

---

## Flux de Travail de Développement

### Développement Local

1. **Modification du réseau de neurones**
   ```bash
   cd neural_network/
   # Modifier inc/model.py ou train.py
   python train.py
   python forecast.py
   ```

2. **Modification du tiler**
   ```bash
   cd tiler/Tiler/
   # Modifier main.cpp
   cd ../../scripts/
   sh build_tiler.sh
   ```

3. **Modification de l'interface web**
   ```bash
   cd www/
   # Modifier index.html, css/, js/
   # Recharger le navigateur
   ```

4. **Modification de l'API**
   ```bash
   cd www/apps/api/
   # Modifier get.php ou autres fichiers PHP
   # Tester avec curl ou Postman
   ```

### Tests

Le projet n'a pas de suite de tests automatisés formelle. La validation se fait par :

1. **Validation de l'entraînement** : Surveillance de la perte de validation
2. **Mode analyse** : Test sur des dates passées
3. **Tests manuels** : Vérification visuelle des tuiles générées

---

## Sources de Données Externes

### Données Météorologiques
- **Source** : GFS (Global Forecast System) de la NOAA
- **Résolution** : 1° (entraînement), 0.25° (prévision)
- **Format** : GRIB
- **Accès** : Serveur NOAA NOMADS (gratuit)

### Données de Vols
- **Source** : Base de données de vols parapente (non documentée publiquement)
- **Contenu** : Lieu de décollage, atterrissage, score XC, altitude
- **Stockage** : Google Drive (accès privé)

### Données d'Élévation
- **Source** : Probablement SRTM ou OpenElevation
- **Format** : Tuiles raster binaires
- **Usage** : Amélioration visuelle et analyse du terrain

---

## Limitations Connues

| Limitation | Description |
|------------|-------------|
| Zone géographique | Concentré sur les Alpes (pas de support fuseaux horaires) |
| Confidentialité | Pas de tracking de localisation (tout côté client) |
| Précision prévisions | Dépend de la qualité du modèle GFS |
| Fréquence mise à jour | Quotidienne (prévisions 10 jours) |
| Temps de calcul | 20 initialisations + affinage = temps considérable |
| Base de données | Credentials codés en dur (non sécurisé production) |
| Liste noire IP | Permanente (pas de déblocage automatique) |

---

## Fichiers Clés pour Comprendre le Projet

### Priorité 1 (Logique Principale)
| Fichier | Description |
|---------|-------------|
| `/neural_network/README.md` | Documentation technique du NN |
| `/neural_network/train.py` | Processus d'entraînement |
| `/neural_network/forecast.py` | Pipeline de prévision |
| `/neural_network/inc/model.py` | Définition de l'architecture |
| `/neural_network/inc/dataset.py` | Chargement des données |

### Priorité 2 (Intégration)
| Fichier | Description |
|---------|-------------|
| `/tiler/Tiler/main.cpp` | Rendu des tuiles |
| `/www/js/paraglidable_lib.js` | Logique frontend |
| `/www/apps/api/get.php` | Implémentation API |
| `/www/index.html` | Interface principale |

### Priorité 3 (Opérations)
| Fichier | Description |
|---------|-------------|
| `/scripts/download_data.py` | Acquisition des données |
| `/scripts/cron_tasks/` | Automatisation |
| `/docker/Dockerfile` | Configuration environnement |

---

## Dépannage Courant

### Problème : Erreur de compilation du tiler
```bash
# Vérifier que Qt5 est installé
qmake --version
# Nettoyer et recompiler
cd tiler/Tiler/
make clean
qmake Tiler.pro
make
```

### Problème : Erreur TensorFlow
```bash
# Vérifier la version
python -c "import tensorflow as tf; print(tf.__version__)"
# Doit être 2.0.0
```

### Problème : Fichiers GRIB non trouvés
```bash
# Télécharger les données météo
cd scripts/
python download_GFS.py
```

### Problème : Tuiles non générées
```bash
# Vérifier que le forecast a été exécuté
ls -la www/data/tiles/
# Exécuter le forecast si nécessaire
cd neural_network/
python forecast.py
```

---

## Contact et Contribution

- **Issues** : https://github.com/AntoineMeler/Paraglidable/issues
- **Auteur** : Antoine Meler
- **Licence** : GPLv3 - Contributions bienvenues sous la même licence

---

## Historique des Versions

Le projet utilise Git pour le versionnement. Les commits récents peuvent être consultés avec :
```bash
git log --oneline -20
```

---

*Dernière mise à jour : Novembre 2025*
