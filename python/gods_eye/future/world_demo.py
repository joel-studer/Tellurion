"""FUTURE-ONLY Tellurion global synthetic world (CC0, deterministic, offline).

SYNTHETIC WORLD REPLAY — never presented as live. Every object carries
source + truth_mode=SYNTHETIC + observation + rights + provenance.

Distributions are realistic without copying individuals:
- aircraft along great-circle-ish corridors between real major airports
- vessels along major shipping-lane waypoints between real major ports
- earthquakes along Ring-of-Fire / ridge zones (not real events)
- wildfires in fire-prone regions, volcanoes at real volcano locations
  (activity levels are synthetic), weather systems in storm belts,
  satellites on synthetic orbits (named public catalog objects only as
  labels, positions are synthetic), air-quality in major metros.

Determinism: same (seed, tick, density) -> identical payload.
No network, no keys, no persons, no private data.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Tuple

DATASET_ID = "tellurion-world-v1"
LICENSE = "CC0-1.0 (synthetic)"
PROVENANCE = "Tellurion synthetic world generator (seeded, deterministic)"
RIGHTS = "CC0: generated in-repo, no persons, no scraped rows"
TRUTH_MODE = "SYNTHETIC"
TRUTH_LABEL = "SYNTHETIC WORLD REPLAY"

# --------------------------------------------------------------------------
# Reference geography (public knowledge: major airports / ports / volcanoes).
# Coordinates are approximate static context (OSM-style), not live data.
# --------------------------------------------------------------------------

AIRPORTS: List[Dict[str, Any]] = [
    {"id": "APT-FRA", "name": "Frankfurt Main", "city": "Frankfurt",
     "country": "Germany", "lat": 50.03, "lon": 8.56},
    {"id": "APT-LHR", "name": "London Heathrow", "city": "London",
     "country": "United Kingdom", "lat": 51.47, "lon": -0.45},
    {"id": "APT-CDG", "name": "Paris Charles de Gaulle", "city": "Paris",
     "country": "France", "lat": 49.01, "lon": 2.55},
    {"id": "APT-AMS", "name": "Amsterdam Schiphol", "city": "Amsterdam",
     "country": "Netherlands", "lat": 52.31, "lon": 4.76},
    {"id": "APT-MAD", "name": "Madrid Barajas", "city": "Madrid",
     "country": "Spain", "lat": 40.50, "lon": -3.57},
    {"id": "APT-FCO", "name": "Rome Fiumicino", "city": "Rome",
     "country": "Italy", "lat": 41.80, "lon": 12.25},
    {"id": "APT-VIE", "name": "Vienna Schwechat", "city": "Vienna",
     "country": "Austria", "lat": 48.11, "lon": 16.57},
    {"id": "APT-ZRH", "name": "Zurich", "city": "Zurich",
     "country": "Switzerland", "lat": 47.46, "lon": 8.55},
    {"id": "APT-IST", "name": "Istanbul Airport", "city": "Istanbul",
     "country": "Turkiye", "lat": 41.27, "lon": 28.74},
    {"id": "APT-DXB", "name": "Dubai International", "city": "Dubai",
     "country": "United Arab Emirates", "lat": 25.25, "lon": 55.36},
    {"id": "APT-DOH", "name": "Hamad International", "city": "Doha",
     "country": "Qatar", "lat": 25.27, "lon": 51.61},
    {"id": "APT-DEL", "name": "Delhi Indira Gandhi", "city": "New Delhi",
     "country": "India", "lat": 28.57, "lon": 77.10},
    {"id": "APT-BOM", "name": "Mumbai Chhatrapati Shivaji", "city": "Mumbai",
     "country": "India", "lat": 19.09, "lon": 72.87},
    {"id": "APT-SIN", "name": "Singapore Changi", "city": "Singapore",
     "country": "Singapore", "lat": 1.36, "lon": 103.99},
    {"id": "APT-HKG", "name": "Hong Kong International", "city": "Hong Kong",
     "country": "China", "lat": 22.31, "lon": 113.91},
    {"id": "APT-PEK", "name": "Beijing Capital", "city": "Beijing",
     "country": "China", "lat": 40.08, "lon": 116.58},
    {"id": "APT-HND", "name": "Tokyo Haneda", "city": "Tokyo",
     "country": "Japan", "lat": 35.55, "lon": 139.78},
    {"id": "APT-NRT", "name": "Tokyo Narita", "city": "Tokyo",
     "country": "Japan", "lat": 35.77, "lon": 140.39},
    {"id": "APT-ICN", "name": "Seoul Incheon", "city": "Seoul",
     "country": "South Korea", "lat": 37.46, "lon": 126.44},
    {"id": "APT-SYD", "name": "Sydney Kingsford Smith", "city": "Sydney",
     "country": "Australia", "lat": -33.95, "lon": 151.18},
    {"id": "APT-LAX", "name": "Los Angeles International", "city": "Los Angeles",
     "country": "United States", "lat": 33.94, "lon": -118.41},
    {"id": "APT-JFK", "name": "New York JFK", "city": "New York",
     "country": "United States", "lat": 40.64, "lon": -73.78},
    {"id": "APT-ORD", "name": "Chicago O'Hare", "city": "Chicago",
     "country": "United States", "lat": 41.97, "lon": -87.91},
    {"id": "APT-DFW", "name": "Dallas Fort Worth", "city": "Dallas",
     "country": "United States", "lat": 32.90, "lon": -97.04},
    {"id": "APT-SFO", "name": "San Francisco International",
     "city": "San Francisco", "country": "United States",
     "lat": 37.62, "lon": -122.38},
    {"id": "APT-GRU", "name": "Sao Paulo Guarulhos", "city": "Sao Paulo",
     "country": "Brazil", "lat": -23.44, "lon": -46.47},
    {"id": "APT-EZE", "name": "Buenos Aires Ezeiza", "city": "Buenos Aires",
     "country": "Argentina", "lat": -34.82, "lon": -58.54},
    {"id": "APT-JNB", "name": "Johannesburg O.R. Tambo",
     "city": "Johannesburg", "country": "South Africa",
     "lat": -26.14, "lon": 28.25},
    {"id": "APT-CAI", "name": "Cairo International", "city": "Cairo",
     "country": "Egypt", "lat": 30.12, "lon": 31.41},
    {"id": "APT-NBO", "name": "Nairobi Jomo Kenyatta", "city": "Nairobi",
     "country": "Kenya", "lat": -1.32, "lon": 36.93},
    {"id": "APT-YYZ", "name": "Toronto Pearson", "city": "Toronto",
     "country": "Canada", "lat": 43.68, "lon": -79.63},
    {"id": "APT-MEX", "name": "Mexico City Benito Juarez",
     "city": "Mexico City", "country": "Mexico",
     "lat": 19.44, "lon": -99.07},
]

PORTS: List[Dict[str, Any]] = [
    {"id": "PORT-RTM", "name": "Port of Rotterdam", "city": "Rotterdam",
     "country": "Netherlands", "lat": 51.95, "lon": 4.14},
    {"id": "PORT-HAM", "name": "Port of Hamburg", "city": "Hamburg",
     "country": "Germany", "lat": 53.87, "lon": 8.30},
    {"id": "PORT-ANR", "name": "Port of Antwerp", "city": "Antwerp",
     "country": "Belgium", "lat": 51.27, "lon": 4.34},
    {"id": "PORT-ALG", "name": "Port of Algeciras", "city": "Algeciras",
     "country": "Spain", "lat": 36.10, "lon": -5.43},
    {"id": "PORT-PIR", "name": "Port of Piraeus", "city": "Piraeus",
     "country": "Greece", "lat": 37.94, "lon": 23.64},
    {"id": "PORT-SIN", "name": "Port of Singapore", "city": "Singapore",
     "country": "Singapore", "lat": 1.26, "lon": 103.82},
    {"id": "PORT-SHA", "name": "Port of Shanghai", "city": "Shanghai",
     "country": "China", "lat": 31.23, "lon": 121.48},
    {"id": "PORT-NGB", "name": "Port of Ningbo-Zhoushan", "city": "Ningbo",
     "country": "China", "lat": 29.95, "lon": 121.85},
    {"id": "PORT-BUS", "name": "Port of Busan", "city": "Busan",
     "country": "South Korea", "lat": 35.10, "lon": 129.04},
    {"id": "PORT-TYO", "name": "Port of Tokyo", "city": "Tokyo",
     "country": "Japan", "lat": 35.62, "lon": 139.65},
    {"id": "PORT-DXB", "name": "Port of Jebel Ali", "city": "Dubai",
     "country": "United Arab Emirates", "lat": 25.01, "lon": 55.06},
    {"id": "PORT-MUM", "name": "Port of Nhava Sheva", "city": "Mumbai",
     "country": "India", "lat": 18.94, "lon": 72.94},
    {"id": "PORT-LAX", "name": "Port of Los Angeles", "city": "Los Angeles",
     "country": "United States", "lat": 33.73, "lon": -118.26},
    {"id": "PORT-NYC", "name": "Port of New York/New Jersey",
     "city": "New York", "country": "United States",
     "lat": 40.67, "lon": -74.02},
    {"id": "PORT-SAV", "name": "Port of Savannah", "city": "Savannah",
     "country": "United States", "lat": 32.08, "lon": -81.08},
    {"id": "PORT-SANT", "name": "Port of Santos", "city": "Santos",
     "country": "Brazil", "lat": -23.96, "lon": -46.33},
    {"id": "PORT-DUR", "name": "Port of Durban", "city": "Durban",
     "country": "South Africa", "lat": -29.87, "lon": 31.03},
    {"id": "PORT-PSD", "name": "Port Said", "city": "Port Said",
     "country": "Egypt", "lat": 31.27, "lon": 32.30},
    {"id": "PORT-SYD", "name": "Port Botany (Sydney)", "city": "Sydney",
     "country": "Australia", "lat": -33.98, "lon": 151.20},
    {"id": "PORT-VAN", "name": "Port of Vancouver", "city": "Vancouver",
     "country": "Canada", "lat": 49.28, "lon": -123.10},
    {"id": "PORT-COL", "name": "Port of Colon", "city": "Colon",
     "country": "Panama", "lat": 9.35, "lon": -79.90},
    {"id": "PORT-HAM-DE", "name": "Port of Bremerhaven", "city": "Bremerhaven",
     "country": "Germany", "lat": 53.57, "lon": 8.14},
    {"id": "PORT-GEN", "name": "Port of Genoa", "city": "Genoa",
     "country": "Italy", "lat": 44.41, "lon": 8.93},
    {"id": "PORT-VIE-AT", "name": "Port of Vienna (Freudenau)", "city": "Vienna",
     "country": "Austria", "lat": 48.18, "lon": 16.46},
]

VOLCANOES: List[Dict[str, Any]] = [
    {"id": "VLC-ETNA", "name": "Etna", "country": "Italy",
     "lat": 37.75, "lon": 14.99},
    {"id": "VLC-STROM", "name": "Stromboli", "country": "Italy",
     "lat": 38.79, "lon": 15.21},
    {"id": "VLC-KILA", "name": "Kilauea", "country": "United States",
     "lat": 19.42, "lon": -155.29},
    {"id": "VLC-STHEL", "name": "Mount St. Helens", "country": "United States",
     "lat": 46.20, "lon": -122.18},
    {"id": "VLC-FUJI", "name": "Mount Fuji", "country": "Japan",
     "lat": 35.36, "lon": 138.73},
    {"id": "VLC-ASO", "name": "Aso", "country": "Japan",
     "lat": 32.88, "lon": 131.10},
    {"id": "VLC-PINAT", "name": "Pinatubo", "country": "Philippines",
     "lat": 15.13, "lon": 120.35},
    {"id": "VLC-MAYON", "name": "Mayon", "country": "Philippines",
     "lat": 13.26, "lon": 123.69},
    {"id": "VLC-MERAP", "name": "Merapi", "country": "Indonesia",
     "lat": -7.54, "lon": 110.44},
    {"id": "VLC-KRAK", "name": "Anak Krakatau", "country": "Indonesia",
     "lat": -6.10, "lon": 105.42},
    {"id": "VLC-EYJA", "name": "Eyjafjallajoekull", "country": "Iceland",
     "lat": 63.63, "lon": -19.62},
    {"id": "VLC-GRIM", "name": "Grimsvotn", "country": "Iceland",
     "lat": 64.42, "lon": -17.33},
    {"id": "VLC-VILL", "name": "Villarrica", "country": "Chile",
     "lat": -39.42, "lon": -71.93},
    {"id": "VLC-CUMB", "name": "Cumbre Vieja (La Palma)", "country": "Spain",
     "lat": 28.58, "lon": -17.85},
    {"id": "VLC-NYIR", "name": "Nyiragongo",
     "country": "Democratic Republic of the Congo",
     "lat": -1.52, "lon": 29.25},
    {"id": "VLC-ERTA", "name": "Erta Ale", "country": "Ethiopia",
     "lat": 13.60, "lon": 40.67},
]

# Tectonic / seismic zones (lat, lon, spread, weight): Ring of Fire + ridges.
QUAKE_ZONES: List[Tuple[float, float, float, float]] = [
    (38.0, 142.0, 6.0, 3.0),    # Japan trench
    (-5.0, 130.0, 7.0, 2.5),    # Indonesia
    (-15.0, -75.0, 6.0, 2.0),   # Peru-Chile
    (55.0, -160.0, 5.0, 1.5),   # Alaska-Aleutian
    (19.0, -155.0, 3.0, 1.0),   # Hawaii
    (36.0, 28.0, 4.0, 1.0),     # E Mediterranean
    (41.0, 44.0, 4.0, 1.0),     # Caucasus
    (-30.0, -70.0, 4.0, 1.5),   # Chile
    (0.0, -90.0, 4.0, 1.0),     # Galapagos ridge
    (51.0, -178.0, 4.0, 1.0),   # Aleutian
    (-38.0, 178.0, 4.0, 1.2),   # New Zealand
    (13.0, 48.0, 5.0, 0.8),     # Gulf of Aden
    (45.0, 150.0, 4.0, 1.2),    # Kuril
    (23.0, 120.0, 3.0, 0.8),    # Taiwan
    (64.0, -20.0, 3.0, 0.6),    # Iceland ridge
]

FIRE_REGIONS: List[Tuple[float, float, float, float]] = [
    (37.5, -120.5, 3.0, 3.0),   # California
    (-33.5, 150.5, 4.0, 2.5),   # SE Australia
    (40.5, -8.0, 3.0, 1.5),     # Iberia
    (37.5, 22.0, 3.0, 1.5),     # Greece/Med
    (55.0, 37.0, 5.0, 1.2),     # Russia boreal
    (-15.0, -55.0, 5.0, 1.5),   # Amazon fringe (agricultural burning belt)
    (0.5, 113.0, 4.0, 1.5),     # Borneo
    (48.0, 16.0, 2.0, 0.5),     # E Austria (low baseline)
]

STORM_SYSTEMS: List[Dict[str, Any]] = [
    {"name": "North Atlantic low", "lat": 52.0, "lon": -30.0, "kind": "STORM"},
    {"name": "Western Pacific typhoon belt", "lat": 18.0, "lon": 132.0,
     "kind": "TYPHOON"},
    {"name": "US Great Plains severe cell", "lat": 38.0, "lon": -97.0,
     "kind": "SEVERE"},
    {"name": "Bay of Bengal monsoon low", "lat": 15.0, "lon": 89.0,
     "kind": "MONSOON"},
    {"name": "Mediterranean medicane watch", "lat": 36.5, "lon": 16.0,
     "kind": "STORM"},
    {"name": "Southern Ocean front", "lat": -50.0, "lon": 30.0,
     "kind": "FRONT"},
]

METROS_AQ: List[Tuple[str, str, float, float]] = [
    ("Vienna", "Austria", 48.21, 16.37),
    ("Berlin", "Germany", 52.52, 13.40),
    ("Paris", "France", 48.86, 2.35),
    ("London", "United Kingdom", 51.50, -0.12),
    ("Madrid", "Spain", 40.42, -3.70),
    ("Rome", "Italy", 41.90, 12.50),
    ("Warsaw", "Poland", 52.23, 21.01),
    ("Istanbul", "Turkiye", 41.01, 28.98),
    ("Cairo", "Egypt", 30.04, 31.24),
    ("Lagos", "Nigeria", 6.52, 3.38),
    ("Johannesburg", "South Africa", -26.20, 28.05),
    ("Mumbai", "India", 19.08, 72.88),
    ("Delhi", "India", 28.61, 77.21),
    ("Beijing", "China", 39.90, 116.40),
    ("Shanghai", "China", 31.23, 121.47),
    ("Tokyo", "Japan", 35.68, 139.69),
    ("Jakarta", "Indonesia", -6.21, 106.85),
    ("Sydney", "Australia", -33.87, 151.21),
    ("New York", "United States", 40.71, -74.01),
    ("Los Angeles", "United States", 34.05, -118.24),
    ("Mexico City", "Mexico", 19.43, -99.13),
    ("Sao Paulo", "Brazil", -23.55, -46.63),
]

# Public catalog satellites (names only; positions are synthetic).
SAT_CATALOG: List[str] = [
    "ISS (ZARYA)", "HST", "NOAA-19", "METOP-B", "SENTINEL-1A",
    "SENTINEL-2A", "TERRA", "AQUA", "LANDSAT-8", "LANDSAT-9",
    "GOES-16", "GOES-18", "METEOSAT-11", "HIMAWARI-9", "TIANGONG",
]

COUNTRIES: List[Dict[str, Any]] = [
    {"name": "Austria", "lat": 47.52, "lon": 14.55, "aliases": ["at"]},
    {"name": "Germany", "lat": 51.17, "lon": 10.45, "aliases": ["de"]},
    {"name": "France", "lat": 46.23, "lon": 2.21, "aliases": ["fr"]},
    {"name": "United Kingdom", "lat": 54.24, "lon": -2.30,
     "aliases": ["uk", "britain", "great britain"]},
    {"name": "Italy", "lat": 41.87, "lon": 12.57, "aliases": ["it"]},
    {"name": "Spain", "lat": 40.46, "lon": -3.75, "aliases": ["es"]},
    {"name": "United States", "lat": 39.83, "lon": -98.58,
     "aliases": ["usa", "us", "america"]},
    {"name": "Japan", "lat": 36.20, "lon": 138.25, "aliases": ["jp"]},
    {"name": "Brazil", "lat": -14.24, "lon": -51.93, "aliases": ["br"]},
    {"name": "India", "lat": 20.59, "lon": 78.96, "aliases": ["in"]},
    {"name": "China", "lat": 35.86, "lon": 104.20, "aliases": ["cn"]},
    {"name": "Australia", "lat": -25.27, "lon": 133.78, "aliases": ["au"]},
    {"name": "South Africa", "lat": -30.56, "lon": 22.94,
     "aliases": ["south-africa", "za"]},
    {"name": "Egypt", "lat": 26.82, "lon": 30.80, "aliases": ["eg"]},
    {"name": "Mexico", "lat": 23.63, "lon": -102.55, "aliases": ["mx"]},
    {"name": "Canada", "lat": 56.13, "lon": -106.35, "aliases": ["ca"]},
    {"name": "Indonesia", "lat": -0.79, "lon": 113.92,
     "aliases": ["indonesia", "id"]},
    {"name": "South Korea", "lat": 35.91, "lon": 127.77,
     "aliases": ["south-korea", "korea", "kr"]},
]


def match_country(selector: str) -> Dict[str, Any] | None:
    """Gazetteer country match with alias support.

    Short selectors (<=3 chars) match names/aliases exactly only, so
    "USA" can never substring-match "Busan" again. Longer selectors
    keep the forgiving substring behavior.
    """
    s = (selector or "").strip().lower()
    if not s:
        return None
    for c in COUNTRIES:
        names = [c["name"].lower()] + [a.lower() for a in
                                       c.get("aliases", [])]
        if len(s) <= 3:
            if s in names:
                return c
        elif c["name"].lower() in s or s in c["name"].lower() or \
                any(a in s.split() or s in a for a in
                    c.get("aliases", [])):
            return c
    return None


def _rng(seed: int) -> random.Random:
    return random.Random(77_000 + seed)


def _pick_weighted(rng: random.Random,
                   zones: List[Tuple[float, float, float, float]]
                   ) -> Tuple[float, float, float]:
    total = sum(z[3] for z in zones)
    x = rng.uniform(0, total)
    acc = 0.0
    for lat, lon, spread, w in zones:
        acc += w
        if x <= acc:
            return lat, lon, spread
    lat, lon, spread, _w = zones[-1]
    return lat, lon, spread


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _base(seed: int = 1, tick: int = 0) -> Dict[str, Any]:
    return {
        "source": "synthetic-world-generator",
        "truth_mode": TRUTH_MODE,
        "truth_label": TRUTH_LABEL,
        "provenance": PROVENANCE,
        "rights": RIGHTS,
        "freshness": "replay",
        "source_event_time": f"synthetic-t{tick}",
        "first_seen": "synthetic-t0",
        "ingested_at": f"synthetic-t{tick}",
        "precision": "APPROXIMATE",
    }


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------

def world_aircraft(seed: int = 101, n: int = 1200,
                   tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        a = rng.choice(AIRPORTS)
        b = rng.choice(AIRPORTS)
        if b is a:
            b = rng.choice(AIRPORTS)
        frac = rng.random()
        # interpolate + cross-track jitter (deterministic per object)
        lat = a["lat"] + (b["lat"] - a["lat"]) * frac + rng.uniform(-1.5, 1.5)
        lon = a["lon"] + (b["lon"] - a["lon"]) * frac + rng.uniform(-1.5, 1.5)
        lat = max(-60.0, min(75.0, round(lat, 3)))
        lon = round(((lon + 180.0) % 360.0) - 180.0, 3)
        hdg = round(_bearing(a["lat"], a["lon"], b["lat"], b["lon"]), 1)
        spd = rng.randint(380, 500)
        alt = rng.choice([29000, 31000, 33000, 35000, 37000, 39000, 41000])
        adv = tick * spd / 3600.0 / 60.0
        lat2 = round(max(-60.0, min(75.0,
                                    lat + adv * math.cos(math.radians(hdg)))),
                     3)
        lon2 = round(((lon + adv * math.sin(math.radians(hdg)) + 180.0)
                      % 360.0) - 180.0, 3)
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-AC{i:05d}", "callsign": f"TWN{i:04d}",
            "lat": lat2, "lon": lon2, "alt_ft": alt,
            "speed_kt": spd, "heading": hdg,
            "origin": a["id"], "destination": b["id"],
            "trail": [[lat, lon], [lat2, lon2]],
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "category": "AIRCRAFT",
        })
    return out


# Major lane waypoint chains (lon/lat pairs, coarse but plausible).
LANES: List[List[Tuple[float, float]]] = [
    [(4.0, 52.0), (-6.0, 36.0), (32.0, 31.5), (43.0, 12.0), (80.0, 6.0),
     (104.0, 1.5), (122.0, 31.0)],                       # Europe-Asia via Suez
    [(-74.0, 40.5), (-60.0, 35.0), (-30.0, 38.0), (-6.0, 36.0)],  # Transatlantic
    [(-118.0, 33.5), (-140.0, 30.0), (150.0, 30.0), (140.0, 35.0)],  # Transpacific
    [(-79.9, 9.3), (-100.0, 5.0), (-140.0, 0.0), (150.0, -10.0)],    # Panama-Pacific
    [(55.0, 25.0), (77.0, 8.0), (104.0, 1.5), (152.0, -34.0)],       # Gulf-Australia
    [(-46.0, -24.0), (-20.0, -35.0), (18.0, -35.0), (31.0, -30.0)],  # S Atlantic
]


def world_vessels(seed: int = 202, n: int = 900,
                  tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        lane = rng.choice(LANES)
        seg = rng.randint(0, len(lane) - 2)
        frac = rng.random()
        (lon1, lat1), (lon2, lat2) = lane[seg], lane[seg + 1]
        lat = lat1 + (lat2 - lat1) * frac + rng.uniform(-1.2, 1.2)
        lon = lon1 + (lon2 - lon1) * frac + rng.uniform(-1.2, 1.2)
        lat = round(max(-60.0, min(70.0, lat)), 3)
        lon = round(((lon + 180.0) % 360.0) - 180.0, 3)
        course = round(_bearing(lat1, lon1, lat2, lon2), 1)
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-VS{i:05d}", "name": f"World Trader {i}",
            "lat": lat, "lon": lon,
            "speed_kt": round(rng.uniform(8, 20), 1),
            "course": course,
            "nav_state": rng.choice(["UNDERWAY", "UNDERWAY", "UNDERWAY",
                                     "ANCHORED", "MOORED"]),
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "category": "MARITIME",
        })
    return out


def world_quakes(seed: int = 303, n: int = 130,
                 tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        clat, clon, spread = _pick_weighted(rng, QUAKE_ZONES)
        lat = round(rng.gauss(clat, spread / 2.0), 3)
        lon = round(rng.gauss(clon, spread / 2.0), 3)
        lat = max(-70.0, min(75.0, lat))
        lon = ((lon + 180.0) % 360.0) - 180.0
        mag = round(min(7.5, max(2.5, rng.gauss(4.3, 0.9))), 1)
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-EQ{i:04d}", "mag": mag,
            "depth_km": round(rng.uniform(5, 120), 1),
            "lat": round(lat, 3), "lon": round(lon, 3),
            "place": "synthetic epicentre (plate-boundary belt)",
            "event_time": f"synthetic-t-{rng.randint(0, 24)}h",
            "precision": "REGIONAL",
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "category": "SEISMIC",
            "severity": 5 if mag >= 6.0 else (4 if mag >= 5.0 else 3),
        })
    return sorted(out, key=lambda o: -o["mag"])


def world_fires(seed: int = 404, n: int = 120,
                tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        clat, clon, spread, _w = rng.choice(FIRE_REGIONS)
        lat = round(rng.gauss(clat, spread / 2.0), 3)
        lon = round(rng.gauss(clon, spread / 2.0), 3)
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-FR{i:04d}", "lat": lat, "lon": lon,
            "confidence": rng.choice(["LOW", "NOMINAL", "NOMINAL", "HIGH"]),
            "sensor": rng.choice(["SYN-VIIRS", "SYN-MODIS"]),
            "observed": f"synthetic-t-{rng.randint(0, 12)}h",
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "category": "WILDFIRE",
        })
    return out


def world_volcanoes(seed: int = 505,
                    tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    for i, v in enumerate(VOLCANOES):
        level = rng.choice(["NORMAL", "NORMAL", "NORMAL", "ADVISORY",
                            "WATCH", "WARNING" if i < 2 else "NORMAL"])
        base = _base(seed, tick)
        out.append({
            **base,
            "id": v["id"], "name": v["name"], "country": v["country"],
            "lat": v["lat"], "lon": v["lon"],
            "alert_level": level,
            "observed": f"synthetic-t-{rng.randint(0, 48)}h",
            "precision": "EXACT",
            "observation": "OBSERVED",
            "observation_type": "GOVERNMENT_NOTICE",
            "category": "VOLCANO",
        })
    return out


def world_weather(seed: int = 606, n_cells: int = 220,
                  tick: int = 0) -> Dict[str, Any]:
    rng = _rng(seed)
    cells: List[Dict[str, Any]] = []
    for i in range(n_cells):
        s = rng.choice(STORM_SYSTEMS)
        lat = round(rng.gauss(s["lat"], 8.0), 3)
        lon = round(rng.gauss(s["lon"], 12.0), 3)
        lat = max(-65.0, min(75.0, lat))
        lon = ((lon + 180.0) % 360.0) - 180.0
        base = _base(seed, tick)
        cells.append({
            **base,
            "id": f"WLD-WX{i:04d}", "lat": lat, "lon": lon,
            "system": s["name"],
            "radius_km": rng.randint(60, 420),
            "wind_kt": rng.randint(15, 110),
            "precip_mm_h": round(rng.uniform(0, 40), 1),
            "observation": "INFERRED",
            "observation_type": "INFERRED",
            "category": "WEATHER",
        })
    alerts: List[Dict[str, Any]] = []
    for i, s in enumerate(STORM_SYSTEMS):
        d = 4.0
        base = _base(seed, tick)
        alerts.append({
            **base,
            "id": f"WLD-ALERT-{i:02d}", "kind": s["kind"],
            "title": f"Synthetic {s['kind'].lower()} watch — {s['name']}",
            "polygon": [[s["lat"] - d, s["lon"] - d * 1.6],
                        [s["lat"] - d, s["lon"] + d * 1.6],
                        [s["lat"] + d, s["lon"] + d * 1.6],
                        [s["lat"] + d, s["lon"] - d * 1.6]],
            "valid_from": "synthetic-t0", "valid_to": "synthetic-t+24h",
            "source": "synthetic met service",
            "precision": "REGIONAL",
            "observation": "INFERRED",
            "observation_type": "GOVERNMENT_NOTICE",
            "category": "WEATHER",
            "severity": "WATCH",
        })
    return {"cells": cells, "alerts": alerts}


def world_air_quality(seed: int = 707,
                      tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    for i, (city, country, lat, lon) in enumerate(METROS_AQ):
        aqi = max(5, min(280, int(rng.gauss(65, 40))))
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-AQ{i:03d}", "city": city, "country": country,
            "lat": round(lat + rng.uniform(-0.15, 0.15), 3),
            "lon": round(lon + rng.uniform(-0.15, 0.15), 3),
            "aqi": aqi,
            "band": "GOOD" if aqi <= 50 else (
                "MODERATE" if aqi <= 100 else (
                    "UNHEALTHY_SG" if aqi <= 150 else "UNHEALTHY")),
            "observed": f"synthetic-t-{rng.randint(0, 3)}h",
            "precision": "APPROXIMATE",
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "category": "AIR_QUALITY",
        })
    # extra synthetic background stations for density
    for j in range(180):
        lat = round(rng.uniform(-55, 65), 3)
        lon = round(rng.uniform(-180, 180), 3)
        aqi = max(5, min(200, int(rng.gauss(55, 35))))
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-AQX{j:04d}", "city": "synthetic grid",
            "country": "UNKNOWN", "lat": lat, "lon": lon, "aqi": aqi,
            "band": "MODERATE", "observed": f"synthetic-t-{j % 4}h",
            "precision": "REGIONAL",
            "observation": "INFERRED",
            "observation_type": "INFERRED",
            "category": "AIR_QUALITY",
        })
    return out


def world_space_weather(seed: int = 808,
                        tick: int = 0) -> Dict[str, Any]:
    rng = _rng(seed)
    kp = max(0, min(9, int(rng.gauss(3, 2))))
    base = _base(seed, tick)
    return {
        **base,
        "id": "WLD-SW-00",
        "kp_index": kp,
        "storm_level": "G0" if kp < 5 else f"G{kp - 4}",
        "solar_wind_km_s": round(rng.uniform(320, 750), 1),
        "xray_class": rng.choice(["B", "B", "C", "C", "M", "X"]),
        "summary": f"Synthetic Kp {kp} — "
                   f"{'quiet' if kp < 4 else 'geomagnetic activity'}",
        "issued": f"synthetic-t{tick}",
        "observation": "OBSERVED",
        "observation_type": "GOVERNMENT_NOTICE",
        "category": "SPACE_WEATHER",
    }


def world_satellites(seed: int = 909, n: int = 60,
                     tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out: List[Dict[str, Any]] = []
    names = (SAT_CATALOG * ((n // len(SAT_CATALOG)) + 1))[:n]
    for i, name in enumerate(names):
        # synthetic orbit: latitude oscillates, longitude drifts with tick
        phase = rng.uniform(0, 360)
        inc = rng.choice([51.6, 97.8, 98.2, 0.0])
        lat = round(max(-80, min(80, inc * 0.9 * math.sin(
            math.radians(phase + tick * 4.0)))), 3)
        lon = round(((phase * 2.0 + tick * 15.0 + i * 37.0) % 360.0) - 180.0,
                    3)
        track = [[round(max(-80, min(80, inc * 0.9 * math.sin(
            math.radians(phase + (tick + k) * 4.0)))), 3),
                  round(((phase * 2.0 + (tick + k) * 15.0 + i * 37.0)
                         % 360.0) - 180.0, 3)] for k in range(-2, 3)]
        base = _base(seed, tick)
        d = 6.0
        out.append({
            **base,
            "id": f"WLD-SAT{i:03d}", "name": name,
            "catalog": "public catalog label only; position synthetic",
            "lat": lat, "lon": lon,
            "alt_km": rng.choice([420, 550, 780, 35786 if i % 9 == 0 else 550]),
            "epoch": f"synthetic-t{tick}",
            "freshness": "replay",
            "track": track,
            "footprint": [[lat - d, lon - d], [lat - d, lon + d],
                          [lat + d, lon + d], [lat + d, lon - d]],
            "scene_id": f"WLD_SCENE_{i:04d}",
            "sensor": "SYN-MSI", "resolution_m": 10,
            "cloud_cover_pct": rng.randint(0, 60),
            "acquired": f"synthetic-t{tick}",
            "precision": "APPROXIMATE",
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "category": "SATELLITE",
        })
    return out


def world_notices(seed: int = 111,
                  tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    kinds = ["GOVERNMENT_NOTICE", "PUBLIC_REPORT", "NEWS_REPORT"]
    cities = rng.sample(METROS_AQ, 12)
    out: List[Dict[str, Any]] = []
    for i, (city, country, lat, lon) in enumerate(cities):
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-NT{i:03d}",
            "title": f"Synthetic public notice — {city}",
            "city": city, "country": country,
            "lat": round(lat, 3), "lon": round(lon, 3),
            "issued": f"synthetic-t-{rng.randint(0, 24)}h",
            "precision": "REGIONAL",
            "observation": "OBSERVED",
            "observation_type": kinds[i % len(kinds)],
            "category": "GOVERNMENT" if i % 3 == 0 else (
                "HUMANITARIAN" if i % 3 == 1 else "NEWS"),
        })
    return out


def world_disasters(seed: int = 222, tick: int = 0) -> List[Dict[str, Any]]:
    """Fused multi-source disaster stories (each links 3+ synthetic legs)."""
    rng = _rng(seed)
    quakes = world_quakes(seed=seed, n=6, tick=tick)
    stories: List[Dict[str, Any]] = []
    for i, q in enumerate(quakes[:4]):
        base = _base(seed, tick)
        stories.append({
            **base,
            "id": f"WLD-DS{i:02d}",
            "title": f"Synthetic disaster watch M{q['mag']} — "
                     f"({q['lat']}, {q['lon']})",
            "lat": q["lat"], "lon": q["lon"],
            "legs": [q["id"], f"WLD-ALERT-{i % 6:02d}",
                     f"WLD-NT{i:03d}", "WLD-SAT001"],
            "corroboration": "MULTIPLE SOURCES",
            "severity": "ALERT" if q["mag"] >= 6.0 else "WATCH",
            "observation": "CORROBORATED",
            "observation_type": "CORROBORATED",
            "category": "DISASTER",
            "precision": "REGIONAL",
        })
    return stories


def world_transit(seed: int = 333, n: int = 150,
                  tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    hubs = [m for m in METROS_AQ[:12]]
    out: List[Dict[str, Any]] = []
    for i in range(n):
        city, country, lat, lon = rng.choice(hubs)
        base = _base(seed, tick)
        out.append({
            **base,
            "id": f"WLD-TR{i:04d}", "city": city, "country": country,
            "lat": round(lat + rng.uniform(-0.3, 0.3), 3),
            "lon": round(lon + rng.uniform(-0.3, 0.3), 3),
            "kind": rng.choice(["DELAY", "DETOUR", "CLOSURE", "CONGESTION"]),
            "severity": rng.randint(1, 4),
            "reported": f"synthetic-t-{rng.randint(0, 6)}h",
            "observation": "OBSERVED",
            "observation_type": "PUBLIC_REPORT",
            "category": "TRANSIT",
        })
    return out


# --------------------------------------------------------------------------
# Payload / aggregation
# --------------------------------------------------------------------------

DENSITIES: Dict[str, Dict[str, int]] = {
    "standard": {"ac": 1200, "vs": 900, "wx": 220, "eq": 130, "fr": 120,
                 "sat": 60, "tr": 150},
    "dense": {"ac": 2600, "vs": 1400, "wx": 320, "eq": 200, "fr": 220,
              "sat": 90, "tr": 300},
    "full": {"ac": 6000, "vs": 3200, "wx": 500, "eq": 300, "fr": 350,
             "sat": 140, "tr": 600},
}


def world_payload(tick: int = 0,
                  density: str = "standard") -> Dict[str, Any]:
    try:
        t = max(0, min(12, int(tick)))
    except (TypeError, ValueError):
        t = 0
    spec = DENSITIES.get(density, DENSITIES["standard"])
    wx = world_weather(tick=t, n_cells=spec["wx"])
    ac = world_aircraft(n=spec["ac"], tick=t)
    vs = world_vessels(n=spec["vs"], tick=t)
    eq = world_quakes(n=spec["eq"], tick=t)
    fr = world_fires(n=spec["fr"], tick=t)
    sats = world_satellites(n=spec["sat"], tick=t)
    aq = world_air_quality(tick=t)
    volc = world_volcanoes(tick=t)
    notices = world_notices(tick=t)
    disasters = world_disasters(tick=t)
    transit = world_transit(n=spec["tr"], tick=t)
    sw = world_space_weather(tick=t)
    total = (len(ac) + len(vs) + len(wx["cells"]) + len(wx["alerts"])
             + len(eq) + len(fr) + len(sats) + len(aq) + len(volc)
             + len(notices) + len(disasters) + len(transit)
             + len(AIRPORTS) + len(PORTS) + 1)
    return {
        "dataset_id": DATASET_ID,
        "license": LICENSE,
        "provenance": PROVENANCE,
        "rights": RIGHTS,
        "truth_mode": TRUTH_MODE,
        "truth_label": TRUTH_LABEL,
        "tick": t,
        "density": density,
        "live": False,
        "aircraft": ac,
        "vessels": vs,
        "weather": wx,
        "seismic": eq,
        "wildfire": fr,
        "satellites": sats,
        "air_quality": aq,
        "volcanoes": volc,
        "notices": notices,
        "disasters": disasters,
        "transit": transit,
        "space_weather": sw,
        "airports": [{"id": a["id"], "name": a["name"],
                      "city": a["city"], "country": a["country"],
                      "lat": a["lat"], "lon": a["lon"],
                      "observation": "OBSERVED",
                      "observation_type": "OBSERVED",
                      "category": "AIRPORT",
                      "provenance": PROVENANCE, "rights": RIGHTS,
                      "truth_mode": TRUTH_MODE} for a in AIRPORTS],
        "ports": [{"id": p["id"], "name": p["name"],
                   "city": p["city"], "country": p["country"],
                   "lat": p["lat"], "lon": p["lon"],
                   "observation": "OBSERVED",
                   "observation_type": "OBSERVED",
                   "category": "PORT",
                   "provenance": PROVENANCE, "rights": RIGHTS,
                   "truth_mode": TRUTH_MODE} for p in PORTS],
        "activity": {},
        "counts": {},
        "health": source_health_snapshot(),
        "blind_spots": blindspot_grid(),
        "total_objects": total,
    }


def activity_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    counts = {
        "aircraft": len(payload.get("aircraft", [])),
        "vessels": len(payload.get("vessels", [])),
        "satellites": len(payload.get("satellites", [])),
        "weather_alerts": len(payload.get("weather", {}).get("alerts", [])),
        "weather_cells": len(payload.get("weather", {}).get("cells", [])),
        "earth_events": len(payload.get("seismic", []))
        + len(payload.get("wildfire", [])) + len(payload.get("volcanoes", [])),
        "wildfires": len(payload.get("wildfire", [])),
        "earthquakes": len(payload.get("seismic", [])),
        "volcanoes": len(payload.get("volcanoes", [])),
        "transit_events": len(payload.get("transit", [])),
        "public_notices": len(payload.get("notices", [])),
        "disasters": len(payload.get("disasters", [])),
        "air_quality": len(payload.get("air_quality", [])),
        "airports": len(payload.get("airports", [])),
        "ports": len(payload.get("ports", [])),
    }
    counts["total"] = sum(v for k, v in counts.items())
    return {
        "counts": counts,
        "truth_mode": TRUTH_MODE,
        "truth_label": TRUTH_LABEL,
        "live": False,
        "note": "counts are derived from the current synthetic dataset; "
                "no live claims",
    }


def source_health_snapshot() -> List[Dict[str, Any]]:
    return [
        {"source_id": "synthetic-world", "state": "ONLINE",
         "detail": "local deterministic generator; no network",
         "rights": "CC0", "freshness": "replay"},
        {"source_id": "usgs-earthquakes", "state": "STANDBY",
         "detail": "qualified; not polled in base demo (opt-in plugin)",
         "rights": "US public domain", "freshness": "delayed-when-enabled"},
        {"source_id": "noaa-weather-alerts", "state": "STANDBY",
         "detail": "qualified; not polled in base demo (opt-in plugin)",
         "rights": "US public domain", "freshness": "delayed-when-enabled"},
        {"source_id": "noaa-swpc", "state": "STANDBY",
         "detail": "qualified; not polled in base demo (opt-in plugin)",
         "rights": "US public domain", "freshness": "delayed-when-enabled"},
        {"source_id": "nasa-eonet", "state": "STANDBY",
         "detail": "qualified metadata; not polled in base demo",
         "rights": "open metadata", "freshness": "delayed-when-enabled"},
        {"source_id": "gdacs-alerts", "state": "STANDBY",
         "detail": "qualified summary/link; not polled in base demo",
         "rights": "humanitarian use", "freshness": "delayed-when-enabled"},
        {"source_id": "nasa-firms", "state": "KEY REQUIRED",
         "detail": "user supplies own MAP_KEY locally; never bundled",
         "rights": "per-user terms", "freshness": "delayed-when-enabled"},
        {"source_id": "opensky-network", "state": "KEY REQUIRED",
         "detail": "user OAuth creds; quota-aware; display-only",
         "rights": "account terms; no bulk redistribution",
         "freshness": "delayed-when-enabled"},
        {"source_id": "aisstream", "state": "KEY REQUIRED",
         "detail": "user key + server proxy; never browser-direct",
         "rights": "account terms", "freshness": "delayed-when-enabled"},
        {"source_id": "celestrak", "state": "RIGHTS BLOCKED",
         "detail": "terms review required before any use",
         "rights": "UNKNOWN", "freshness": "unknown"},
        {"source_id": "gdelt-events", "state": "RIGHTS BLOCKED",
         "detail": "reported events only; review before use",
         "rights": "UNKNOWN", "freshness": "unknown"},
    ]


def blindspot_grid() -> List[Dict[str, Any]]:
    return [
        {"region": "North Atlantic", "status": "PARTIAL",
         "reason": "synthetic density only; live aviation/maritime need "
                   "user-key legs"},
        {"region": "Pacific / remote ocean", "status": "PARTIAL",
         "reason": "sparse receiver coverage even when live legs enabled"},
        {"region": "Central Africa / Central Asia",
         "status": "NO QUALIFIED SOURCE",
         "reason": "no qualified ground-station feed in base demo"},
        {"region": "Polar regions", "status": "STALE",
         "reason": "synthetic orbits only; no qualified polar feed"},
        {"region": "United States", "status": "GOOD",
         "detail": "USGS + NWS + AirNow qualified paths exist (opt-in)"},
        {"region": "Europe", "status": "GOOD",
         "detail": "EEA AQ + Copernicus EMS + OSM context paths exist"},
        {"region": "Austria", "status": "GOOD",
         "detail": "see Austria demo pack (GeoSphere/OWD/ASFINAG/GTFS paths)"},
        {"region": "Open ocean vessel fringe", "status": "UNKNOWN",
         "reason": "receiver-dependent even when live"},
    ]


# --------------------------------------------------------------------------
# Search / region / whats-here / feed
# --------------------------------------------------------------------------

def _gazetteer() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for a in AIRPORTS:
        rows.append({"kind": "airport", "id": a["id"],
                     "label": f"{a['name']} ({a['city']}, {a['country']})",
                     "lat": a["lat"], "lon": a["lon"],
                     "hay": f"{a['id']} {a['name']} {a['city']} "
                            f"{a['country']} airport".lower()})
    for p in PORTS:
        rows.append({"kind": "port", "id": p["id"],
                     "label": f"{p['name']} ({p['city']}, {p['country']})",
                     "lat": p["lat"], "lon": p["lon"],
                     "hay": f"{p['id']} {p['name']} {p['city']} "
                            f"{p['country']} port".lower()})
    for v in VOLCANOES:
        rows.append({"kind": "volcano", "id": v["id"],
                     "label": f"{v['name']} volcano ({v['country']})",
                     "lat": v["lat"], "lon": v["lon"],
                     "hay": f"{v['id']} {v['name']} {v['country']} "
                            f"volcano".lower()})
    for c in COUNTRIES:
        rows.append({"kind": "country", "id": f"CTRY-{c['name']}",
                     "label": c["name"], "lat": c["lat"], "lon": c["lon"],
                     "hay": f"{c['name']} country".lower()})
    for s in SAT_CATALOG:
        rows.append({"kind": "satellite", "id": f"SAT-{s}",
                     "label": f"{s} (public catalog label)",
                     "lat": None, "lon": None,
                     "hay": f"{s} satellite".lower()})
    for src in ("usgs-earthquakes", "noaa-weather-alerts", "noaa-swpc",
                "nasa-eonet", "gdacs-alerts", "reliefweb-reports",
                "copernicus-ems", "nasa-firms", "opensky-network",
                "synthetic-world"):
        rows.append({"kind": "source", "id": src,
                     "label": f"source: {src}", "lat": None, "lon": None,
                     "hay": f"{src} source".lower()})
    return rows


def search_world(query: str, payload: Dict[str, Any] | None = None,
                 limit: int = 12) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q or len(q) < 2:
        return []
    # persons / private addresses are never searchable: fail closed.
    blocked = ("cctv", "rtsp", "onvif", "password", "plate", "face",
               "person", "phone", "wifi", "bluetooth")
    if any(tok in q for tok in blocked):
        return [{"kind": "blocked", "id": "BLOCKED",
                 "label": "Query class is out of scope (public data only).",
                 "lat": None, "lon": None}]
    out: List[Dict[str, Any]] = []
    for row in _gazetteer():
        if q in row["hay"]:
            out.append({k: row[k] for k in ("kind", "id", "label",
                                           "lat", "lon")})
            if len(out) >= limit:
                return out
    if payload:
        pools: List[Tuple[str, List[Dict[str, Any]]]] = [
            ("aircraft", payload.get("aircraft", [])),
            ("vessel", payload.get("vessels", [])),
            ("satellite", payload.get("satellites", [])),
            ("disaster", payload.get("disasters", [])),
            ("event", payload.get("notices", [])),
        ]
        for kind, items in pools:
            for o in items:
                oid = str(o.get("id", "")).lower()
                extra = str(o.get("callsign", o.get("name", o.get("title",
                            "")))).lower()
                if q in oid or (extra and q in extra):
                    out.append({"kind": kind, "id": o.get("id"),
                                "label": f"{o.get('id')} "
                                         f"({o.get('callsign', o.get('name', o.get('title', '')))})",
                                "lat": o.get("lat"), "lon": o.get("lon")})
                    if len(out) >= limit:
                        return out
    return out


def region_overview(selector: str,
                    payload: Dict[str, Any]) -> Dict[str, Any]:
    s = (selector or "").strip().lower()
    center: Tuple[float, float] | None = None
    label = selector or "UNKNOWN"
    hit = match_country(s)
    if hit is not None:
        center = (hit["lat"], hit["lon"])
        label = hit["name"]
    if center is None:
        for a in AIRPORTS + PORTS:  # type: ignore[operator]
            hay = f"{a['name']} {a.get('city', '')} {a.get('country', '')}".lower()
            toks = set(hay.replace(",", " ").replace("-", " ").split())
            if s and (s in toks or (len(s) > 3 and s in hay)):
                center = (a["lat"], a["lon"])
                label = a.get("country", a["name"])
                break
    if center is None:
        return {"region": label, "status": "UNKNOWN",
                "note": "no matching public region in gazetteer",
                "counts": {}, "alerts": [], "truth_mode": TRUTH_MODE}
    lat0, lon0 = center
    radius_km = 1200.0
    nearby: Dict[str, int] = {"aircraft": 0, "vessels": 0, "alerts": 0,
                              "quakes": 0, "fires": 0, "notices": 0}
    for o in payload.get("aircraft", []):
        if _haversine_km(lat0, lon0, o["lat"], o["lon"]) <= radius_km:
            nearby["aircraft"] += 1
    for o in payload.get("vessels", []):
        if _haversine_km(lat0, lon0, o["lat"], o["lon"]) <= radius_km:
            nearby["vessels"] += 1
    for o in payload.get("seismic", []):
        if _haversine_km(lat0, lon0, o["lat"], o["lon"]) <= radius_km:
            nearby["quakes"] += 1
    for o in payload.get("wildfire", []):
        if _haversine_km(lat0, lon0, o["lat"], o["lon"]) <= radius_km:
            nearby["fires"] += 1
    alerts = [a for a in payload.get("weather", {}).get("alerts", [])]
    return {"region": label, "center": {"lat": lat0, "lon": lon0},
            "radius_km": radius_km, "counts": nearby,
            "active_alerts": alerts[:4],
            "disasters": payload.get("disasters", [])[:3],
            "source_health": "see /api/world/health",
            "coverage": next(
                (b for b in blindspot_grid()
                 if label.lower() in b["region"].lower()),
                {"status": "PARTIAL",
                 "reason": "synthetic density; live legs opt-in"}),
            "truth_mode": TRUTH_MODE,
            "truth_label": TRUTH_LABEL}


def whats_here(lat: float, lon: float, radius_km: float,
               payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        la, lo, r = float(lat), float(lon), float(radius_km)
    except (TypeError, ValueError):
        return {"error": "invalid coordinates", "items": []}
    r = max(5.0, min(1500.0, r))
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "aircraft_density": [], "vessels": [], "weather": [],
        "earth_events": [], "alerts": [], "notices": [],
        "infrastructure": [], "satellite_coverage": [],
    }
    for o in payload.get("aircraft", []):
        if _haversine_km(la, lo, o["lat"], o["lon"]) <= r:
            buckets["aircraft_density"].append(o["id"])
    for o in payload.get("vessels", []):
        if _haversine_km(la, lo, o["lat"], o["lon"]) <= r:
            buckets["vessels"].append(o["id"])
    for o in payload.get("weather", {}).get("cells", []):
        if _haversine_km(la, lo, o["lat"], o["lon"]) <= r + 200:
            buckets["weather"].append(o["id"])
    for o in payload.get("seismic", []) + payload.get("wildfire", []) + \
            payload.get("volcanoes", []):
        if o.get("lat") is not None and \
                _haversine_km(la, lo, o["lat"], o["lon"]) <= r:
            buckets["earth_events"].append(o["id"])
    for a in payload.get("weather", {}).get("alerts", []):
        buckets["alerts"].append(a["id"])
    for o in payload.get("notices", []):
        if _haversine_km(la, lo, o["lat"], o["lon"]) <= r:
            buckets["notices"].append(o["id"])
    for o in payload.get("airports", []) + payload.get("ports", []):
        if _haversine_km(la, lo, o["lat"], o["lon"]) <= r:
            buckets["infrastructure"].append(o["id"])
    for o in payload.get("satellites", [])[:10]:
        buckets["satellite_coverage"].append(o["id"])
    summary = {k: len(v) for k, v in buckets.items()}
    return {"at": {"lat": la, "lon": lo}, "radius_km": r,
            "summary": summary,
            "sample_ids": {k: v[:6] for k, v in buckets.items()},
            "note": "public observations only; every id links to evidence; "
                    "no inference",
            "truth_mode": TRUTH_MODE, "truth_label": TRUTH_LABEL}


def event_feed(payload: Dict[str, Any], category: str = "GLOBAL",
               limit: int = 60) -> List[Dict[str, Any]]:
    cat = (category or "GLOBAL").upper()
    items: List[Dict[str, Any]] = []
    for q in payload.get("seismic", []):
        items.append({"id": q["id"], "kind": "EARTH",
                      "title": f"M{q['mag']} synthetic quake",
                      "severity": q.get("severity", 3),
                      "lat": q["lat"], "lon": q["lon"],
                      "time": q.get("event_time", "UNKNOWN"),
                      "corroboration": "ONE SOURCE"})
    for d in payload.get("disasters", []):
        items.append({"id": d["id"], "kind": "DISASTER",
                      "title": d["title"], "severity": 5,
                      "lat": d["lat"], "lon": d["lon"],
                      "time": "synthetic-t0",
                      "corroboration": d.get("corroboration",
                                             "MULTIPLE SOURCES")})
    for a in payload.get("weather", {}).get("alerts", []):
        items.append({"id": a["id"], "kind": "WEATHER",
                      "title": a["title"], "severity": 4,
                      "lat": None, "lon": None,
                      "time": a.get("valid_from", "UNKNOWN"),
                      "corroboration": "ONE SOURCE"})
    for f in payload.get("wildfire", []):
        items.append({"id": f["id"], "kind": "EARTH",
                      "title": f"synthetic hotspot {f['id']}",
                      "severity": 3, "lat": f["lat"], "lon": f["lon"],
                      "time": f.get("observed", "UNKNOWN"),
                      "corroboration": "ONE SOURCE"})
    for t in payload.get("transit", [])[:200]:
        items.append({"id": t["id"], "kind": "INFRASTRUCTURE",
                      "title": f"{t['kind']} — {t['city']}",
                      "severity": t.get("severity", 2),
                      "lat": t["lat"], "lon": t["lon"],
                      "time": t.get("reported", "UNKNOWN"),
                      "corroboration": "ONE SOURCE"})
    for n in payload.get("notices", []):
        items.append({"id": n["id"], "kind": "PUBLIC NOTICE",
                      "title": n["title"], "severity": 2,
                      "lat": n["lat"], "lon": n["lon"],
                      "time": n.get("issued", "UNKNOWN"),
                      "corroboration": "ONE SOURCE"})
    for v in payload.get("volcanoes", []):
        if v.get("alert_level", "NORMAL") != "NORMAL":
            items.append({"id": v["id"], "kind": "EARTH",
                          "title": f"{v['name']} {v['alert_level']}",
                          "severity": 4, "lat": v["lat"], "lon": v["lon"],
                          "time": v.get("observed", "UNKNOWN"),
                          "corroboration": "ONE SOURCE"})
    if cat != "GLOBAL":
        want = {"WEATHER": ("WEATHER",), "EARTH": ("EARTH",),
                "DISASTER": ("DISASTER",), "MOVEMENT": (),
                "INFRASTRUCTURE": ("INFRASTRUCTURE",),
                "PUBLIC NOTICE": ("PUBLIC NOTICE",)}.get(cat, None)
        if want is not None:
            items = [i for i in items if i["kind"] in want]
    items.sort(key=lambda i: (-i["severity"], i["id"]))
    return items[:max(1, min(200, limit))]


def evidence_for_world(obj_id: str,
                       payload: Dict[str, Any]) -> Dict[str, Any]:
    pools: List[Dict[str, Any]] = []
    for key in ("aircraft", "vessels", "seismic", "wildfire", "volcanoes",
                "satellites", "notices", "disasters", "transit",
                "air_quality", "airports", "ports"):
        items = payload.get(key, [])
        if isinstance(items, list):
            pools.extend(items)
    for cell in payload.get("weather", {}).get("cells", []):
        pools.append(cell)
    for alert in payload.get("weather", {}).get("alerts", []):
        poly = alert.get("polygon") or []
        lat = sum(p[0] for p in poly) / len(poly) if poly else None
        lon = sum(p[1] for p in poly) / len(poly) if poly else None
        pools.append({**alert, "lat": lat, "lon": lon})
    for o in pools:
        if o.get("id") == obj_id:
            lat, lon = o.get("lat"), o.get("lon")
            if (lat is None or lon is None) and o.get("footprint"):
                pts = o["footprint"]
                lat = round(sum(p[0] for p in pts) / len(pts), 3)
                lon = round(sum(p[1] for p in pts) / len(pts), 3)
            return {
                "what": f"{o.get('category', 'object')} {obj_id}",
                "where": {"lat": lat, "lon": lon},
                "when": o.get("source_event_time")
                or o.get("event_time") or o.get("observed")
                or o.get("issued") or o.get("epoch") or "UNKNOWN",
                "first_seen": o.get("first_seen", "synthetic-t0"),
                "ingested_at": o.get("ingested_at", "UNKNOWN"),
                "effective_time": o.get("source_event_time", "UNKNOWN"),
                "source": o.get("source", PROVENANCE),
                "rights": o.get("rights", RIGHTS),
                "provenance": o.get("provenance", PROVENANCE),
                "observation": o.get("observation", "UNKNOWN"),
                "observation_type": o.get("observation_type", "UNKNOWN"),
                "truth_mode": TRUTH_MODE,
                "truth_label": TRUTH_LABEL,
                "confidence": "demo-fixed",
                "precision": o.get("precision", "APPROXIMATE"),
                "corroboration": o.get("corroboration",
                                       "single synthetic source"),
                "contradictions": "none in demo",
                "blind_spots": ["fringe coverage (synthetic)",
                                "live legs not polled in base demo"],
                "exportable": True,
            }
    return {"what": f"object {obj_id}", "where": {"lat": None, "lon": None},
            "when": "UNKNOWN", "first_seen": "UNKNOWN",
            "source": PROVENANCE, "rights": RIGHTS,
            "observation": "UNKNOWN", "observation_type": "UNKNOWN",
            "truth_mode": TRUTH_MODE, "truth_label": TRUTH_LABEL,
            "corroboration": "UNKNOWN", "exportable": True}
