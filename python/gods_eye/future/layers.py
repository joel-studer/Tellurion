"""FUTURE-ONLY Ultra world-layer contracts (V18, open-core safe).

A WorldLayer is a *display + provenance* contract: what the world
surface may render, how fresh it is, who owns the rights, and how
uncertain it is. Layers never carry alpha, ranking, or timing logic —
cross-sensor context is descriptive proximity, not inference.

Observation vocabulary (binding): every rendered object is one of
OBSERVED / INFERRED / CORROBORATED / UNKNOWN. Anything else is a bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

OBSERVATION_STATES = ("OBSERVED", "INFERRED", "CORROBORATED", "UNKNOWN")

LAYER_CATEGORIES = ("AIRCRAFT", "MARITIME", "SATELLITE", "WEATHER",
                    "RADAR", "WILDFIRE", "SEISMIC", "VOLCANO", "TRAFFIC", "ROAD",
                    "TRANSIT", "PUBLIC_CAMERA", "PORT", "AIRPORT",
                    "INFRASTRUCTURE", "ENERGY", "AIR_QUALITY",
                    "SPACE_WEATHER", "SPACE", "GOVERNMENT", "DISASTER",
                    "FLOOD", "TSUNAMI", "STORM", "HUMANITARIAN", "NEWS",
                    "MILITARY_PUBLIC_OSINT", "EVENT", "ENTITY",
                    "BLIND_SPOT", "UNKNOWN")

LAYER_GROUPS = ("MOVEMENT", "EARTH", "INFRASTRUCTURE", "EVENTS",
                "SOURCES", "INTELLIGENCE")

CATEGORY_GROUP = {
    "AIRCRAFT": "MOVEMENT", "MARITIME": "MOVEMENT", "TRAFFIC": "MOVEMENT",
    "ROAD": "MOVEMENT", "TRANSIT": "MOVEMENT", "SATELLITE": "EARTH",
    "SPACE": "EARTH", "SPACE_WEATHER": "EARTH", "WEATHER": "EARTH",
    "STORM": "EARTH", "RADAR": "EARTH", "WILDFIRE": "EARTH",
    "SEISMIC": "EARTH", "VOLCANO": "EARTH", "FLOOD": "EARTH",
    "TSUNAMI": "EARTH", "DISASTER": "EARTH", "AIR_QUALITY": "EARTH",
    "PORT": "INFRASTRUCTURE", "HUMANITARIAN": "EVENTS", "NEWS": "EVENTS",
    "AIRPORT": "INFRASTRUCTURE", "INFRASTRUCTURE": "INFRASTRUCTURE",
    "ENERGY": "INFRASTRUCTURE", "PUBLIC_CAMERA": "SOURCES",
    "GOVERNMENT": "SOURCES", "EVENT": "EVENTS", "ENTITY": "EVENTS",
    "MILITARY_PUBLIC_OSINT": "INTELLIGENCE", "BLIND_SPOT": "INTELLIGENCE",
    "UNKNOWN": "EVENTS",
}

# Data-source truth model: every source declares one of these.
# LIVE = real-time qualified feed; DELAYED = qualified feed with lag;
# STATIC = timetable/geography snapshot; REPLAY = deterministic fixture
# playback; SYNTHETIC = generated demo world (never presented as live).
TRUTH_MODES = ("LIVE", "DELAYED", "STATIC", "REPLAY", "SYNTHETIC")

# Observation vocabulary for world objects (binding on new world paths;
# legacy OBSERVED/INFERRED/CORROBORATED/UNKNOWN mapping is preserved):
# OBSERVED = sensor saw it; PUBLIC_REPORT = press/community report;
# GOVERNMENT_NOTICE = official notice; NEWS_REPORT = news metadata
# (e.g. GDELT); INFERRED = modeled/derived; CORROBORATED = multi-source;
# UNKNOWN = unstated.
OBSERVATION_TYPES = ("OBSERVED", "PUBLIC_REPORT", "GOVERNMENT_NOTICE",
                     "NEWS_REPORT", "INFERRED", "CORROBORATED", "UNKNOWN")

# Corroboration wording (UI must use exactly these tokens).
CORROBORATION_STATES = ("ONE SOURCE", "MULTIPLE SOURCES", "CORROBORATED",
                        "CONFLICTING", "UNKNOWN")

TIME_MODES = ("LIVE", "DELAYED", "STATIC", "REPLAY", "SYNTHETIC")

HEALTH_STATES = ("OK", "DEGRADED", "STALE", "OFFLINE", "RIGHTS_BLOCKED",
                 "BLIND")

PRECISION = ("EXACT", "APPROXIMATE", "REGIONAL", "UNKNOWN")


@dataclass(frozen=True)
class LayerCapability:
    kind: str            # points | tracks | polygons | raster | feed | graph
    realtime: bool = False
    replayable: bool = True


@dataclass(frozen=True)
class LayerHealth:
    state: str           # one of HEALTH_STATES
    object_count: int = 0
    last_update: str = "never"
    detail: str = ""


@dataclass(frozen=True)
class LayerRights:
    basis: str           # e.g. "CC0 synthetic", "US public domain", "user-key"
    redistribution: str = "UNKNOWN"
    commercial_use: str = "UNKNOWN"


@dataclass(frozen=True)
class LayerStyle:
    color: str           # hex
    icon: str            # glyph/shape name
    opacity: float = 0.9


@dataclass(frozen=True)
class LayerLegend:
    label: str
    unit: str = ""
    breaks: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class LayerTimeMode:
    mode: str            # one of TIME_MODES
    cursor: str = "now"  # ISO time or "now"


@dataclass(frozen=True)
class LayerProvenance:
    source_id: str
    fetched_at: str = "never"
    observation: str = "UNKNOWN"  # one of OBSERVATION_STATES


@dataclass(frozen=True)
class WorldLayer:
    layer_id: str
    category: str
    title: str
    group: str = ""
    capabilities: LayerCapability = field(
        default_factory=lambda: LayerCapability("points"))
    health: LayerHealth = field(default_factory=lambda: LayerHealth("BLIND"))
    rights: LayerRights = field(
        default_factory=lambda: LayerRights("UNKNOWN"))
    style: LayerStyle = field(
        default_factory=lambda: LayerStyle("#9aa4b2", "dot"))
    legend: LayerLegend = field(
        default_factory=lambda: LayerLegend(""))
    time_mode: LayerTimeMode = field(
        default_factory=lambda: LayerTimeMode("REPLAY"))
    precision: str = "UNKNOWN"
    provenance: LayerProvenance = field(
        default_factory=lambda: LayerProvenance("synthetic-replay"))

    def __post_init__(self) -> None:
        if self.category not in LAYER_CATEGORIES:
            raise ValueError(f"unknown layer category: {self.category}")
        if self.health.state not in HEALTH_STATES:
            raise ValueError(f"unknown health state: {self.health.state}")
        if self.provenance.observation not in OBSERVATION_STATES:
            raise ValueError(
                f"observation must be one of {OBSERVATION_STATES}")
        if self.precision not in PRECISION:
            raise ValueError(f"unknown precision: {self.precision}")
        if self.time_mode.mode not in TIME_MODES:
            raise ValueError(f"unknown time mode: {self.time_mode.mode}")


def default_stack() -> List[WorldLayer]:
    """The demo layer stack: honest defaults, synthetic provenance."""
    specs = [
        ("aircraft", "AIRCRAFT", "Aircraft", "#5aa9ff", "plane"),
        ("maritime", "MARITIME", "Vessels", "#4fd1a5", "ship"),
        ("satellite", "SATELLITE", "Satellite scenes", "#b48cff", "footprint"),
        ("weather", "WEATHER", "Weather + alerts", "#ffc857", "cloud"),
        ("wildfire", "WILDFIRE", "Wildfires", "#ff6b4a", "flame"),
        ("seismic", "SEISMIC", "Earthquakes", "#ff9f68", "pulse"),
        ("traffic", "TRAFFIC", "Road incidents", "#ffd166", "cone"),
        ("cameras", "PUBLIC_CAMERA", "Public cameras", "#8fd0ff", "camera"),
        ("ports", "PORT", "Ports", "#7fe0d4", "anchor"),
        ("airports", "AIRPORT", "Airports", "#a8c8ff", "tower"),
        ("infra", "INFRASTRUCTURE", "Infrastructure", "#c9b8ff", "grid"),
        ("energy", "ENERGY", "Energy / grid", "#ffe08a", "bolt"),
        ("gov", "GOVERNMENT", "Notices", "#d7dce3", "doc"),
        ("disaster", "DISASTER", "Disasters", "#ff8fa3", "alert"),
        ("events", "EVENT", "Events", "#ffffff", "event"),
        ("entities", "ENTITY", "Entities", "#cfe3ff", "node"),
        ("blind", "BLIND_SPOT", "Blind spots", "#6b7280", "blind"),
    ]
    out = []
    for lid, cat, title, color, icon in specs:
        out.append(WorldLayer(
            layer_id=lid, category=cat, title=title,
            group=CATEGORY_GROUP.get(cat, "EVENTS"),
            capabilities=LayerCapability(
                "points", realtime=False, replayable=True),
            health=LayerHealth("OK", 0, "demo-t0",
                               "synthetic replay; no live claims"),
            rights=LayerRights("CC0 synthetic", "permitted", "permitted"),
            style=LayerStyle(color, icon),
            legend=LayerLegend(title),
            time_mode=LayerTimeMode("REPLAY", "now"),
            precision="APPROXIMATE" if cat in ("WEATHER", "DISASTER") else "EXACT",
            provenance=LayerProvenance("synthetic-replay", "demo-t0",
                                       "OBSERVED" if cat in (
                                           "AIRCRAFT", "MARITIME", "SEISMIC",
                                           "EVENT", "ENTITY") else "INFERRED"),
        ))
    return out


def stack_summary() -> Dict[str, Any]:
    stack = default_stack()
    return {"schema": "world-layers-v1", "n_layers": len(stack),
            "categories": sorted({ly.category for ly in stack}),
            "groups": sorted({ly.group for ly in stack}),
            "rule": "observation is always one of "
                    "OBSERVED/INFERRED/CORROBORATED/UNKNOWN"}


def make_observation(source: str,
                     source_event_time: str | None = None,
                     published_time: str | None = None,
                     first_seen: str | None = None,
                     ingested_at: str | None = None,
                     effective_time: str | None = None,
                     precision: str = "UNKNOWN",
                     rights: str = "UNKNOWN",
                     provenance: str = "UNKNOWN",
                     observation_type: str = "UNKNOWN") -> Dict[str, Any]:
    """Truth-model observation envelope (never substitutes ingest for event).

    Unknown timestamps stay the string "UNKNOWN" (never None-mapped to now).
    """
    def _t(v: str | None) -> str:
        return v if v else "UNKNOWN"
    if observation_type not in OBSERVATION_TYPES and observation_type not in \
            OBSERVATION_STATES:
        raise ValueError(f"unknown observation_type: {observation_type}")
    if precision not in PRECISION:
        raise ValueError(f"unknown precision: {precision}")
    return {
        "source": source,
        "source_event_time": _t(source_event_time),
        "published_time": _t(published_time),
        "first_seen": _t(first_seen),
        "ingested_at": _t(ingested_at),
        "effective_time": _t(effective_time or source_event_time),
        "precision": precision,
        "rights": rights,
        "provenance": provenance,
        "observation_type": observation_type,
    }


def truth_label(truth_mode: str) -> str:
    """Human label for a TRUTH_MODES value (fail-closed on unknown)."""
    labels = {
        "LIVE": "LIVE",
        "DELAYED": "DELAYED",
        "STATIC": "STATIC",
        "REPLAY": "REPLAY",
        "SYNTHETIC": "SYNTHETIC WORLD REPLAY",
    }
    if truth_mode not in TRUTH_MODES:
        raise ValueError(f"unknown truth mode: {truth_mode}")
    return labels[truth_mode]
