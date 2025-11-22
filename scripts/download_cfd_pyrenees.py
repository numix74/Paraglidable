#!/usr/bin/env python3
# coding: utf-8
"""
Script de téléchargement des vols CFD FFVL pour les Pyrénées
============================================================

Ce script :
1. Télécharge les vols via l'API wxc_export (par mois)
2. Parse le XML et extrait les métadonnées
3. Télécharge les fichiers IGC
4. Parse les IGC pour extraire les données détaillées
5. Filtre par zone géographique (Pyrénées)
6. Sauvegarde en pickle/CSV

Zone Pyrénées (France + Espagne) : 41.5° - 44.0° N, -2.0° - 4.0° E

Usage:
    python download_cfd_pyrenees.py --start-year 2015 --end-year 2024
    python download_cfd_pyrenees.py --download-igc  # Télécharge aussi les fichiers IGC
"""

import os
import sys
import time
import argparse
import requests
import pickle
import csv
import hashlib
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# Zone géographique Pyrénées (France + Espagne)
# - Nord : Piémont français (Toulouse, Pau, Perpignan)
# - Sud : Versant espagnol (Aragon, Catalogne, Navarre)
# - Spots espagnols inclus : Àger, Organyà, Castejón de Sos, Liri, etc.
BBOX_PYRENEES = {
    'min_lat': 41.5,  # Versant espagnol (Catalogne/Aragon)
    'max_lat': 44.0,  # Piémont français
    'min_lon': -2.0,  # Pays Basque
    'max_lon': 4.0    # Méditerranée
}

# Répertoires
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "neural_network" / "bin" / "data_pyrenees"
IGC_DIR = DATA_DIR / "igc_files"
CACHE_DIR = DATA_DIR / "cache"

# API CFD
CFD_API_URL = "https://parapente.ffvl.fr/wxc_export"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Rate limiting
REQUEST_DELAY = 1.0  # secondes entre chaque requête
IGC_DOWNLOAD_DELAY = 0.5  # secondes entre chaque téléchargement IGC


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FlightMetadata:
    """Métadonnées d'un vol extraites de l'API CFD"""
    flight_id: str
    civl_id: Optional[str]
    pilot_first_name: str
    pilot_last_name: str
    pilot_nation: str
    pilot_gender: str
    igc_url: str
    igc_md5: str
    takeoff_timestamp: int
    landing_timestamp: int
    takeoff_name: str
    takeoff_country: str
    glider: str
    glider_cat: str
    flight_url: str
    nac_flight_id: str

    @property
    def takeoff_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.takeoff_timestamp)

    @property
    def landing_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.landing_timestamp)

    @property
    def duration_hours(self) -> float:
        return (self.landing_timestamp - self.takeoff_timestamp) / 3600.0


@dataclass
class IGCData:
    """Données extraites d'un fichier IGC"""
    # Position décollage
    takeoff_lat: float
    takeoff_lon: float
    takeoff_alt: int

    # Position atterrissage
    landing_lat: float
    landing_lon: float
    landing_alt: int

    # Performance
    max_altitude: int
    min_altitude: int
    altitude_gain: int  # max_alt - takeoff_alt

    # Vario
    mean_positive_vario: float  # m/s
    max_vario: float
    min_vario: float

    # Vitesse
    mean_ground_speed: float  # km/h
    max_ground_speed: float

    # Thermiques
    thermal_count: int  # Nombre de thermiques (vario > 2 m/s pendant > 2 min)
    thermal_percentage: float  # % du temps en thermique

    # Distance (simplifiée - ligne droite)
    straight_distance_km: float

    # Nombre de points
    n_fixes: int


@dataclass
class FlightComplete:
    """Vol complet avec métadonnées + données IGC"""
    metadata: FlightMetadata
    igc_data: Optional[IGCData]

    # Score calculé (votre formule)
    @property
    def score(self) -> float:
        if self.igc_data is None:
            return 0.0
        # Formule : min(100, distance_km * 1.8 + duration_h * 8 + mean_vario * 10)
        distance_km = self.igc_data.straight_distance_km
        duration_h = self.metadata.duration_hours
        mean_vario = self.igc_data.mean_positive_vario
        return min(100.0, distance_km * 1.8 + duration_h * 8 + mean_vario * 10)


# =============================================================================
# Fonctions de téléchargement
# =============================================================================

def download_cfd_month(year: int, month: int) -> Optional[str]:
    """Télécharge les vols CFD pour un mois donné"""

    # Calculer les timestamps
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    from_ts = int(start_date.timestamp())
    to_ts = int(end_date.timestamp())

    url = f"{CFD_API_URL}?from={from_ts}&to={to_ts}"
    logger.info(f"Téléchargement {year}-{month:02d}: {url}")

    try:
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=60
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Erreur téléchargement {year}-{month:02d}: {e}")
        return None


def parse_cfd_xml(xml_content: str) -> List[FlightMetadata]:
    """Parse le XML de l'API CFD et retourne les métadonnées des vols"""

    flights = []

    try:
        root = ET.fromstring(xml_content)

        for flight_elem in root.findall('.//FlightInfo'):
            try:
                flight = FlightMetadata(
                    flight_id=flight_elem.get('Id', ''),
                    civl_id=_get_text(flight_elem, 'CivlId'),
                    pilot_first_name=_get_text(flight_elem, 'PilotFirstName', ''),
                    pilot_last_name=_get_text(flight_elem, 'PilotLastName', ''),
                    pilot_nation=_get_text(flight_elem, 'PilotNation', ''),
                    pilot_gender=_get_text(flight_elem, 'PilotGender', ''),
                    igc_url=_get_text(flight_elem, 'IgcUrl', ''),
                    igc_md5=_get_text(flight_elem, 'IgcMd5', ''),
                    takeoff_timestamp=int(_get_text(flight_elem, 'TakeoffTime', '0')),
                    landing_timestamp=int(_get_text(flight_elem, 'LandingTime', '0')),
                    takeoff_name=_get_text(flight_elem, 'TakeoffName', ''),
                    takeoff_country=_get_text(flight_elem, 'TakeoffCountry', ''),
                    glider=_get_text(flight_elem, 'Glider', ''),
                    glider_cat=_get_text(flight_elem, 'GliderCat', ''),
                    flight_url=_get_text(flight_elem, 'FlightUrl', ''),
                    nac_flight_id=_get_text(flight_elem, 'NacFlightId', ''),
                )
                flights.append(flight)
            except Exception as e:
                logger.warning(f"Erreur parsing vol: {e}")
                continue

    except ET.ParseError as e:
        logger.error(f"Erreur parsing XML: {e}")

    return flights


def _get_text(elem: ET.Element, tag: str, default: str = None) -> Optional[str]:
    """Helper pour extraire le texte d'un élément XML"""
    child = elem.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return default


def download_igc_file(igc_url: str, dest_path: Path) -> bool:
    """Télécharge un fichier IGC"""

    if dest_path.exists():
        logger.debug(f"IGC déjà présent: {dest_path.name}")
        return True

    try:
        response = requests.get(
            igc_url,
            headers={'User-Agent': USER_AGENT},
            timeout=30
        )
        response.raise_for_status()

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(response.content)
        logger.debug(f"IGC téléchargé: {dest_path.name}")
        return True

    except requests.RequestException as e:
        logger.warning(f"Erreur téléchargement IGC {igc_url}: {e}")
        return False


# =============================================================================
# Parser IGC
# =============================================================================

def parse_igc_file(igc_path: Path) -> Optional[IGCData]:
    """Parse un fichier IGC et extrait les données de vol"""

    try:
        with open(igc_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    except Exception as e:
        logger.warning(f"Erreur lecture IGC {igc_path}: {e}")
        return None

    # Extraire les B-records (points de trace)
    fixes = []
    for line in lines:
        if line.startswith('B'):
            fix = parse_b_record(line)
            if fix:
                fixes.append(fix)

    if len(fixes) < 10:
        logger.warning(f"Pas assez de points dans {igc_path.name}: {len(fixes)}")
        return None

    # Calculer les métriques
    return compute_igc_metrics(fixes)


def parse_b_record(line: str) -> Optional[Dict[str, Any]]:
    """Parse un B-record IGC

    Format: BHHMMSSLLLLLLLNLLLLLLLLEVPPPPPGGGGGCRLF
    - B: Record type
    - HHMMSS: Time UTC
    - LLLLLLLN: Latitude (degrés, minutes, N/S)
    - LLLLLLLLE: Longitude (degrés, minutes, E/W)
    - V: Validity (A=3D fix, V=2D fix)
    - PPPPP: Pressure altitude
    - GGGGG: GPS altitude
    """

    if len(line) < 35:
        return None

    try:
        time_str = line[1:7]

        # Latitude
        lat_deg = int(line[7:9])
        lat_min = int(line[9:14]) / 1000.0
        lat_dir = line[14]
        lat = lat_deg + lat_min / 60.0
        if lat_dir == 'S':
            lat = -lat

        # Longitude
        lon_deg = int(line[15:18])
        lon_min = int(line[18:23]) / 1000.0
        lon_dir = line[23]
        lon = lon_deg + lon_min / 60.0
        if lon_dir == 'W':
            lon = -lon

        # Altitude
        validity = line[24]
        press_alt = int(line[25:30])
        gps_alt = int(line[30:35])

        # Utiliser l'altitude GPS si disponible, sinon pression
        alt = gps_alt if gps_alt > 0 else press_alt

        return {
            'time': time_str,
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'validity': validity
        }

    except (ValueError, IndexError) as e:
        return None


def compute_igc_metrics(fixes: List[Dict]) -> IGCData:
    """Calcule les métriques à partir des points de trace"""

    import math

    n = len(fixes)

    # Positions
    takeoff = fixes[0]
    landing = fixes[-1]

    # Altitudes
    altitudes = [f['alt'] for f in fixes]
    max_alt = max(altitudes)
    min_alt = min(altitudes)

    # Calcul du vario (m/s) - différence d'altitude entre points consécutifs
    # Supposons 1 point par seconde environ (à ajuster selon l'IGC)
    varios = []
    for i in range(1, n):
        dt = 1.0  # Approximation: 1 seconde entre chaque point
        dalt = fixes[i]['alt'] - fixes[i-1]['alt']
        vario = dalt / dt
        varios.append(vario)

    # Vario positif moyen
    positive_varios = [v for v in varios if v > 0]
    mean_positive_vario = sum(positive_varios) / len(positive_varios) if positive_varios else 0.0

    # Vitesse sol (km/h)
    speeds = []
    for i in range(1, n):
        dist = haversine_distance(
            fixes[i-1]['lat'], fixes[i-1]['lon'],
            fixes[i]['lat'], fixes[i]['lon']
        )
        dt = 1.0 / 3600.0  # 1 seconde en heures
        speed = dist / dt if dt > 0 else 0
        speeds.append(speed)

    mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
    max_speed = max(speeds) if speeds else 0.0

    # Comptage des thermiques (vario > 2 m/s pendant > 2 min = 120 points)
    thermal_count = 0
    thermal_duration = 0
    in_thermal = False
    current_thermal_length = 0

    for v in varios:
        if v > 2.0:
            current_thermal_length += 1
            if not in_thermal and current_thermal_length >= 120:
                in_thermal = True
                thermal_count += 1
            if in_thermal:
                thermal_duration += 1
        else:
            in_thermal = False
            current_thermal_length = 0

    thermal_percentage = (thermal_duration / len(varios) * 100) if varios else 0.0

    # Distance en ligne droite
    straight_distance = haversine_distance(
        takeoff['lat'], takeoff['lon'],
        landing['lat'], landing['lon']
    )

    return IGCData(
        takeoff_lat=takeoff['lat'],
        takeoff_lon=takeoff['lon'],
        takeoff_alt=takeoff['alt'],
        landing_lat=landing['lat'],
        landing_lon=landing['lon'],
        landing_alt=landing['alt'],
        max_altitude=max_alt,
        min_altitude=min_alt,
        altitude_gain=max_alt - takeoff['alt'],
        mean_positive_vario=round(mean_positive_vario, 2),
        max_vario=round(max(varios) if varios else 0, 2),
        min_vario=round(min(varios) if varios else 0, 2),
        mean_ground_speed=round(mean_speed, 1),
        max_ground_speed=round(max_speed, 1),
        thermal_count=thermal_count,
        thermal_percentage=round(thermal_percentage, 1),
        straight_distance_km=round(straight_distance, 2),
        n_fixes=n
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcule la distance entre deux points en km (formule de Haversine)"""

    import math

    R = 6371.0  # Rayon de la Terre en km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


# =============================================================================
# Filtrage géographique
# =============================================================================

def is_in_pyrenees(lat: float, lon: float) -> bool:
    """Vérifie si un point est dans la zone Pyrénées"""
    return (BBOX_PYRENEES['min_lat'] <= lat <= BBOX_PYRENEES['max_lat'] and
            BBOX_PYRENEES['min_lon'] <= lon <= BBOX_PYRENEES['max_lon'])


def filter_flights_by_location(
    flights: List[FlightComplete],
    spots_csv: Optional[Path] = None
) -> List[FlightComplete]:
    """Filtre les vols par zone géographique"""

    filtered = []

    for flight in flights:
        if flight.igc_data:
            # Filtrer par coordonnées du décollage
            if is_in_pyrenees(flight.igc_data.takeoff_lat, flight.igc_data.takeoff_lon):
                filtered.append(flight)
        else:
            # Si pas d'IGC, on garde le vol (sera filtré plus tard)
            # Ou on peut filtrer par nom de site si on a le CSV
            filtered.append(flight)

    return filtered


# =============================================================================
# Sauvegarde
# =============================================================================

def save_flights_pickle(flights: List[FlightComplete], output_path: Path):
    """Sauvegarde les vols en pickle"""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as f:
        pickle.dump(flights, f)

    logger.info(f"Sauvegardé {len(flights)} vols dans {output_path}")


def save_flights_csv(flights: List[FlightComplete], output_path: Path):
    """Sauvegarde les vols en CSV"""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'flight_id', 'date', 'takeoff_time', 'landing_time',
            'pilot_name', 'pilot_nation',
            'takeoff_name', 'takeoff_country',
            'glider', 'glider_cat',
            'duration_hours',
            'takeoff_lat', 'takeoff_lon', 'takeoff_alt',
            'landing_lat', 'landing_lon', 'landing_alt',
            'max_altitude', 'altitude_gain',
            'mean_positive_vario', 'max_vario',
            'mean_ground_speed', 'max_ground_speed',
            'thermal_count', 'thermal_percentage',
            'straight_distance_km',
            'score',
            'igc_url', 'flight_url'
        ])

        # Data
        for flight in flights:
            m = flight.metadata
            i = flight.igc_data

            row = [
                m.nac_flight_id,
                m.takeoff_datetime.strftime('%Y-%m-%d'),
                m.takeoff_datetime.strftime('%H:%M:%S'),
                m.landing_datetime.strftime('%H:%M:%S'),
                f"{m.pilot_first_name} {m.pilot_last_name}",
                m.pilot_nation,
                m.takeoff_name,
                m.takeoff_country,
                m.glider,
                m.glider_cat,
                round(m.duration_hours, 2),
            ]

            if i:
                row.extend([
                    i.takeoff_lat, i.takeoff_lon, i.takeoff_alt,
                    i.landing_lat, i.landing_lon, i.landing_alt,
                    i.max_altitude, i.altitude_gain,
                    i.mean_positive_vario, i.max_vario,
                    i.mean_ground_speed, i.max_ground_speed,
                    i.thermal_count, i.thermal_percentage,
                    i.straight_distance_km,
                    round(flight.score, 1),
                ])
            else:
                row.extend([''] * 16)

            row.extend([m.igc_url, m.flight_url])

            writer.writerow(row)

    logger.info(f"Sauvegardé {len(flights)} vols dans {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Télécharge les vols CFD FFVL pour les Pyrénées"
    )
    parser.add_argument(
        '--start-year', type=int, default=2015,
        help="Année de début (défaut: 2015)"
    )
    parser.add_argument(
        '--end-year', type=int, default=2024,
        help="Année de fin (défaut: 2024)"
    )
    parser.add_argument(
        '--download-igc', action='store_true',
        help="Télécharger aussi les fichiers IGC"
    )
    parser.add_argument(
        '--parse-igc', action='store_true',
        help="Parser les fichiers IGC téléchargés"
    )
    parser.add_argument(
        '--spots-csv', type=Path, default=None,
        help="Fichier CSV des spots Pyrénées pour filtrage"
    )
    parser.add_argument(
        '--output-dir', type=Path, default=DATA_DIR,
        help=f"Répertoire de sortie (défaut: {DATA_DIR})"
    )

    args = parser.parse_args()

    # Créer les répertoires
    args.output_dir.mkdir(parents=True, exist_ok=True)
    IGC_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    all_flights: List[FlightMetadata] = []

    # ==========================================================================
    # Étape 1: Télécharger les métadonnées des vols
    # ==========================================================================

    logger.info("=" * 60)
    logger.info("ÉTAPE 1: Téléchargement des métadonnées CFD")
    logger.info("=" * 60)

    for year in range(args.start_year, args.end_year + 1):
        for month in range(1, 13):
            # Vérifier le cache
            cache_file = CACHE_DIR / f"cfd_{year}_{month:02d}.xml"

            if cache_file.exists():
                logger.info(f"Cache trouvé pour {year}-{month:02d}")
                xml_content = cache_file.read_text(encoding='utf-8')
            else:
                xml_content = download_cfd_month(year, month)
                if xml_content:
                    cache_file.write_text(xml_content, encoding='utf-8')
                time.sleep(REQUEST_DELAY)

            if xml_content:
                flights = parse_cfd_xml(xml_content)
                logger.info(f"  -> {len(flights)} vols trouvés")
                all_flights.extend(flights)

    logger.info(f"\nTotal: {len(all_flights)} vols téléchargés")

    # ==========================================================================
    # Étape 2: Télécharger les fichiers IGC (optionnel)
    # ==========================================================================

    if args.download_igc:
        logger.info("\n" + "=" * 60)
        logger.info("ÉTAPE 2: Téléchargement des fichiers IGC")
        logger.info("=" * 60)

        for i, flight in enumerate(all_flights):
            if flight.igc_url:
                igc_filename = f"{flight.nac_flight_id}_{flight.igc_md5[:8]}.igc"
                igc_path = IGC_DIR / igc_filename

                if download_igc_file(flight.igc_url, igc_path):
                    pass  # OK

                if (i + 1) % 100 == 0:
                    logger.info(f"  Progression: {i+1}/{len(all_flights)}")

                time.sleep(IGC_DOWNLOAD_DELAY)

    # ==========================================================================
    # Étape 3: Parser les IGC et créer les vols complets
    # ==========================================================================

    complete_flights: List[FlightComplete] = []

    if args.parse_igc:
        logger.info("\n" + "=" * 60)
        logger.info("ÉTAPE 3: Parsing des fichiers IGC")
        logger.info("=" * 60)

        for i, flight in enumerate(all_flights):
            igc_filename = f"{flight.nac_flight_id}_{flight.igc_md5[:8]}.igc"
            igc_path = IGC_DIR / igc_filename

            igc_data = None
            if igc_path.exists():
                igc_data = parse_igc_file(igc_path)

            complete_flights.append(FlightComplete(
                metadata=flight,
                igc_data=igc_data
            ))

            if (i + 1) % 500 == 0:
                logger.info(f"  Progression: {i+1}/{len(all_flights)}")
    else:
        # Créer les vols sans données IGC
        complete_flights = [
            FlightComplete(metadata=f, igc_data=None)
            for f in all_flights
        ]

    # ==========================================================================
    # Étape 4: Filtrer par zone Pyrénées
    # ==========================================================================

    logger.info("\n" + "=" * 60)
    logger.info("ÉTAPE 4: Filtrage par zone Pyrénées")
    logger.info("=" * 60)

    pyrenees_flights = filter_flights_by_location(complete_flights, args.spots_csv)
    logger.info(f"Vols dans les Pyrénées: {len(pyrenees_flights)}/{len(complete_flights)}")

    # ==========================================================================
    # Étape 5: Sauvegarde
    # ==========================================================================

    logger.info("\n" + "=" * 60)
    logger.info("ÉTAPE 5: Sauvegarde")
    logger.info("=" * 60)

    # Sauvegarder tous les vols (pour référence)
    save_flights_pickle(
        complete_flights,
        args.output_dir / "all_flights.pkl"
    )
    save_flights_csv(
        complete_flights,
        args.output_dir / "all_flights.csv"
    )

    # Sauvegarder les vols Pyrénées
    save_flights_pickle(
        pyrenees_flights,
        args.output_dir / "pyrenees_flights.pkl"
    )
    save_flights_csv(
        pyrenees_flights,
        args.output_dir / "pyrenees_flights.csv"
    )

    # Statistiques finales
    logger.info("\n" + "=" * 60)
    logger.info("RÉSUMÉ")
    logger.info("=" * 60)
    logger.info(f"Total vols CFD: {len(all_flights)}")
    logger.info(f"Vols avec IGC parsé: {sum(1 for f in complete_flights if f.igc_data)}")
    logger.info(f"Vols Pyrénées: {len(pyrenees_flights)}")
    logger.info(f"Fichiers sauvegardés dans: {args.output_dir}")


if __name__ == "__main__":
    main()
