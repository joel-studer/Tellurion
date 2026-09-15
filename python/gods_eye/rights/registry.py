"""
Data-Rights-Registry für Project GOD'S EYE (Phase 3G).

Software-Lizenz und DATENRECHTE strikt getrennt. Je Quelle alle 12 Felder;
UNKNOWN bei Unsicherheit (niemals raten). Eingaben u. a. aus dem
OSS-Harvest (gods-eye-view DATA_SOURCES.md: OpenSky nicht-kommerziell!,
adsb.lol ODbL, Google-News nur persönlich/nicht-kommerziell, GDELT ok mit
Zitierung) sowie eigenen Live-Verifikationen.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

# NOTE: registry.py is standalone; it stamps no package version.


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
    # Harvest (gods-eye-view DATA_SOURCES.md, verifiziert gelesen):
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
