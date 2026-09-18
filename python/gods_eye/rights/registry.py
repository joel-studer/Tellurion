"""Data rights registry for Tellurion.

Software licence and DATA RIGHTS are tracked strictly separately. Every
source carries all 12 fields; anything uncertain stays UNKNOWN, never
guessed, and an UNKNOWN source is refused at run time rather than fetched.

Entries come from published terms read directly (OpenSky: non-commercial;
adsb.lol: ODbL; Google News: personal, non-commercial only; GDELT: allowed
with citation) plus this project's own live verifications.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

# NOTE (V17): no module-scope version-stamp import here — the public
# preview ships registry.py standalone and the stamp was unused.


@dataclass(frozen=True)
class SourceRights:
    source_id: str
    commercial_use: str      # "yes" | "no" | "UNKNOWN"
    storage: str             # "yes" | "transient-only" | "UNKNOWN"
    derived_data: str
    redistribution: str
    ml_use: str
    attribution: str
    geographic_restrictions: str
    rate_limits: str
    retention_constraints: str
    rights_basis: str
    rights_source: str
    verified_at: str
    confidence: float


def _r(source_id: str, **kw) -> SourceRights:
    base = {"commercial_use": "UNKNOWN", "storage": "UNKNOWN",
            "derived_data": "UNKNOWN", "redistribution": "UNKNOWN",
            "ml_use": "UNKNOWN", "attribution": "UNKNOWN",
            "geographic_restrictions": "UNKNOWN", "rate_limits": "UNKNOWN",
            "retention_constraints": "UNKNOWN", "rights_basis": "UNKNOWN",
            "rights_source": "", "verified_at": "2026-09-11",
            "confidence": 0.8}
    base.update(kw)
    return SourceRights(source_id=source_id, **base)


REGISTRY: Dict[str, SourceRights] = {
    "sec_edgar_8k": _r("sec_edgar_8k", commercial_use="yes", storage="yes",
                       derived_data="yes", redistribution="yes", ml_use="yes",
                       attribution="NONE",
                       rights_basis="17 U.S.C. Sec. 105 / SEC EDGAR Public Domain",
                       rights_source="https://www.sec.gov/edgar.shtml", confidence=1.0),
    "us_government_procurement": _r("us_government_procurement", commercial_use="yes",
                                    storage="yes", derived_data="yes", redistribution="yes",
                                    ml_use="yes", attribution="NONE",
                                    rights_basis="17 U.S.C. Sec. 105 (public domain)",
                                    rights_source="https://www.usa.gov/government-works",
                                    rate_limits="fair use, schonend pollen", confidence=1.0),
    "fed_press_releases": _r("fed_press_releases", commercial_use="yes", storage="yes",
                             derived_data="yes", redistribution="yes", ml_use="yes",
                             attribution="NONE",
                             rights_basis="17 U.S.C. Sec. 105 (Board work, public domain)",
                             rights_source="https://www.federalreserve.gov/aboutthefed/k8.htm",
                             confidence=0.9),
    "fed_speeches": _r("fed_speeches", commercial_use="yes", storage="yes",
                       derived_data="yes", redistribution="yes", ml_use="yes",
                       attribution="NONE",
                       rights_basis="17 U.S.C. Sec. 105 (Board work, public domain)",
                       rights_source="https://www.federalreserve.gov/aboutthefed/k8.htm",
                       confidence=0.9),
    "boe_news": _r("boe_news", commercial_use="yes", storage="yes",
                   derived_data="yes", redistribution="yes", ml_use="yes",
                   attribution="Contains public sector information licensed under the OGL v3.0",
                   rights_basis="UK Open Government Licence v3.0",
                   rights_source="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
                   confidence=0.9),
    # Terms read directly from each provider:
    "adsb_lol_snapshot": _r("adsb_lol_snapshot", commercial_use="yes", storage="yes",
                            derived_data="yes", redistribution="yes", ml_use="yes",
                            attribution="adsb.lol contributors (ODbL)",
                            rights_basis="ODbL 1.0 (Share-Alike auf Daten!)",
                            rights_source="https://adsb.lol/",
                            retention_constraints="Share-Alike bei Weitergabe abgeleiteter DB",
                            confidence=0.8),
    "opensky_snapshot": _r("opensky_snapshot", commercial_use="no",
                           storage="transient-only", derived_data="UNKNOWN",
                           redistribution="no", ml_use="UNKNOWN",
                           attribution="Schäfer et al., IPSN 2014 + opensky-network.org",
                           rights_basis="OpenSky non-commercial research/education license",
                           rights_source="https://opensky-network.org/",
                           rate_limits="anonym limitiert; Produkt-Einsatz nur mit Vereinbarung",
                           confidence=0.9),
    "pc_stac_sentinel2": _r("pc_stac_sentinel2", commercial_use="yes", storage="yes",
                            derived_data="yes", redistribution="yes", ml_use="yes",
                            attribution="Copernicus Sentinel data",
                            rights_basis="Copernicus Sentinel-Daten (frei, EU-Programm)",
                            rights_source="https://dataspace.copernicus.eu/",
                            confidence=0.8),
    "yfinance_market": _r("yfinance_market", commercial_use="UNKNOWN", storage="transient-only",
                          derived_data="yes", redistribution="no", ml_use="UNKNOWN",
                          attribution="Yahoo Finance (via yfinance)",
                          rights_basis="Yahoo-ToS (Umverteilung eingeschränkt); Klärung offen",
                          rights_source="https://legal.yahoo.com/",
                          rate_limits="fair use, Drosselung beobachtet",
                          retention_constraints="kein Dauerarchiv für Roh-Bars zugesagt",
                          confidence=0.6),
    # Phase 4: neue Sensoren/Abhängigkeiten
    "faa_asws": _r("faa_asws", commercial_use="yes", storage="yes",
                   derived_data="yes", redistribution="yes", ml_use="yes",
                   attribution="Federal Aviation Administration",
                   rights_basis="17 U.S.C. Sec. 105 (Bundeswerk); ENDPOINT LIVE UNVERIFIZIERT (DNS-fail)",
                   rights_source="https://www.faa.gov/",
                   rate_limits="UNKNOWN", confidence=0.5),
    "carbonintensity_gb": _r("carbonintensity_gb", commercial_use="UNKNOWN", storage="yes",
                             derived_data="yes", redistribution="UNKNOWN", ml_use="UNKNOWN",
                             attribution="National Grid ESO (prüfen)",
                             rights_basis="UNKNOWN (Lizenzseite nicht verifiziert)",
                             rights_source="https://carbonintensity.org.uk/",
                             confidence=0.4),
    "lib_trafilatura": _r("lib_trafilatura", commercial_use="yes", storage="yes",
                          derived_data="yes", redistribution="yes", ml_use="yes",
                          attribution="trafilatura authors",
                          rights_basis="Software-Dependency, kein Datenlieferant (Apache-2.0 lt. Projekt, verifizieren)",
                          rights_source="https://pypi.org/project/trafilatura/",
                          confidence=0.7),
    "lib_pystac_client": _r("lib_pystac_client", commercial_use="yes", storage="yes",
                            derived_data="yes", redistribution="yes", ml_use="yes",
                            attribution="pystac authors",
                            rights_basis="Software-Dependency, kein Datenlieferant (Apache-2.0 lt. Projekt, verifizieren)",
                            rights_source="https://pypi.org/project/pystac-client/",
                            confidence=0.7),
    "lib_pyais": _r("lib_pyais", commercial_use="yes", storage="yes",
                     derived_data="yes", redistribution="yes", ml_use="yes",
                     attribution="M0r13n (MIT)",
                     rights_basis="Software-Dependency, kein Datenlieferant (MIT)",
                     rights_source="https://pypi.org/project/pyais/",
                     confidence=0.9),
    # World-coverage harvest (public-safe only; terms URLs in WORLD_SOURCE_MATRIX.md)
    "usgs_earthquakes": _r("usgs_earthquakes", commercial_use="yes", storage="yes",
                           derived_data="yes", redistribution="yes", ml_use="yes",
                           attribution="USGS Earthquake Hazards Program",
                           rights_basis="17 U.S.C. Sec. 105 (public domain)",
                           rights_source="https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
                           rate_limits="polite polling; 20k catalog cap",
                           retention_constraints="keep fetch timestamps; feed lifecycle",
                           confidence=1.0),
    "nws_alerts": _r("nws_alerts", commercial_use="yes", storage="yes",
                     derived_data="yes", redistribution="yes", ml_use="yes",
                     attribution="National Weather Service",
                     rights_basis="17 U.S.C. Sec. 105 (public domain); User-Agent required",
                     rights_source="https://www.weather.gov/documentation/services-web-api",
                     rate_limits="polite polling", confidence=1.0),
    "noaa_swpc": _r("noaa_swpc", commercial_use="yes", storage="yes",
                    derived_data="yes", redistribution="yes", ml_use="yes",
                    attribution="NOAA SWPC",
                    rights_basis="17 U.S.C. Sec. 105 (public domain)",
                    rights_source="https://www.swpc.noaa.gov/content/data-access",
                    rate_limits="polite; per-product cadence", confidence=0.95),
    "nasa_eonet": _r("nasa_eonet", commercial_use="yes", storage="yes",
                     derived_data="yes", redistribution="yes", ml_use="yes",
                     attribution="NASA EONET",
                     rights_basis="US government open metadata; imagery per linked source",
                     rights_source="https://eonet.gsfc.nasa.gov/docs/v3",
                     rate_limits="paginate limit/days", confidence=0.85),
    "gdacs_alerts": _r("gdacs_alerts", commercial_use="UNKNOWN", storage="yes",
                       derived_data="yes", redistribution="yes", ml_use="yes",
                       attribution="GDACS (UN OCHA / EC JRC)",
                       rights_basis="EU CC BY 4.0 in-band notice (credit GDACS); summary+link ok, no bulk mirror",
                       rights_source="https://www.gdacs.org/About/termofuse.aspx",
                       confidence=0.85),
    "reliefweb": _r("reliefweb", commercial_use="UNKNOWN", storage="yes",
                    derived_data="yes", redistribution="yes", ml_use="yes",
                    attribution="UN OCHA ReliefWeb + origin",
                    rights_basis="free with attribution; origin docs per terms",
                    rights_source="https://reliefweb.int/help/api",
                    confidence=0.85),
    "copernicus_ems": _r("copernicus_ems", commercial_use="yes", storage="yes",
                         derived_data="yes", redistribution="yes", ml_use="yes",
                         attribution="Copernicus EMS",
                         rights_basis="Copernicus free full open use",
                         rights_source="https://emergency.copernicus.eu/",
                         confidence=0.9),
    "usgs_volcanoes": _r("usgs_volcanoes", commercial_use="yes", storage="yes",
                         derived_data="yes", redistribution="yes", ml_use="yes",
                         attribution="USGS Volcano Hazards Program",
                         rights_basis="17 U.S.C. Sec. 105 (public domain)",
                         rights_source="https://www.usgs.gov/volcanoes",
                         confidence=0.95),
    "epa_airnow": _r("epa_airnow", commercial_use="yes", storage="yes",
                     derived_data="yes", redistribution="yes", ml_use="yes",
                     attribution="US EPA AirNow",
                     rights_basis="US public domain (federal portion)",
                     rights_source="https://www.airnow.gov/",
                     confidence=0.9),
    "eea_airquality": _r("eea_airquality", commercial_use="yes", storage="yes",
                         derived_data="yes", redistribution="yes", ml_use="yes",
                         attribution="European Environment Agency",
                         rights_basis="EU open data reuse",
                         rights_source="https://www.eea.europa.eu/en/datahub",
                         confidence=0.85),
    "osm_overpass": _r("osm_overpass", commercial_use="yes", storage="yes",
                       derived_data="yes", redistribution="yes", ml_use="yes",
                       attribution="(c) OpenStreetMap contributors",
                       rights_basis="ODbL 1.0 (Share-Alike auf abgeleiteter DB)",
                       rights_source="https://www.openstreetmap.org/copyright",
                       rate_limits="tile politely; cache; self-host heavy use",
                       retention_constraints="Share-Alike bei Weitergabe abgeleiteter DB",
                       confidence=0.9),
    "gtfs_static": _r("gtfs_static", commercial_use="UNKNOWN", storage="yes",
                      derived_data="yes", redistribution="UNKNOWN", ml_use="yes",
                      attribution="per-agency (verify feed)",
                      rights_basis="UNKNOWN per feed (meist offen; je Agency pruefen)",
                      rights_source="per-agency terms",
                      confidence=0.6),
    "nasa_firms": _r("nasa_firms", commercial_use="UNKNOWN", storage="yes",
                     derived_data="yes", redistribution="UNKNOWN", ml_use="UNKNOWN",
                     attribution="NASA LANCE FIRMS (user key)",
                     rights_basis="per-user MAP_KEY terms; key never shared/bundled",
                     rights_source="https://firms.modaps.eosdis.nasa.gov/api/",
                     rate_limits="5000 tx / 10 min / key",
                     confidence=0.7),
    "celestrak": _r("celestrak", commercial_use="UNKNOWN", storage="UNKNOWN",
                    derived_data="UNKNOWN", redistribution="UNKNOWN", ml_use="UNKNOWN",
                    attribution="CelesTrak",
                    rights_basis="UNKNOWN (TERMS REVIEW REQUIRED before any use)",
                    rights_source="https://celestrak.org/",
                    confidence=0.4),
    "gdelt": _r("gdelt", commercial_use="yes", storage="yes",
                derived_data="yes", redistribution="yes", ml_use="yes",
                attribution="GDELT Project + link https://www.gdeltproject.org/ (mandatory citation)",
                rights_basis="open platform: unlimited academic/commercial/governmental use; redistribution with citation (verified 2026-09-16)",
                rights_source="https://www.gdeltproject.org/about.html#termsofuse",
                rate_limits="max 1 req / 5 s (429 observed); Tellurion polls 1x / 30 min",
                retention_constraints="reported events only; never ground truth",
                confidence=0.85),
    "openaq": _r("openaq", commercial_use="UNKNOWN", storage="yes",
                 derived_data="yes", redistribution="UNKNOWN", ml_use="UNKNOWN",
                 attribution="OpenAQ",
                 rights_basis="UNKNOWN (v3 terms review required)",
                 rights_source="https://openAQ.org/",
                 confidence=0.5),
    "adsb_lol_live": _r("adsb_lol_live", commercial_use="yes", storage="yes",
                        derived_data="yes", redistribution="yes", ml_use="yes",
                        attribution="adsb.lol contributors (ODbL)",
                        rights_basis="ODbL 1.0 for API + public data; display + transient cache (verified 2026-09-16)",
                        rights_source="https://api.adsb.lol/docs",
                        rate_limits="dynamic by load; 4xx means back off; Tellurion: 8 tiles/120 s + squawk/60 s + mil/120 s",
                        retention_constraints="transient TTL cache + rolling ~15 min memory trails; no disk persistence of tracks; bulk export refused in-app",
                        confidence=0.9),
    "airplanes_live": _r("airplanes_live", commercial_use="no", storage="yes",
                         derived_data="yes", redistribution="UNKNOWN", ml_use="UNKNOWN",
                         attribution="airplanes.live",
                         rights_basis="free REST API is Non-Commercial Use, no SLA (verified 2026-09-16); standby fallback only",
                         rights_source="https://airplanes.live/terms-of-use/",
                         rate_limits="1 request/second",
                         confidence=0.7),
}


def lookup(source_id: str) -> Optional[SourceRights]:
    return REGISTRY.get(source_id)


def check_event_rights(source_id: str, claims: Dict[str, str]) -> List[str]:
    """Prüft Event-Behauptungen gegen Registry; meldet Lücken (leere Liste = sauber)."""
    issues: List[str] = []
    rec = REGISTRY.get(source_id)
    if rec is None:
        return [f"UNREGISTERED_SOURCE:{source_id}"]
    for field in ("commercial_use", "storage", "redistribution", "ml_use"):
        claimed = (claims.get(field) or "").lower()
        allowed = getattr(rec, field).lower()
        if allowed == "unknown" and claimed in ("true", "yes", "1"):
            issues.append(f"UNVERIFIED_CLAIM:{field} (Registry=UNKNOWN)")
        if allowed == "no" and claimed in ("true", "yes", "1"):
            issues.append(f"RIGHTS_VIOLATION:{field} (Registry=no)")
    return issues
