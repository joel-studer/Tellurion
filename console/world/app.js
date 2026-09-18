/* Tellurion ULTRA world surface: globe-first, evidence-first, time-aware.
 * Synthetic replay data only. The page talks to this localhost server and
 * nothing else; every map asset is vendored. */
import * as maplibreModule from "/vendor/maplibre/maplibre-gl.mjs";

const maplibregl = maplibreModule.default ?? maplibreModule;
const QS = new URLSearchParams(location.search);
const CAPTURE = QS.get("capture") || "";
// The hero story is the default first impression: the globe opens, then flies
// to the scenario with its evidence drawer open. Opt out with ?story=none (or
// ?demo=plain) to land on the bare globe with the event list.
const STORY_PARAM = QS.get("story") ?? (QS.get("demo") === "plain" ? "none" : "port");
const STORY = STORY_PARAM === "none" ? "" : STORY_PARAM;
// WORLD NOW live-data mode (?mode=now, combinable with ?view/?sky/
// ?aircraft/?event/?region=/camera). Declared up top because NAV row
// property values evaluate at init time.
const MODE_NOW = (QS.get("mode") || "").toLowerCase() === "now";
const NOW_VIEW = (QS.get("view") || "").toLowerCase();
const NOW_SKY = (QS.get("sky") || "").toLowerCase();
const SCENE = ["dense", "load5k", "load10k"].includes(QS.get("scene"))
  ? QS.get("scene") : (QS.get("demo") === "dense" ? "dense" : "");
const BENCH = QS.get("bench") === "1";
const REDUCED_MOTION = Boolean(CAPTURE) || matchMedia("(prefers-reduced-motion: reduce)").matches;
const MAX_TICK = 12;
const CAPTURE_TICK = 6;
const EARTH_KM = 6371.0088;

/* ------------------------------------------------------------- catalog */

const ICONS = {
  plane: { fill: true, d: "M12 2.2c.9 0 1.4 1 1.4 2v5.3l7.4 4.4v2.2l-7.4-2.3v4.5l2.3 1.8v1.7L12 21l-3.7.8v-1.7l2.3-1.8v-4.5l-7.4 2.3v-2.2l7.4-4.4V4.2c0-1 .5-2 1.4-2z" },
  ship: { fill: true, d: "M12 2.5 17.5 20 12 16.6 6.5 20z" },
  sat: { fill: false, d: "M8.5 8.5l7 7M3.5 6l2.5-2.5 4 4L7.5 10zM14 16.5l2.5-2.5 4 4-2.5 2.5zM10.5 13.5a2.5 2.5 0 0 0 3-3" },
  anchor: { fill: false, d: "M12 7.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 7.5V21M5 13a7 7 0 0 0 14 0M8.5 11h7" },
  airport: { fill: false, d: "M12 3v18M6 9l6-3 6 3M4 16l8-3 8 3M9 21h6" },
  cone: { fill: true, d: "M10 3h4l4.5 15h-13zM4 18.5h16V21H4z" },
  camera: { fill: true, d: "M3.5 7h12v10h-12zM15.5 10.5l5-3v9l-5-3z" },
  fire: { fill: true, d: "M12 2.5c1.8 3.4 6 5.8 6 11a6 6 0 0 1-12 0c0-2.8 1.6-4.6 2.7-6.3.6 1.9 1.6 3 2.8 3-.8-2.8-.4-5.2.5-7.7z" },
  quake: { fill: false, d: "M2 12h4l2.2-6.5 3.3 13 3.1-9.5 1.9 3H22" },
  notice: { fill: false, d: "M6.5 3h8.5l3 3v15H6.5zM9.5 11h5M9.5 15h5" },
  change: { fill: false, d: "M12 4l9 16H3zM12 10v4M12 17.2v.1" },
  cloud: { fill: true, d: "M7 18.5a4.2 4.2 0 0 1-.7-8.3 6.2 6.2 0 0 1 11.8 1.7 3.4 3.4 0 0 1-.4 6.6z" },
  storm: { fill: false, d: "M4 12a8 8 0 1 1 8 8M12 8a4 4 0 1 0 4 4" },
  globe: { fill: false, d: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3.5 9h17M3.5 15h17M12 3c2.5 2.6 3.7 5.6 3.7 9s-1.2 6.4-3.7 9c-2.5-2.6-3.7-5.6-3.7-9S9.5 5.6 12 3z" },
  signal: { fill: false, d: "M3.5 18a8.5 8.5 0 0 1 17 0M7.5 18a4.5 4.5 0 0 1 9 0M12 17.9v.1" },
  hatch: { fill: false, d: "M4 4h16v16H4zM4 12l8-8M4 20 20 4M12 20l8-8" },
  pin: { fill: false, d: "M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" },
  search: { fill: false, d: "M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zM20 20l-4.8-4.8" },
  play: { fill: true, d: "M8 5.5v13l10.5-6.5z" },
  pause: { fill: true, d: "M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" },
  focus: { fill: false, d: "M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" },
  reset: { fill: false, d: "M4.5 12a7.5 7.5 0 1 0 2.2-5.3M4.5 4v4.5H9" },
  follow: { fill: false, d: "M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4M12 9v6M9 12h6" },
  close: { fill: false, d: "M6 6l12 12M18 6 6 18" },
  back: { fill: false, d: "M15 5 8 12l7 7" },
  chevron: { fill: false, d: "M9 6l6 6-6 6" },
  graph: { fill: false, d: "M6 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM18 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM17 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM8.4 6.2l7.2-.9M7.7 8.6l7.8 8.3" },
  clock: { fill: false, d: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17zM12 7.5V12l3 2" },
};

const CATEGORY = {
  AIR: { label: "Aircraft", color: "#6aa8ff", icon: "plane" },
  MARITIME: { label: "Maritime", color: "#37d2b0", icon: "ship" },
  SPACE: { label: "Space", color: "#b79cff", icon: "sat" },
  WEATHER: { label: "Weather", color: "#9ec7e8", icon: "cloud" },
  EARTH: { label: "Earth", color: "#ff8a5b", icon: "quake" },
  INFRASTRUCTURE: { label: "Infrastructure", color: "#c9b38a", icon: "anchor" },
  ROADS: { label: "Roads", color: "#e2c26f", icon: "cone" },
  CAMERA: { label: "Cameras", color: "#e48fd0", icon: "camera" },
  INTELLIGENCE: { label: "Intelligence", color: "#dfe7f1", icon: "notice" },
  CHANGE: { label: "Change", color: "#a3e635", icon: "change" },
};
const SEVERITY = {
  INFO: { rank: 0, color: "#8fa0b6", label: "Info" },
  WATCH: { rank: 1, color: "#f5c451", label: "Watch" },
  ALERT: { rank: 2, color: "#ff8a3d", label: "Alert" },
  CRITICAL: { rank: 3, color: "#ff4d5e", label: "Critical" },
};
const LAYER_CATEGORY = {
  WEATHER: "WEATHER", TRAFFIC: "ROADS", MARITIME: "MARITIME", PUBLIC_CAMERA: "CAMERA",
  SATELLITE: "SPACE", GOVERNMENT: "INTELLIGENCE", INFRASTRUCTURE: "INFRASTRUCTURE",
  SEISMIC: "EARTH", DISASTER: "EARTH", AIRCRAFT: "AIR",
};
const LAYER_SEVERITY = { WEATHER: "ALERT", SEISMIC: "ALERT", DISASTER: "ALERT", TRAFFIC: "WATCH", GOVERNMENT: "WATCH" };
const KIND_CATEGORY = {
  aircraft: "AIR", vessel: "MARITIME", satellite: "SPACE", scene: "SPACE", weather: "WEATHER",
  alert: "WEATHER", storm: "WEATHER", wildfire: "EARTH", seismic: "EARTH", road: "ROADS",
  camera: "CAMERA", port: "INFRASTRUCTURE", airport: "INFRASTRUCTURE", "airport-ref": "INFRASTRUCTURE",
  notice: "INTELLIGENCE", blind: "INTELLIGENCE", change: "CHANGE",
};

const CAMERA_PRESETS = {
  world: { center: [-28, 34], zoom: 1.45, pitch: 0, bearing: 0 },
  hero: { center: [-15.5, 47.2], zoom: 3.1, pitch: 30, bearing: -14 },
  port: { center: [-3.3, 51.33], zoom: 8.6, pitch: 50, bearing: -20 },
  airport: { center: [-3.02, 51.55], zoom: 9.6, pitch: 52, bearing: 24 },
  earth: { center: [-4.2, 51.0], zoom: 7.7, pitch: 42, bearing: -8 },
};
const STORIES = {
  port: { preset: "port", event: "SYN-ALERT-01" },
  airport: { preset: "airport", event: "SYN-AC001" },
  earth: { preset: "earth", event: "SYN-EQ00" },
};
const BLIND_ZONES = [
  { id: "BLIND-OFFSHORE", label: "Low coverage", reason: "Offshore fringe: vessel receivers are sparse in this scenario.",
    pts: [[50.5, -5.6], [50.5, -4.4], [51.2, -4.4], [51.2, -5.6]] },
  { id: "BLIND-RURAL", label: "Stale source", reason: "Rural road sensors report sparsely and late.",
    pts: [[51.8, -2.4], [51.8, -1.6], [52.2, -1.6], [52.2, -2.4]] },
  { id: "BLIND-OCEAN", label: "No qualified source", reason: "Open-ocean vessel positions here are replay only; no qualified receiver covers this area.",
    pts: [[40, -40], [40, -22], [52, -22], [52, -40]] },
];
const ENTITY_FOR = {
  "SYN-AC001": ["ENT-AC001"], "SYN-VS002": ["ENT-VS002"], "SYN-PORT-01": ["ENT-PORT"],
  "SYN-APT-01": ["ENT-APT"], "SYN-SAT00": ["ENT-SAT00"], "SYN-ALERT-01": ["ENT-STORM"], "SYN-EQ00": ["ENT-STORM"],
};
const WHY = {
  WEATHER: "Severe weather over busy approaches: vessels may hold, coastal roads may slow, and harbour operations may change. Each source below says what it reported and when.",
  EARTH: "An offshore event near shipping lanes and coastal infrastructure. Offshore sensors are sparse, so check coverage before drawing conclusions.",
  SPACE: "An overpass footprint covers the area, so imagery could corroborate ground reports. This demo claims the footprint only, never pixels.",
  AIR: "Aircraft are holding near the airfield. Positions are approximate replay tracks, not surveillance-grade data.",
  MARITIME: "Vessel movement near the approaches. Replay positions are approximate; gaps in receiver coverage are marked as blind spots.",
  ROADS: "Road conditions change how quickly people and services can move around the event.",
  CAMERA: "A public camera snapshot can confirm conditions. Snapshots show places, never identify people.",
  INFRASTRUCTURE: "Critical sites near the event. Status comes from operator notices, not inference.",
  INTELLIGENCE: "An open public notice relevant to the area.",
};

const state = {
  ultra: null, world: null, events: [], tick: CAPTURE ? CAPTURE_TICK : 0, mode: "replay",
  // Single authoritative UI world-mode state. URL is parsed once into
  // MODE_NOW; every chrome surface below reads state.worldMode — no widget
  // may infer the mode on its own. (state.mode is the *timeline* mode:
  // "current" | "belief" | "replay". state.truth holds backend truth
  // metadata separately and never drives the mode.)
  worldMode: MODE_NOW ? "now" : "replay", truth: null,
  playing: false, speed: 1, timer: null, selected: null, evidence: null, context: null,
  investigating: false, focus: CAPTURE === "focus", following: null, plugins: null,
  related: new Set(), cache: new Map(), paletteItems: [], paletteIndex: 0,
  now: null, airNow: null, importantV2: null, nowError: null,
  changes: [], changeById: {},
  liveEarth: { mode: "standard", layer: null, status: null },
  visible: { night: true, cities: true, graticule: false, aircraft: true, vessels: true, seismic: true,
    wildfire: true, satellite: true, storm: true, weather: true, infra: true, roads: true, cameras: true,
    notices: true, blind: false, coverage: true },
};
let map = null;

/* ------------------------------------------------------------- helpers */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const announce = (message) => { $("live").textContent = message; };
const fmt = (n) => Number(n).toLocaleString("en-US");

async function getJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} answered HTTP ${response.status}`);
  return response.json();
}

function svgIcon(name, color = "currentColor", size = 16) {
  const spec = ICONS[name] || ICONS.globe;
  const paint = spec.fill ? `fill="${color}"`
    : `fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path ${paint} d="${spec.d}"/></svg>`;
}

function distanceKm(a, b) {
  const r = Math.PI / 180;
  const h = Math.sin((b[0] - a[0]) * r / 2) ** 2
    + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin((b[1] - a[1]) * r / 2) ** 2;
  return 2 * EARTH_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

function circleRing(lat, lon, km, steps = 48) {
  const r = Math.PI / 180, d = km / EARTH_KM, la = lat * r, lo = lon * r, ring = [];
  for (let i = 0; i <= steps; i++) {
    const b = 2 * Math.PI * i / steps;
    const la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(b));
    const lo2 = lo + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
    ring.push([lo2 / r, la2 / r]);
  }
  return ring;
}

const fc = (features) => ({ type: "FeatureCollection", features });
const pt = (lat, lon, properties) => ({ type: "Feature", properties, geometry: { type: "Point", coordinates: [lon, lat] } });
const lineLL = (pairs, properties = {}) => ({ type: "Feature", properties, geometry: { type: "LineString", coordinates: pairs.map(([la, lo]) => [lo, la]) } });
const polyLL = (pairs, properties = {}) => ({ type: "Feature", properties, geometry: { type: "Polygon", coordinates: [pairs.map(([la, lo]) => [lo, la])] } });
const polyXY = (ring, properties = {}) => ({ type: "Feature", properties, geometry: { type: "Polygon", coordinates: [ring] } });
const closeRing = (pairs) => (pairs.length && (pairs[0][0] !== pairs.at(-1)[0] || pairs[0][1] !== pairs.at(-1)[1]) ? [...pairs, pairs[0]] : pairs);
const centre = (pairs) => [pairs.reduce((s, p) => s + p[0], 0) / pairs.length, pairs.reduce((s, p) => s + p[1], 0) / pairs.length];

function minuteOf(t) {
  const m = /T\s*([+-]?\d+)\s*(m|h)?/i.exec(String(t ?? ""));
  if (!m) return 0;
  return Number(m[1]) * (m[2] && m[2].toLowerCase() === "h" ? 60 : 1);
}

function replayClock(minute) {
  const epoch = Date.parse(state.world?.epoch ?? "2026-09-15T16:40:00Z");
  return `${new Date(epoch + minute * 60000).toISOString().slice(11, 16)} UTC`;
}

function utcLabel(iso) {
  // Real timestamps may carry any offset; always show them converted to UTC.
  const ms = Date.parse(String(iso ?? ""));
  if (!Number.isFinite(ms)) return "UNKNOWN";
  const t = new Date(ms).toISOString();
  return `${t.slice(0, 10)} ${t.slice(11, 16)} UTC`;
}

function importantWhy(id) {
  // Important Now is only honest if its reasoning is visible: rank, certainty,
  // observed/inferred, source count, score and every reason the backend gave.
  const items = state.importantV2?.items || [];
  const i = items.findIndex((x) => x.key === id);
  if (i < 0) return "";
  const it = items[i], n = it.n_sources ?? 0;
  // Same total as the HUD chip (backend n; the item list itself is capped).
  const total = state.importantV2?.n ?? items.length;
  return `<section class="dsec"><h3>Why flagged · Important #${i + 1} of ${total}</h3>
    <p>${esc(it.certainty || "UNKNOWN")} · ${esc(it.observed_or_inferred || "UNKNOWN")} · ${n} source${n === 1 ? "" : "s"} · score ${esc(it.total ?? "?")}/12</p>
    <ul class="why">${(it.reasons || []).map((r) => `<li>${esc(r)}</li>`).join("")}</ul></section>`;
}

function ageLabel(iso) {
  // Age of a real event at the payload's own time (not the viewer's clock).
  const at = Date.parse(String(state.now?.generated_at ?? "")), t = Date.parse(String(iso ?? ""));
  if (!Number.isFinite(at) || !Number.isFinite(t)) return "UNKNOWN";
  const h = Math.max(0, (at - t) / 3600000);
  const age = h < 1 ? `${Math.round(h * 60)} min` : h < 48 ? `${h.toFixed(1)} h` : `${(h / 24).toFixed(1)} days`;
  return `${age} old at data time`;
}

function humanWhen(raw, fallbackMinute) {
  const text = String(raw ?? "");
  if (/^\d{4}-\d\d-\d\dT/.test(text)) return `${text.slice(0, 10)} ${text.slice(11, 16)} UTC`;
  if (/(^|-)T/i.test(text) || /^demo-t/i.test(text)) {
    const unit = /h\b/i.test(text) ? "h" : "m";
    const minutes = minuteOf(text.replace(/^demo-/i, ""));
    const shown = unit === "h" ? `${minutes / 60 >= 0 ? "+" : ""}${minutes / 60}h` : `+${minutes}m`;
    return `T${shown} · ${replayClock(minutes)} (replay)`;
  }
  if (fallbackMinute != null) return `T+${fallbackMinute}m · ${replayClock(fallbackMinute)} (replay)`;
  return "Not stated";
}

function formatLatLon(lat, lon) {
  return `${Math.abs(lat).toFixed(1)}°${lat >= 0 ? "N" : "S"} ${Math.abs(lon).toFixed(1)}°${lon >= 0 ? "E" : "W"}`;
}

function placeName(lat, lon) {
  if (lat == null || lon == null) return "Location not stated";
  const u = state.ultra, w = state.world;
  if (u && distanceKm([lat, lon], [u.harbor.lat, u.harbor.lon]) < 12) return "Port Meridian (fictional)";
  if (u && distanceKm([lat, lon], [u.airfield.lat, u.airfield.lon]) < 8) return "Meridian Field (fictional)";
  let best = null;
  for (const c of w?.cities ?? []) {
    const d = distanceKm([lat, lon], [c.lat, c.lon]);
    if (!best || d < best.d) best = { c, d };
  }
  if (best && best.d < 45) return `Near ${best.c.name}`;
  if (best && best.d < 350) return `${fmt(Math.round(best.d / 10) * 10)} km from ${best.c.name}`;
  return formatLatLon(lat, lon);
}

function observationChip(observation) {
  const cls = { OBSERVED: "obs", INFERRED: "inf", CORROBORATED: "cor" }[observation] || "unk";
  const label = { OBSERVED: "Reported", INFERRED: "Modeled", CORROBORATED: "Corroborated" }[observation] || "Unverified";
  return `<span class="chip ${cls}">${label}</span>`;
}

/* ---------------------------------------------------------------- data */

async function loadTick(tick) {
  const key = `${tick}:${SCENE}`;
  if (!state.cache.has(key)) {
    const sceneArg = SCENE ? `&scene=${SCENE}` : "";
    state.cache.set(key, Promise.all([
      getJSON(`/api/ultra?tick=${tick}${sceneArg}`),
      getJSON(`/api/world?tick=${tick}`),
    ]));
  }
  try {
    return await state.cache.get(key);
  } catch (error) {
    state.cache.delete(key);
    throw error;
  }
}

function topoFeatures(topology, objectName) {
  const { scale = [1, 1], translate = [0, 0] } = topology.transform || {};
  const arcs = topology.arcs.map((arc) => {
    let x = 0, y = 0;
    return arc.map(([dx, dy]) => { x += dx; y += dy; return [x * scale[0] + translate[0], y * scale[1] + translate[1]]; });
  });
  const ring = (ids) => {
    const out = [];
    for (const i of ids) {
      const pts = i >= 0 ? arcs[i] : arcs[~i].slice().reverse();
      out.push(...(out.length ? pts.slice(1) : pts));
    }
    return out;
  };
  const obj = topology.objects[objectName];
  return fc((obj.geometries || [obj])
    .filter((g) => g.type === "Polygon" || g.type === "MultiPolygon")
    .map((g) => ({
      type: "Feature", properties: { name: g.properties?.name ?? "" },
      geometry: g.type === "Polygon"
        ? { type: "Polygon", coordinates: g.arcs.map(ring) }
        : { type: "MultiPolygon", coordinates: g.arcs.map((p) => p.map(ring)) },
    })));
}

function graticule(step = 30) {
  const lines = [];
  for (let lon = -180; lon < 180; lon += step) {
    const c = [];
    for (let lat = -80; lat <= 80; lat += 2) c.push([lon, lat]);
    lines.push(c);
  }
  for (let lat = -60; lat <= 60; lat += step) {
    const c = [];
    for (let lon = -180; lon <= 180; lon += 2) c.push([lon, lat]);
    lines.push(c);
  }
  return fc(lines.map((coordinates) => ({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates } })));
}

function nightStrips(ring) {
  // Strips from the terminator to the night pole render cleanly on a globe,
  // unlike one polygon that spans every longitude.
  const terminator = ring.slice(0, ring.length - 3);
  const pole = ring[ring.length - 3][0] < 0 ? -89.5 : 89.5;
  const features = [];
  for (let i = 0; i < terminator.length - 1; i++) {
    const [la1, lo1] = terminator[i], [la2, lo2] = terminator[i + 1];
    features.push(polyXY([[lo1, la1], [lo2, la2], [lo2, pole], [lo1, pole], [lo1, la1]]));
  }
  return fc(features);
}

function findObject(id) {
  const u = state.ultra, w = state.world;
  if (MODE_NOW && state.now) {
    const hit = findNowObject(id);
    if (hit) return hit;
  }
  if (!u || !w || !id) return null;
  const pools = [["aircraft", w.aircraft], ["aircraft", u.aircraft], ["vessel", w.vessels], ["vessel", u.vessels],
    ["wildfire", u.wildfire], ["seismic", u.seismic], ["road", u.road], ["camera", u.cameras],
    ["port", u.ports], ["airport", u.airports], ["weather", u.weather.cells]];
  for (const [kind, list] of pools) {
    const o = list.find((x) => x.id === id);
    if (o) return { kind, obj: o, lat: o.lat, lon: o.lon };
  }
  const alert = u.weather.alerts.find((x) => x.id === id);
  if (alert) { const [lat, lon] = centre(alert.polygon); return { kind: "alert", obj: alert, lat, lon }; }
  const scene = u.satellite.find((x) => x.id === id);
  if (scene) { const [lat, lon] = centre(scene.footprint); return { kind: "scene", obj: scene, lat, lon }; }
  const notice = u.osint.find((x) => x.id === id);
  if (notice) {
    const [lat, lon] = notice.polygon ? centre(notice.polygon) : [notice.lat, notice.lon];
    return { kind: "notice", obj: notice, lat, lon };
  }
  if (id === w.storm.id) return { kind: "storm", obj: w.storm, lat: w.storm.center[0], lon: w.storm.center[1] };
  if (id === w.satellite.id) return { kind: "satellite", obj: w.satellite, lat: w.satellite.position[0], lon: w.satellite.position[1] };
  const ref = w.airports.find((x) => x.code === id);
  if (ref) return { kind: "airport-ref", obj: ref, lat: ref.lat, lon: ref.lon };
  const fixed = { "SYN-NOTICE-01": u.harbor, "SYN-GRID-01": u.harbor, "SYN-NOTICE-02": u.airfield }[id];
  if (fixed) return { kind: "notice", obj: { id, ...fixed }, lat: fixed.lat, lon: fixed.lon };
  const zone = BLIND_ZONES.find((z) => z.id === id);
  if (zone) { const [lat, lon] = centre(zone.pts); return { kind: "blind", obj: zone, lat, lon }; }
  return null;
}

const isWorldId = (id) => /^SYN-(LH|LV)\d/.test(id) || id === "SYN-STORM-01" || id === "SYN-SAT-1" || /^[A-Z]{3}$/.test(id);

function buildEvents() {
  const out = state.world.events.map((e) => ({ ...e, kind: "event", minute: minuteOf(e.t), hero: null }));
  for (const hero of state.ultra.heroes) {
    for (const step of hero.steps) {
      const existing = out.find((e) => e.id === step.ref);
      if (existing) { existing.hero = existing.hero || hero.id; continue; }
      const found = findObject(step.ref);
      if (!found) continue;
      out.push({
        id: step.ref, title: step.text, kind: found.kind, severity: LAYER_SEVERITY[step.layer] || "INFO",
        category: LAYER_CATEGORY[step.layer] || "INTELLIGENCE", lat: found.lat, lon: found.lon,
        t: step.at, minute: minuteOf(step.at), sources: 1, hero: hero.id,
      });
    }
  }
  for (const e of out) {
    if (!e.hero) continue;
    const hero = state.ultra.heroes.find((h) => h.id === e.hero);
    e.sources = Math.max(e.sources, hero.steps.filter((s) => s.ref === e.id).length);
  }
  if (MODE_NOW && state.now) out.push(...nowEvents());
  return out.sort((a, b) => SEVERITY[b.severity].rank - SEVERITY[a.severity].rank || a.minute - b.minute);
}

/* ---------------------------------------------------------- map images */

function pixelRatio() { return Math.min(2, window.devicePixelRatio || 1); }

function iconImage(name, color, size = 26) {
  const ratio = pixelRatio(), px = Math.round(size * ratio), spec = ICONS[name] || ICONS.globe;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.scale(px / 24, px / 24);
  const path = new Path2D(spec.d);
  ctx.lineJoin = "round"; ctx.lineCap = "round";
  ctx.strokeStyle = "rgba(3,7,13,0.9)"; ctx.lineWidth = spec.fill ? 2.6 : 4.4; ctx.stroke(path);
  if (spec.fill) { ctx.fillStyle = color; ctx.fill(path); } else { ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke(path); }
  return { image: ctx.getImageData(0, 0, px, px), pixelRatio: ratio };
}

function textImage(text, { size = 12, weight = 600, color = "#c9d4e2" } = {}) {
  const ratio = pixelRatio(), pad = 3, font = `${weight} ${size}px Inter, system-ui, sans-serif`;
  const measure = document.createElement("canvas").getContext("2d");
  measure.font = font;
  const width = Math.ceil(measure.measureText(text).width) + pad * 2, height = size + pad * 2 + 2;
  const canvas = document.createElement("canvas");
  canvas.width = width * ratio; canvas.height = height * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio); ctx.font = font; ctx.textBaseline = "middle";
  ctx.lineWidth = 3.2; ctx.strokeStyle = "rgba(3,7,13,0.92)"; ctx.lineJoin = "round";
  ctx.strokeText(text, pad, height / 2);
  ctx.fillStyle = color; ctx.fillText(text, pad, height / 2);
  return { image: ctx.getImageData(0, 0, canvas.width, canvas.height), pixelRatio: ratio };
}

function countImage(label, color) {
  const ratio = pixelRatio(), size = 12, font = `700 ${size}px Inter, system-ui, sans-serif`;
  const measure = document.createElement("canvas").getContext("2d");
  measure.font = font;
  const width = Math.max(26, Math.ceil(measure.measureText(label).width) + 14), height = 22;
  const canvas = document.createElement("canvas");
  canvas.width = width * ratio; canvas.height = height * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  ctx.beginPath(); ctx.roundRect(1, 1, width - 2, height - 2, 10);
  ctx.fillStyle = "rgba(6,11,18,0.94)"; ctx.fill();
  ctx.lineWidth = 1.5; ctx.strokeStyle = color; ctx.stroke();
  ctx.font = font; ctx.fillStyle = "#eef3f9"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(label, width / 2, height / 2 + 0.5);
  return { image: ctx.getImageData(0, 0, canvas.width, canvas.height), pixelRatio: ratio };
}

function hatchImage() {
  const px = 16, canvas = document.createElement("canvas");
  canvas.width = canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.strokeStyle = "rgba(150,164,184,0.38)"; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(0, px); ctx.lineTo(px, 0); ctx.moveTo(-4, 4); ctx.lineTo(4, -4); ctx.moveTo(px - 4, px + 4); ctx.lineTo(px + 4, px - 4); ctx.stroke();
  return { image: ctx.getImageData(0, 0, px, px), pixelRatio: 1 };
}

function registerImages() {
  const icons = [["plane:air", "plane", CATEGORY.AIR.color], ["ship:sea", "ship", CATEGORY.MARITIME.color],
    ["sat:space", "sat", CATEGORY.SPACE.color], ["cone:roads", "cone", CATEGORY.ROADS.color],
    ["camera:camera", "camera", CATEGORY.CAMERA.color], ["fire:earth", "fire", "#ff6f4a"],
    ["anchor:infra", "anchor", CATEGORY.INFRASTRUCTURE.color], ["airport:infra", "airport", CATEGORY.INFRASTRUCTURE.color],
    ["airport:ref", "airport", "#8fa0b6"], ["notice:intel", "notice", CATEGORY.INTELLIGENCE.color]];
  for (const [id, name, color] of icons) {
    const { image, pixelRatio: ratio } = iconImage(name, color, id.startsWith("plane") || id.startsWith("ship") ? 24 : 22);
    map.addImage(id, image, { pixelRatio: ratio });
  }
  const hatch = hatchImage();
  map.addImage("hatch", hatch.image, { pixelRatio: hatch.pixelRatio });
  // Labels and cluster badges are drawn on demand (no glyph server offline).
  const resolve = (id) => {
    if (map.hasImage(id)) return;
    let made = null;
    if (id.startsWith("label:")) made = textImage(id.slice(6), id.startsWith("label:Storm") ? { color: "#d6e8f7", weight: 650 } : {});
    else if (id.startsWith("count:")) {
      const [, cat, n] = id.split(":");
      made = countImage(n, cat === "sea" ? CATEGORY.MARITIME.color : CATEGORY.AIR.color);
    }
    if (made) map.addImage(id, made.image, { pixelRatio: made.pixelRatio });
  };
  if (typeof map.setMissingStyleImageResolver === "function") map.setMissingStyleImageResolver(resolve);
  else map.on("styleimagemissing", (event) => resolve(event.id));
}

/* ------------------------------------------------------------ map data */

function buildData() {
  if (MODE_NOW) return buildNowData();
  const u = state.ultra, w = state.world;
  const air = [
    ...w.aircraft.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "aircraft", label: o.callsign, heading: o.heading,
      detail: `${o.route} · FL${Math.round(o.alt_ft / 100)} · ${o.speed_kt} kt` })),
    ...u.aircraft.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "aircraft", label: o.callsign, heading: o.heading,
      detail: `${fmt(o.alt_ft)} ft · ${o.speed_kt} kt` })),
  ];
  const sea = [
    ...w.vessels.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "vessel", label: o.name, heading: o.course,
      detail: `${o.speed_kt} kt · ${o.lane}` })),
    ...u.vessels.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "vessel", label: o.name, heading: o.course,
      detail: `${String(o.nav_state).toLowerCase()} · ${o.speed_kt} kt` })),
  ];
  const osintFeatures = u.osint.map((o) => (o.polygon
    ? polyLL(closeRing(o.polygon), { id: o.id, kind: "notice", label: o.title })
    : pt(o.lat, o.lon, { id: o.id, kind: "notice", label: o.title })));
  return {
    air: fc(air), sea: fc(sea),
    trails: fc(u.aircraft.filter((o) => o.trail).map((o) => lineLL(o.trail, { id: o.id }))),
    corridors: fc(w.corridors.map((c) => lineLL(c.path, { id: c.id }))),
    lanes: fc(w.lanes.map((l) => lineLL(l.path, { id: l.id, label: l.name }))),
    storm: fc(w.storm.bands.map((b) => polyLL(b.polygon, { id: w.storm.id, kind: "storm", intensity: b.intensity, label: w.storm.label, detail: b.name }))),
    stormTrack: fc([lineLL(w.storm.track_past, { part: "past" }), lineLL(w.storm.track_illustrative, { part: "ahead" })]),
    stormLabel: fc([pt(w.storm.center[0], w.storm.center[1], { id: w.storm.id, kind: "storm", label: w.storm.label })]),
    satTrack: fc([lineLL(w.satellite.track, { id: w.satellite.id })]),
    satSwath: fc([polyLL(w.satellite.swath, { id: w.satellite.id, kind: "satellite", label: "SYN-SAT-1 swath", detail: `${w.satellite.swath_km} km wide · modeled` })]),
    satPos: fc([pt(w.satellite.position[0], w.satellite.position[1], { id: w.satellite.id, kind: "satellite", label: "SYN-SAT-1",
      detail: `${w.satellite.orbit.altitude_km} km · ${w.satellite.orbit.inclination_deg}° · modeled orbit` })]),
    scenes: fc(u.satellite.map((s) => polyLL(closeRing(s.footprint), { id: s.id, kind: "scene", label: s.scene_id, detail: `${s.sensor} · clouds ${s.cloud_cover_pct}%` }))),
    cells: fc(u.weather.cells.map((c) => polyXY(circleRing(c.lat, c.lon, c.radius_km), { id: c.id, kind: "weather", label: `Weather cell ${c.id}`, detail: `wind ${c.wind_kt} kt · ${c.precip_mm_h} mm/h` }))),
    alerts: fc(u.weather.alerts.map((a) => polyLL(closeRing(a.polygon), { id: a.id, kind: "alert", label: a.title }))),
    fires: fc(u.wildfire.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "wildfire", label: `Hotspot ${o.id}`, detail: `confidence ${String(o.confidence).toLowerCase()}` }))),
    quakes: fc(u.seismic.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "seismic", label: `M${o.mag} earthquake`, detail: `depth ${o.depth_km} km`, mag: o.mag }))),
    roads: fc(u.road.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "road", label: `Road ${String(o.kind).toLowerCase()}`, detail: `severity ${o.severity}/5` }))),
    cameras: fc(u.cameras.map((o) => pt(o.lat, o.lon, { id: o.id, kind: "camera", label: `Public camera ${o.id}`, detail: `${o.status === "OK" ? "online" : "stale"} · snapshot only` }))),
    infra: fc([
      ...u.ports.map((p) => pt(p.lat, p.lon, { id: p.id, kind: "port", label: `${p.name} (fictional)`, icon: "anchor:infra" })),
      ...u.airports.map((a) => pt(a.lat, a.lon, { id: a.id, kind: "airport", label: `${a.name} (fictional)`, icon: "airport:infra" })),
      ...w.airports.map((a) => pt(a.lat, a.lon, { id: a.code, kind: "airport-ref", label: a.code, detail: a.name, icon: "airport:ref" })),
    ]),
    notices: fc(osintFeatures),
    blind: fc(BLIND_ZONES.map((z) => polyLL(closeRing(z.pts), { id: z.id, kind: "blind", label: z.label, detail: z.reason }))),
    night: nightStrips(w.solar.night),
    cities: fc(w.cities.map((c) => pt(c.lat, c.lon, { name: c.name, rank: c.rank }))),
    events: fc(state.events.map((e) => pt(e.lat, e.lon, { id: e.id, kind: "event", severity: e.severity, label: e.title }))),
    // Replay has no change objects: source stays empty so the change ring
    // can exist in both modes without ever rendering synthetic content.
    changes: fc([]),
  };
}

function buildNowData() {
  // WORLD NOW: real pools only. Replay pools stay empty so no synthetic
  // object can render; uncovered domains stay absent (never filler).
  // Shared geographic truth (cities, night, graticule) still renders.
  const empty = fc([]);
  const quakes = [], fires = [], notices = [];
  const objs = state.now?.objects || {};
  for (const q of objs["usgs-earthquakes"] || []) {
    if (q.lat == null) continue;
    const f = q.fields || {};
    quakes.push(pt(q.lat, q.lon, { id: q.stable_key, kind: "seismic",
      label: `M${f.mag ?? "?"} earthquake`, detail: `${f.place || ""} · ${q.source_event_time || "UNKNOWN"}`,
      mag: f.mag ?? 4 }));
  }
  for (const e of objs["nasa-eonet"] || []) {
    if (e.lat == null) continue;
    const f = e.fields || {}, cats = (f.categories || []).join(",");
    const title = f.title || e.stable_key;
    if (/wildfire/i.test(cats)) fires.push(pt(e.lat, e.lon, { id: e.stable_key, kind: "wildfire", label: title, detail: "EONET open event" }));
    else notices.push(pt(e.lat, e.lon, { id: e.stable_key, kind: "notice", label: title }));
  }
  for (const g of objs["gdacs-alerts"] || []) {
    if (g.lat == null) continue;
    const f = g.fields || {};
    notices.push(pt(g.lat, g.lon, { id: g.stable_key, kind: "notice",
      label: `${f.alert_level || ""} ${f.event_type || ""} — ${(f.title || "").slice(0, 60)}`.trim() }));
  }
  const w = state.world;
  return {
    air: fc(nowAircraftPoints()), sea: empty, trails: empty, corridors: empty, lanes: empty,
    storm: empty, stormTrack: empty, stormLabel: empty,
    satTrack: empty, satSwath: empty, satPos: empty, scenes: empty, cells: empty, alerts: empty,
    fires: fc(fires), quakes: fc(quakes),
    roads: empty, cameras: empty,
    infra: fc([...(state.now?.static_geo?.airports || []), ...(state.now?.static_geo?.ports || [])]
      .map((p) => pt(p.lat, p.lon, { id: p.id, kind: p.id.startsWith("APT") ? "airport" : "port",
        label: `${p.name} (static reference)`, icon: p.id.startsWith("APT") ? "airport:ref" : "anchor:infra" }))),
    notices: fc(notices),
    blind: empty,
    coverage: fc(nowCoverageFeatures()),
    nowtrail: empty, nowsel: empty,
    // Real sun at the data time from the backend; never the replay scene sun.
    night: state.now?.solar?.night ? nightStrips(state.now.solar.night) : empty,
    cities: fc(w.cities.map((c) => pt(c.lat, c.lon, { name: c.name, rank: c.rank }))),
    events: fc(state.events.map((e) => e.lat == null ? null : pt(e.lat, e.lon,
      { id: e.id, kind: "event", severity: e.severity, label: e.title })).filter(Boolean)),
    // Change pins: real transitions only (empty until the change engine
    // emits). Rendered with their own ring so "something changed here"
    // reads instantly at globe zoom.
    changes: fc(state.events.filter((e) => e.kind === "change" && e.lat != null).map((e) =>
      pt(e.lat, e.lon, { id: e.id, kind: "change", severity: e.severity, label: e.title }))),
  };
}

function addNowLayers() {
  if (!map.getSource("coverage")) {
    addSource("coverage", fc([]));
    addSource("nowtrail", fc([]));
    addSource("nowsel", fc([]));
    map.addLayer({ id: "coverage-fill", type: "fill", source: "coverage",
      paint: { "fill-color": ["match", ["get", "state"], "GOOD", "#3fe0b0", "PARTIAL", "#ffc857", "RATE LIMITED", "#ff6b6b", "#8a93a6"],
        "fill-opacity": 0.06 } });
    map.addLayer({ id: "coverage-line", type: "line", source: "coverage",
      paint: { "line-color": ["match", ["get", "state"], "GOOD", "#3fe0b0", "PARTIAL", "#ffc857", "RATE LIMITED", "#ff6b6b", "#8a93a6"],
        "line-width": 1.2, "line-dasharray": [5, 5], "line-opacity": 0.8 } });
    map.addLayer({ id: "nowtrail-line", type: "line", source: "nowtrail",
      paint: { "line-color": "#6aa8ff", "line-width": 1.6, "line-opacity": 0.8 } });
    map.addLayer({ id: "nowsel-ring", type: "circle", source: "nowsel",
      paint: { "circle-radius": 14, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#ffb547", "circle-stroke-width": 2 } });
  }
  tuneNowLod();
}

function tuneNowLod() {
  // Replay layers were tuned for one region (minzoom 4-6), which hid every
  // real earthquake, wildfire and notice at the globe view. WORLD NOW is
  // global: sparse real layers show from the globe, and aircraft clusters are
  // strong enough to read against the dark ocean. Replay never calls this.
  for (const [id, min] of [["quake-ring", 0], ["quake-point", 0], ["fire-point", 0], ["notice-point", 2]]) {
    if (map.getLayer(id)) map.setLayerZoomRange(id, min, 24);
  }
  if (map.getLayer("air-cluster")) {
    map.setPaintProperty("air-cluster", "circle-opacity", 0.45);
    map.setPaintProperty("air-cluster", "circle-stroke-opacity", 0.85);
  }
}

function addSource(id, data, options = {}) {
  map.addSource(id, { type: "geojson", data, ...options });
}

function addBaseLayers(land, countries) {
  addSource("land", land, { tolerance: 0.25 });
  addSource("countries", countries, { tolerance: 0.35 });
  addSource("graticule", graticule());
  map.addLayer({ id: "land-fill", type: "fill", source: "land",
    paint: { "fill-color": ["interpolate", ["linear"], ["zoom"], 1, "#1c2d3f", 7, "#223751", 11, "#27405e"], "fill-antialias": true } });
  map.addLayer({ id: "country-border", type: "line", source: "countries",
    paint: { "line-color": "#3a536c", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.35, 7, 0.9],
      "line-opacity": ["interpolate", ["linear"], ["zoom"], 1, 0.5, 5, 0.85] } });
  map.addLayer({ id: "coastline", type: "line", source: "land",
    paint: { "line-color": "#6283a1", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.6, 7, 1.4], "line-opacity": 0.85 } });
  map.addLayer({ id: "graticule", type: "line", source: "graticule", maxzoom: 6,
    layout: { visibility: state.visible.graticule ? "visible" : "none" },
    paint: { "line-color": "#223549", "line-width": 0.6, "line-opacity": 0.6 } });
}

function addDataLayers(d) {
  for (const [id, data] of Object.entries(d)) {
    if (id === "air" || id === "sea") addSource(id, data, { cluster: true, clusterRadius: 46, clusterMaxZoom: 5 });
    else addSource(id, data);
  }
  addSource("selection", fc([]));
  const L = (layer) => map.addLayer(layer);
  L({ id: "night-fill", type: "fill", source: "night", paint: { "fill-color": "#01040a", "fill-antialias": false,
    "fill-opacity": ["interpolate", ["linear"], ["zoom"], 1, 0.42, 7, 0.26] } });
  L({ id: "blind-fill", type: "fill", source: "blind", layout: { visibility: "none" }, paint: { "fill-pattern": "hatch", "fill-opacity": 0.9 } });
  L({ id: "blind-line", type: "line", source: "blind", layout: { visibility: "none" }, paint: { "line-color": "#9aa7b8", "line-width": 1.2, "line-dasharray": [3, 2], "line-opacity": 0.8 } });
  // Weather is context: it fades out as the camera moves into the operational
  // view, so it never hides the objects the analyst came to look at.
  L({ id: "storm-fill", type: "fill", source: "storm", maxzoom: 9, paint: {
    "fill-color": ["match", ["get", "intensity"], "HIGH", "#cfe5f7", "MODERATE", "#9cc2e2", "#7aa3c6"],
    "fill-opacity": ["interpolate", ["linear"], ["zoom"], 2,
      ["match", ["get", "intensity"], "HIGH", 0.34, "MODERATE", 0.22, 0.13], 7,
      ["match", ["get", "intensity"], "HIGH", 0.18, "MODERATE", 0.11, 0.07], 9, 0.03] } });
  L({ id: "storm-label", type: "symbol", source: "stormLabel", maxzoom: 6.5, layout: {
    "icon-image": "label:Storm system · synthetic", "icon-anchor": "top", "icon-offset": [0, 14], "icon-allow-overlap": true } });
  L({ id: "storm-track", type: "line", source: "stormTrack", paint: { "line-color": "#b9d8f2", "line-width": 1.6,
    "line-opacity": ["match", ["get", "part"], "past", 0.55, 0.9], "line-dasharray": [2, 2] } });
  L({ id: "cell-fill", type: "fill", source: "cells", minzoom: 5, paint: { "fill-color": "#9ec7e8",
    "fill-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.14, 8, 0.09, 11, 0.05] } });
  L({ id: "alert-fill", type: "fill", source: "alerts", minzoom: 4, paint: { "fill-color": "#ff8a3d", "fill-opacity": 0.1 } });
  L({ id: "alert-line", type: "line", source: "alerts", minzoom: 4, paint: { "line-color": "#ff8a3d", "line-width": 1.6, "line-dasharray": [4, 2] } });
  L({ id: "sat-swath-fill", type: "fill", source: "satSwath", maxzoom: 10, paint: { "fill-color": "#b79cff",
    "fill-opacity": ["interpolate", ["linear"], ["zoom"], 2, 0.07, 7, 0.09, 10, 0.04] } });
  L({ id: "sat-swath-line", type: "line", source: "satSwath", paint: { "line-color": "#b79cff", "line-width": 1, "line-opacity": 0.6 } });
  L({ id: "scene-line", type: "line", source: "scenes", minzoom: 6, paint: { "line-color": "#b79cff", "line-width": 1.2, "line-dasharray": [3, 2], "line-opacity": 0.8 } });
  L({ id: "sat-track", type: "line", source: "satTrack", paint: { "line-color": "#b79cff", "line-width": 1.4, "line-opacity": 0.75, "line-dasharray": [1.5, 1.5] } });
  L({ id: "corridor-line", type: "line", source: "corridors", maxzoom: 7, paint: { "line-color": "#6aa8ff", "line-width": 1, "line-opacity": ["interpolate", ["linear"], ["zoom"], 1, 0.28, 6, 0.12] } });
  L({ id: "lane-line", type: "line", source: "lanes", maxzoom: 9, paint: { "line-color": "#37d2b0", "line-width": 1, "line-opacity": 0.26, "line-dasharray": [2, 3] } });
  L({ id: "air-trail", type: "line", source: "trails", minzoom: 6, paint: { "line-color": "#6aa8ff", "line-width": 1.2, "line-opacity": 0.45 } });
  for (const rank of [1, 2, 3]) {
    const minzoom = { 1: 1.8, 2: 4, 3: 6.4 }[rank];
    L({ id: `city-dot-${rank}`, type: "circle", source: "cities", minzoom, filter: ["==", ["get", "rank"], rank],
      paint: { "circle-radius": rank === 1 ? 2.4 : 2, "circle-color": "#c9d4e2", "circle-opacity": 0.8, "circle-stroke-color": "#03070d", "circle-stroke-width": 1 } });
    L({ id: `city-label-${rank}`, type: "symbol", source: "cities", minzoom, filter: ["==", ["get", "rank"], rank],
      layout: { "icon-image": ["concat", "label:", ["get", "name"]], "icon-anchor": "left", "icon-offset": [5, 0], "icon-allow-overlap": false },
      paint: { "icon-opacity": 0.9 } });
  }
  L({ id: "notice-fill", type: "fill", source: "notices", minzoom: 6, filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#dfe7f1", "fill-opacity": 0.05 } });
  L({ id: "notice-line", type: "line", source: "notices", minzoom: 6, filter: ["==", ["geometry-type"], "Polygon"], paint: { "line-color": "#dfe7f1", "line-width": 1, "line-dasharray": [2, 2], "line-opacity": 0.6 } });
  L({ id: "notice-point", type: "symbol", source: "notices", minzoom: 6, filter: ["==", ["geometry-type"], "Point"], layout: { "icon-image": "notice:intel", "icon-allow-overlap": true } });
  L({ id: "road-point", type: "symbol", source: "roads", minzoom: 7.2, layout: { "icon-image": "cone:roads", "icon-size": 0.8, "icon-allow-overlap": true } });
  L({ id: "camera-point", type: "symbol", source: "cameras", minzoom: 7.8, layout: { "icon-image": "camera:camera", "icon-size": 0.8, "icon-allow-overlap": true } });
  L({ id: "infra-point", type: "symbol", source: "infra", minzoom: 4.5, layout: { "icon-image": ["get", "icon"], "icon-size": 0.9, "icon-allow-overlap": true } });
  L({ id: "fire-point", type: "symbol", source: "fires", minzoom: 5.5, layout: { "icon-image": "fire:earth", "icon-size": 0.85, "icon-allow-overlap": true } });
  L({ id: "quake-ring", type: "circle", source: "quakes", minzoom: 4, paint: { "circle-radius": ["interpolate", ["linear"], ["get", "mag"], 2, 5, 6, 16],
    "circle-color": "rgba(255,138,91,0.14)", "circle-stroke-color": "#ff8a5b", "circle-stroke-width": 1.2 } });
  L({ id: "quake-point", type: "circle", source: "quakes", minzoom: 4, paint: { "circle-radius": 3, "circle-color": "#ff8a5b" } });
  for (const [src, cat, icon] of [["sea", "sea", "ship:sea"], ["air", "air", "plane:air"]]) {
    const color = cat === "sea" ? CATEGORY.MARITIME.color : CATEGORY.AIR.color;
    L({ id: `${src}-cluster`, type: "circle", source: src, filter: ["has", "point_count"], paint: {
      "circle-color": color, "circle-opacity": 0.2, "circle-stroke-color": color, "circle-stroke-width": 0.8, "circle-stroke-opacity": 0.35,
      "circle-blur": 0.15,
      "circle-radius": ["interpolate", ["linear"], ["get", "point_count"], 2, 9, 30, 17, 300, 28, 3000, 42] } });
    L({ id: `${src}-count`, type: "symbol", source: src, filter: ["has", "point_count"], layout: {
      "icon-image": ["concat", `count:${cat}:`, ["get", "point_count_abbreviated"]], "icon-allow-overlap": true, "icon-ignore-placement": true } });
    L({ id: `${src}-point`, type: "symbol", source: src, filter: ["!", ["has", "point_count"]], layout: {
      "icon-image": icon, "icon-size": ["interpolate", ["linear"], ["zoom"], 2, 0.72, 7, 0.92, 11, 1.1],
      "icon-rotate": ["get", "heading"], "icon-rotation-alignment": "map", "icon-pitch-alignment": "map",
      "icon-allow-overlap": true, "icon-ignore-placement": true } });
  }
  L({ id: "sat-pos", type: "symbol", source: "satPos", layout: { "icon-image": "sat:space", "icon-allow-overlap": true, "icon-size": 1 } });
  L({ id: "event-halo", type: "circle", source: "events", filter: ["in", ["get", "severity"], ["literal", ["ALERT", "CRITICAL"]]],
    paint: { "circle-radius": 12, "circle-color": "rgba(0,0,0,0)", "circle-stroke-width": 1.6, "circle-stroke-opacity": 0.8,
      "circle-stroke-color": ["match", ["get", "severity"], "CRITICAL", SEVERITY.CRITICAL.color, SEVERITY.ALERT.color] } });
  L({ id: "event-core", type: "circle", source: "events", paint: {
    "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 3.5, 8, 5.5],
    "circle-color": ["match", ["get", "severity"], "CRITICAL", SEVERITY.CRITICAL.color, "ALERT", SEVERITY.ALERT.color, "WATCH", SEVERITY.WATCH.color, SEVERITY.INFO.color],
    "circle-stroke-color": "#03070d", "circle-stroke-width": 1.5 } });
  L({ id: "change-ring", type: "circle", source: "changes", paint: {
    "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 8, 8, 11],
    "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#a3e635",
    "circle-stroke-width": 2, "circle-stroke-opacity": 0.9 } });
  L({ id: "selection-ring", type: "circle", source: "selection", paint: { "circle-radius": 18, "circle-color": "rgba(255,181,71,0.10)",
    "circle-stroke-color": "#ffb547", "circle-stroke-width": 2 } });
}

function updateSources(d = buildData()) {
  for (const [id, data] of Object.entries(d)) map.getSource(id)?.setData(data);
}

const nowOn = () => MODE_NOW && !!state.now;
const nowCount = (replayFn, nowFn) => (nowOn() ? nowFn() : replayFn());
const NAV = [
  { id: "world", title: "World", icon: "globe", rows: [
    { key: "night", label: "Day and night", sub: MODE_NOW ? "Modeled from data time (UTC)" : "Modeled from world time", icon: "clock", color: "#ffb547", count: () => "", layers: ["night-fill"] },
    { key: "cities", label: "Cities", sub: "Reference labels", icon: "pin", color: "#c9d4e2", count: () => state.world.cities.length,
      layers: ["city-dot-1", "city-label-1", "city-dot-2", "city-label-2", "city-dot-3", "city-label-3"] },
    { key: "graticule", label: "Graticule", sub: "30 degree grid", icon: "globe", color: "#8290a3", count: () => "", layers: ["graticule"] } ] },
  { id: "movement", title: "Movement", icon: "plane", rows: [
    // NAV is built once at load, before any data arrives: wording keys on the
    // URL mode (MODE_NOW), counts stay lazy and read live state when drawn.
    { key: "aircraft", label: "Aircraft", sub: MODE_NOW ? "Live ADS-B (delayed seconds)" : "Corridors and regional replay", icon: "plane", color: CATEGORY.AIR.color,
      count: () => nowCount(() => state.world.aircraft.length + state.ultra.aircraft.length, () => state.airNow?.counts?.total ?? 0), layers: ["corridor-line", "air-trail", "air-cluster", "air-count", "air-point"] },
    { key: "vessels", label: "Vessels", sub: MODE_NOW ? "No qualified live source" : "Sea lanes and harbour", icon: "ship", color: CATEGORY.MARITIME.color,
      count: () => nowOn() ? "—" : state.world.vessels.length + state.ultra.vessels.length, layers: ["lane-line", "sea-cluster", "sea-count", "sea-point"] } ] },
  { id: "earth", title: "Earth", icon: "quake", rows: [
    { key: "seismic", label: "Earthquakes", sub: MODE_NOW ? "USGS M4.5+, past 7 days" : "Magnitude and depth", icon: "quake", color: CATEGORY.EARTH.color,
      count: () => nowCount(() => state.ultra.seismic.length, () => (state.now.objects?.["usgs-earthquakes"] || []).length), layers: ["quake-ring", "quake-point"] },
    { key: "wildfire", label: "Wildfires", sub: MODE_NOW ? "NASA EONET open wildfire events" : "Satellite detections", icon: "fire", color: "#ff6f4a",
      // Count only what the map draws: EONET events in a wildfire category.
      count: () => nowCount(() => state.ultra.wildfire.length, () => (state.now.objects?.["nasa-eonet"] || [])
        .filter((e) => e.lat != null && /wildfire/i.test((e.fields?.categories || []).join(","))).length), layers: ["fire-point"] },
    { key: "satellite", label: "Satellite", sub: MODE_NOW ? "No qualified live source" : "Ground track, swath, scenes", icon: "sat", color: CATEGORY.SPACE.color,
      count: () => nowOn() ? "—" : 1 + state.ultra.satellite.length, layers: ["sat-track", "sat-swath-fill", "sat-swath-line", "scene-line", "sat-pos"] } ] },
  { id: "weather", title: "Weather", icon: "cloud", rows: [
    { key: "storm", label: MODE_NOW ? "Space weather" : "Storm system", sub: MODE_NOW ? "NOAA SWPC alerts, not a weather model" : "Rain bands and track", icon: "storm", color: CATEGORY.WEATHER.color,
      count: () => nowOn() ? (state.now.objects?.["noaa-swpc"] || []).length : 1, layers: ["storm-fill", "storm-track"] },
    { key: "weather", label: MODE_NOW ? "Weather alerts" : "Cells and alerts", sub: MODE_NOW ? "NWS alerts, United States only" : "Regional warnings", icon: "cloud", color: SEVERITY.WATCH.color,
      count: () => nowCount(() => state.ultra.weather.cells.length + state.ultra.weather.alerts.length, () => (state.now.objects?.["nws-alerts"] || []).length), layers: ["cell-fill", "alert-fill", "alert-line"] } ] },
  { id: "infrastructure", title: "Infrastructure", icon: "anchor", rows: [
    { key: "infra", label: "Ports and airports", sub: MODE_NOW ? "Static reference geography" : "Reference and fictional", icon: "anchor", color: CATEGORY.INFRASTRUCTURE.color,
      count: () => nowCount(() => state.ultra.ports.length + state.ultra.airports.length + state.world.airports.length,
        () => (state.now.static_geo?.airports || []).length + (state.now.static_geo?.ports || []).length), layers: ["infra-point"] },
    { key: "roads", label: "Roads", sub: MODE_NOW ? "No qualified live source" : "Closures and congestion", icon: "cone", color: CATEGORY.ROADS.color,
      count: () => nowOn() ? "—" : state.ultra.road.length, layers: ["road-point"] },
    // The count column is narrow and numeric: status text belongs in the sub.
    { key: "cameras", label: "Public cameras", sub: MODE_NOW ? "No qualified source" : "Snapshots, never people", icon: "camera", color: CATEGORY.CAMERA.color,
      count: () => nowOn() ? "—" : state.ultra.cameras.length, layers: ["camera-point"] } ] },
  { id: "intelligence", title: "Intelligence", icon: "notice", rows: [
    { key: "notices", label: "Public notices", sub: MODE_NOW ? "GDACS alerts + GDELT news reports" : "Open bulletins", icon: "notice", color: CATEGORY.INTELLIGENCE.color,
      count: () => nowCount(() => state.ultra.osint.length,
        () => (state.now.objects?.["gdacs-alerts"] || []).length + (state.now.objects?.["gdelt-doc"] || []).length), layers: ["notice-fill", "notice-line", "notice-point"] },
    { key: "blind", label: "Blind spots", sub: "Where coverage is thin", icon: "hatch", color: "#9aa7b8", count: () => BLIND_ZONES.length, layers: ["blind-fill", "blind-line"] } ] },
  { id: "sources", title: "Sources", icon: "signal", rows: [
    { key: "health", label: "Source health", sub: "Online, stale, offline, unknown", icon: "signal", color: "#46d19a",
      count: () => (state.plugins ? state.plugins.sources.length : ""), action: () => openSources() } ] },
];

function setVisible(key, on) {
  state.visible[key] = on;
  for (const section of NAV) {
    for (const row of section.rows) {
      if (row.key !== key || !row.layers) continue;
      for (const layer of row.layers) if (map.getLayer(layer)) map.setLayoutProperty(layer, "visibility", on ? "visible" : "none");
    }
  }
  document.querySelector(`.navrow[data-key="${key}"]`)?.setAttribute("aria-checked", String(on));
}

/* ------------------------------------------------------------ rendering */

function renderNav() {
  if (!state.world || !state.ultra) return;
  $("layers").innerHTML = NAV.map((section) => `
    <div class="navsec" data-open="${section.id !== "sources" || true}">
      <button class="navhead" type="button" aria-expanded="true">${svgIcon(section.icon, "currentColor", 14)}<span>${esc(section.title)}</span>
        <span class="chev">${svgIcon("chevron", "currentColor", 14)}</span></button>
      <div class="navrows">${section.rows.map((row) => `
        <button class="navrow${row.action ? " action" : ""}" type="button" data-key="${row.key}" ${row.action ? "" : `role="switch" aria-checked="${state.visible[row.key] !== false}"`} style="--c:${row.color}">
          <span class="ic">${svgIcon(row.icon, row.color, 18)}</span>
          <span><span class="name">${esc(row.label)}</span><span class="sub">${esc(row.sub)}</span></span>
          <span class="count">${esc(row.count())}</span><span class="switch" aria-hidden="true"></span>
        </button>`).join("")}</div>
    </div>`).join("");
  document.querySelectorAll(".navhead").forEach((head) => {
    head.onclick = () => {
      const sec = head.parentElement, open = sec.dataset.open !== "true";
      sec.dataset.open = String(open);
      head.setAttribute("aria-expanded", String(open));
    };
  });
  document.querySelectorAll(".navrow").forEach((btn) => {
    const row = NAV.flatMap((s) => s.rows).find((r) => r.key === btn.dataset.key);
    btn.onclick = () => (row.action ? row.action() : setVisible(row.key, !state.visible[row.key]));
  });
}

function visibleEvents() {
  return state.mode === "belief" ? state.events.filter((e) => e.minute <= state.tick) : state.events;
}

function renderEvents() {
  const list = visibleEvents();
  $("evCount").textContent = `${list.length} of ${state.events.length}`;
  if (!list.length) {
    $("eventList").innerHTML = `<div class="empty"><b>Nothing was known yet</b>Historical belief at T+${state.tick}m hides later reports. Scrub the Time Machine forward.</div>`;
    return;
  }
  $("eventList").innerHTML = list.map((e) => {
    const cat = CATEGORY[e.category] || CATEGORY.INTELLIGENCE, sev = SEVERITY[e.severity], index = state.events.indexOf(e);
    const selected = state.selected && state.selected.id === e.id && state.selected.title === e.title;
    return `<button class="evcard" type="button" role="option" data-index="${index}" aria-selected="${Boolean(selected)}" style="--sev:${sev.color};--c:${cat.color}">
      <span class="ic">${svgIcon(cat.icon, cat.color, 19)}</span>
      <span><span class="sev">${sev.label}</span><h3>${esc(e.title)}</h3>
        <span class="meta"><span>${esc(placeName(e.lat, e.lon))}</span><span>${esc(e.t)}${e.now ? "" : ` · ${replayClock(e.minute)}`}</span><span>${e.sources} source${e.sources === 1 ? "" : "s"}</span></span>
      </span></button>`;
  }).join("");
  const cards = [...document.querySelectorAll(".evcard")];
  cards.forEach((card, i) => {
    card.onclick = () => selectTarget(state.events[Number(card.dataset.index)]);
    card.onkeydown = (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        cards[Math.max(0, Math.min(cards.length - 1, i + (event.key === "ArrowDown" ? 1 : -1)))].focus();
      }
    };
  });
}

function renderTimeline() {
  const pct = (m) => `${(m / MAX_TICK) * 100}%`;
  $("tmFill").style.width = pct(state.tick);
  $("tmThumb").style.left = pct(state.tick);
  const track = $("tmTrack");
  track.setAttribute("aria-valuenow", String(state.tick));
  track.setAttribute("aria-valuetext", `T plus ${state.tick} minutes, ${replayClock(state.tick)}`);
  $("tmMarkers").innerHTML = state.events.map((e) => `<span class="mark${e.minute > state.tick ? " future" : ""}${state.related.has(e.id) ? " related" : ""}"
    style="left:${pct(e.minute)};--sev:${SEVERITY[e.severity].color}" title="${esc(e.t)} · ${esc(e.title)}"></span>`).join("");
  if (MODE_NOW) {
    // WORLD NOW has no replay clock: every time shown is the data's own time.
    const at = state.now?.generated_at;
    $("tmClock").textContent = at ? `Data · ${utcLabel(at).slice(11)}` : "Data · loading";
    $("worldTime").textContent = at ? utcLabel(at) : "Loading";
    track.setAttribute("aria-valuetext", at ? `Data time ${utcLabel(at)}` : "Data loading");
    const scrub = document.querySelector('.tm-modes button[data-mode="replay"]');
    if (scrub) scrub.textContent = "Scrub snapshot";
  } else {
    $("tmClock").textContent = `T+${String(state.tick).padStart(2, "0")}m · ${replayClock(state.tick)}`;
    $("worldTime").textContent = `${(state.world?.world_time ?? "").slice(0, 10)} ${replayClock(state.tick)}`;
  }
  document.querySelectorAll(".tm-modes button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.mode === state.mode)));
  document.querySelectorAll(".speed button").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.speed) === state.speed)));
  $("play").innerHTML = svgIcon(state.playing ? "pause" : "play", "currentColor", 16);
  $("play").setAttribute("aria-label", state.playing ? "Pause replay" : "Play replay");
  $("play").disabled = state.mode === "current";
  $("tmNote").textContent = MODE_NOW && state.now ? {
    replay: "WORLD NOW cache: scrubbing re-polls the current public snapshot. Time travel lives in DEMO REPLAY (remove ?mode=now).",
    belief: "WORLD NOW cache: belief mode needs recorded ticks — switch to DEMO REPLAY for time travel.",
    current: "WORLD NOW: current public cache. Scrubbing re-polls; time travel lives in DEMO REPLAY.",
  }[state.mode] : {
    replay: `Current replay: the world as recorded at T+${state.tick}m. Scrub to watch aircraft, vessels, the storm, and the satellite move.`,
    belief: `Historical belief: only what was known by T+${state.tick}m. Later reports stay hidden until the scrubber reaches them.`,
    current: "Current world: the latest replay state. Live sources are off in this demo.",
  }[state.mode];
}

function updateHud() {
  const w = state.world, u = state.ultra;
  if (!w || !u) return;
  if (MODE_NOW && state.now) {
    const c = state.now.counts || {}, ac = state.airNow?.counts || {};
    const imp = state.importantV2?.n ?? (state.airNow?.important || []).length;
    const online = state.now.sources_online ?? 0;
    const alerts = state.events.filter((e) => SEVERITY[e.severity].rank >= 2).length;
    $("objCount").textContent = fmt((c.total_real || 0) + (ac.total || 0));
    $("srcCount").textContent = `${online} online · REAL DATA`;
    $("aggregates").innerHTML = [["Aircraft", ac.total || 0, CATEGORY.AIR.color],
      ["Events", state.events.length, "#dfe7f1"], ["Alerts", alerts, SEVERITY.ALERT.color],
      ["Important", imp, "#ffb547"], ["Sources online", online, "#46d19a"]]
      .map(([k, v, col]) => `<span class="hudchip"><i class="dot" style="background:${col}"></i>${k} <b class="mono">${fmt(v)}</b></span>`).join("")
      // Aviation is regional and rate-limited: say how much of the world the
      // aircraft count actually covers, so one cluster never reads as "all".
      + (state.airNow?.source_rollup ? `<span class="hudchip" title="adsb.lol regional tiles answering now; aircraft outside them are not shown">Aircraft coverage <b class="mono">${esc(state.airNow.source_rollup.tiles_online)}</b> regions</span>` : "")
      + `<span class="hudchip">REAL DATA · no synthetic objects</span>`;
    updateLod();
    return;
  }
  const air = w.aircraft.length + u.aircraft.length, sea = w.vessels.length + u.vessels.length;
  const alerts = state.events.filter((e) => SEVERITY[e.severity].rank >= 2).length;
  const total = air + sea + u.weather.cells.length + u.road.length + u.cameras.length + u.seismic.length + u.wildfire.length + u.satellite.length + 2;
  $("objCount").textContent = fmt(total);
  $("srcCount").textContent = state.plugins ? `${state.plugins.sources.length} registered` : "Registry offline";
  $("aggregates").innerHTML = [["Aircraft", air, CATEGORY.AIR.color], ["Vessels", sea, CATEGORY.MARITIME.color],
    ["Events", state.events.length, "#dfe7f1"], ["Alerts", alerts, SEVERITY.ALERT.color]]
    .map(([k, v, c]) => `<span class="hudchip"><i class="dot" style="background:${c}"></i>${k} <b class="mono">${fmt(v)}</b></span>`).join("");
  updateLod();
}

function updateLod() {
  if (!map) return;
  const zoom = map.getZoom();
  const level = state.investigating ? [3, "Investigation"] : zoom < 3.2 ? [0, "Globe"] : zoom < 6.5 ? [1, "Region"] : [2, "Local"];
  $("lod").innerHTML = `<span class="hudchip">Level ${level[0]} <b>${level[1]}</b></span>`;
  $("aggregates").hidden = zoom >= 3.2 || state.investigating;
}

/* ------------------------------------------------- truth chrome (1 owner) —
   The ONLY place that writes the top mode banner, the mode pill, and the
   attribution line. Reads state.worldMode exclusively: every surface agrees
   by construction, and no widget invents the mode on its own. */

function syncTruthChrome() {
  const now = state.worldMode === "now";
  document.body.dataset.worldmode = state.worldMode;
  // The static HTML carries the conservative replay wording for no-JS; CSS
  // keeps it unpainted until this first sync so WORLD NOW never flashes it.
  document.body.dataset.truthSynced = "true";
  const badge = $("modeBadge");
  if (badge) {
    badge.className = `badge ${now ? "now" : "replay"}`;
    badge.textContent = now ? "WORLD NOW · real data" : "Replay · synthetic";
  }
  const scenario = $("scenario");
  if (scenario) {
    if (now) {
      scenario.classList.add("now");
      scenario.textContent = "REAL WORLD NOW · real public feeds (delayed, never global LIVE)";
    } else {
      scenario.classList.remove("now");
      scenario.textContent = "SYNTHETIC SCENARIO · replay data, not live";
    }
  }
  const attr = $("attribution");
  if (attr) {
    attr.textContent = now
      ? "Natural Earth (public domain) · MapLibre · real public feeds, delayed — per-source rights"
      : "Natural Earth (public domain) · MapLibre · synthetic replay, not live";
  }
}

/* --------------------------------------------------------------- drawer */

function worldEvidence(found, target) {
  const o = found.obj;
  return {
    what: `${found.kind} ${target.id}`, where: { lat: found.lat, lon: found.lon }, when: `T+${state.tick}m`,
    first_seen: "T0", source: o.provenance ?? state.world.provenance, rights: o.rights ?? state.world.rights,
    observation: o.observation ?? "OBSERVED", confidence: null, precision: o.precision ?? "APPROXIMATE",
    raw_vs_normalized: "generated directly in normalized form (synthetic)",
    blind_spots: found.kind === "vessel" ? ["Open-ocean positions here have no qualified receiver in this demo"] : [],
    model: o.orbit?.model ?? (found.kind === "storm" ? "illustrative storm geometry (not a forecast)" : null),
  };
}

function sourceCards(ev, hero, target) {
  const cards = [];
  if (hero) {
    for (const step of hero.steps) {
      const cat = CATEGORY[LAYER_CATEGORY[step.layer]] || CATEGORY.INTELLIGENCE;
      const own = step.ref === target.id;
      cards.push(`<div class="srccard" style="--c:${cat.color}"><span class="ic">${svgIcon(cat.icon, cat.color, 14)}</span>
        <b>${esc(step.text)}</b>${observationChip(own ? ev.observation : "OBSERVED")}
        <small>${esc(cat.label)} · ${esc(step.at)} · ${replayClock(minuteOf(step.at))} · synthetic source</small></div>`);
    }
    return cards.join("");
  }
  const cat = CATEGORY[target.category] || CATEGORY.INTELLIGENCE;
  return `<div class="srccard" style="--c:${cat.color}"><span class="ic">${svgIcon(cat.icon, cat.color, 14)}</span>
    <b>${esc(ev.source)}</b>${observationChip(ev.observation)}
    <small>Precision ${esc(String(ev.precision).toLowerCase())} · first seen ${esc(humanWhen(ev.first_seen, 0))}</small></div>`;
}

function corroboration(ev, hero) {
  if (hero) {
    const layers = [...new Set(hero.steps.map((s) => LAYER_CATEGORY[s.layer] || "INTELLIGENCE"))];
    const bars = Array.from({ length: 6 }, (_, i) => `<span class="${i < layers.length ? "on" : ""}"></span>`).join("");
    return `<p>${layers.length} independent synthetic layers describe this story: ${layers.map((l) => esc(CATEGORY[l]?.label ?? l)).join(", ")}.</p>
      <div class="bars" aria-hidden="true">${bars}</div>
      <p class="note">Contradictions: none recorded in this replay.</p>`;
  }
  return `<p>Single synthetic source. No other layer corroborates this object in the replay.</p><p class="note">Contradictions: none recorded.</p>`;
}

function relatedEntities(target, ctx) {
  const ents = ENTITY_FOR[target.id] || [];
  const names = Object.fromEntries(state.ultra.entities.map((e) => [e.id, e.label]));
  const rels = state.ultra.relations.filter((r) => ents.includes(r.src) || ents.includes(r.dst)).slice(0, 5);
  const relHtml = rels.length ? rels.map((r) => `<div class="rel"><span>${esc(names[r.src] || r.src)}</span><span class="type">${esc(r.type)}</span><span>${esc(names[r.dst] || r.dst)}</span></div>`).join("")
    : `<p>No charted relations for this object. Absence is stated, not hidden.</p>`;
  const counts = ctx ? [["aircraft", ctx.nearby_aircraft], ["vessels", ctx.nearby_vessels], ["weather cells", ctx.nearby_weather], ["road reports", ctx.nearby_road]]
    .filter(([, list]) => list && list.length).map(([k, list]) => `<span class="chip">${list.length} ${k}</span>`).join("") : "";
  return `${relHtml}${counts ? `<div class="near">${counts}</div><p class="note">Nearby means proximity only, not corroboration.</p>` : ""}
    ${rels.length ? `<div class="actions"><button class="btn" type="button" id="exploreRelations">${svgIcon("graph")} Explore relations</button></div>` : ""}`;
}

function blindSpots(ev, hero) {
  const items = [...new Set([...(ev.blind_spots || []), ...(hero?.blind_spots || [])])];
  const cards = items.map((b) => `<div class="blindcard"><b>Low coverage</b>${esc(b)}</div>`).join("");
  return `${cards || "<p>No coverage gaps recorded for this object.</p>"}<p class="note">Missing data is not evidence that nothing happened.</p>`;
}

function renderDrawer(target, ev, ctx) {
  const cat = CATEGORY[target.category] || CATEGORY.INTELLIGENCE, sev = SEVERITY[target.severity] || SEVERITY.INFO;
  const hero = target.hero ? state.ultra.heroes.find((h) => h.id === target.hero) : null;
  const movable = ["aircraft", "vessel", "satellite", "storm"].includes(target.kind) || /^SYN-(AC|VS|LH|LV)/.test(target.id);
  const status = hero ? "Corroborated story" : ({ OBSERVED: "Reported in replay", INFERRED: "Modeled", CORROBORATED: "Corroborated" }[ev.observation] || "Unverified");
  const confidence = !ev.confidence || ev.confidence === "demo-fixed" ? "Not scored (synthetic demo)" : ev.confidence;
  const lat = ev.where?.lat ?? target.lat, lon = ev.where?.lon ?? target.lon;
  const drawer = $("drawer");
  drawer.style.setProperty("--sev", sev.color);
  drawer.innerHTML = `
    <div class="drawer-top">
      <div class="drawer-nav">
        <button class="btn ghost" type="button" id="backToEvents">${svgIcon("back")} Events</button>
        <span class="chip syn">SYNTHETIC</span>
        <button class="icon-btn close" type="button" id="closeDrawer" aria-label="Close evidence">${svgIcon("close")}</button>
      </div>
      <span class="sev" style="--sev:${sev.color}">${sev.label}</span>
      <span class="chip" style="margin-left:6px">${svgIcon(cat.icon, cat.color, 12)} ${esc(cat.label)}</span>
      <h2 id="drawerTitle">${esc(target.title)}</h2>
      <div class="facts">
        <div class="fact"><span class="k">Status</span><span class="v">${esc(status)}</span></div>
        <div class="fact"><span class="k">Confidence</span><span class="v">${esc(confidence)}</span></div>
        <div class="fact"><span class="k">Time</span><span class="v">${esc(humanWhen(ev.when, target.minute))}</span></div>
        <div class="fact"><span class="k">Location</span><span class="v">${esc(placeName(lat, lon))}</span></div>
      </div>
      <div class="actions">
        <button class="btn primary" type="button" id="investigateBtn">${svgIcon("focus", "#1b1305")} ${state.investigating ? "Exit investigation" : "Enter investigation"}</button>
        <button class="btn" type="button" id="flyBtn">${svgIcon("pin")} Fly to</button>
        ${movable ? `<button class="btn" type="button" id="followBtn" aria-pressed="${state.following === target.id}">${svgIcon("follow")} Follow</button>` : ""}
      </div>
    </div>
    <div class="drawer-body" id="drawerBody">
      <section class="dsec"><h3>Why it matters</h3><p>${esc(WHY[target.category] || WHY.INTELLIGENCE)}</p>
        <p class="note">Editorial template written for this demo, not an AI summary.</p></section>
      <section class="dsec"><h3>Evidence</h3>${sourceCards(ev, hero, target)}</section>
      <section class="dsec"><h3>Corroboration</h3>${corroboration(ev, hero)}</section>
      <section class="dsec"><h3>Related entities</h3>${relatedEntities(target, ctx)}</section>
      <section class="dsec"><h3>Blind spots</h3>${blindSpots(ev, hero)}</section>
      <section class="dsec"><h3>Provenance and rights</h3><dl class="kv">
        <dt>Source</dt><dd>${esc(ev.source)}</dd>
        <dt>Rights</dt><dd>${esc(ev.rights)}</dd>
        <dt>Precision</dt><dd>${esc(String(ev.precision ?? "Not stated").toLowerCase())}</dd>
        <dt>Observation</dt><dd>${observationChip(ev.observation)}</dd>
        <dt>Raw vs normalized</dt><dd>${esc(ev.raw_vs_normalized ?? "fixture equals normalized (synthetic)")}</dd>
        ${ev.model ? `<dt>Model</dt><dd>${esc(ev.model)}</dd>` : ""}
        <dt>Dataset</dt><dd>${esc(isWorldId(target.id) ? state.world.dataset_id : state.ultra.dataset_id)} · replay, not live</dd>
      </dl></section>
    </div>`;
  $("events").hidden = true;
  drawer.hidden = false;
  $("backToEvents").onclick = () => closeDrawer({ keepSelection: true });
  $("closeDrawer").onclick = () => closeDrawer();
  $("investigateBtn").onclick = () => setInvestigation(!state.investigating);
  $("flyBtn").onclick = () => flyToTarget(target);
  if ($("followBtn")) $("followBtn").onclick = () => toggleFollow(target);
  if ($("exploreRelations")) $("exploreRelations").onclick = () => openGraph(target);
}

function renderDrawerLoading(target) {
  $("events").hidden = true;
  $("drawer").hidden = false;
  $("drawer").innerHTML = `<div class="drawer-top"><h2 id="drawerTitle">${esc(target.title)}</h2><p class="muted">Loading evidence…</p></div>
    <div class="drawer-body"><div class="skeleton"></div><div class="skeleton" style="margin-top:8px"></div></div>`;
}

function closeDrawer({ keepSelection = false } = {}) {
  $("drawer").hidden = true;
  $("events").hidden = false;
  if (!keepSelection) {
    state.selected = null;
    state.following = null;
    state.related = new Set();
    map.getSource("selection")?.setData(fc([]));
    if (state.investigating) setInvestigation(false);
  }
  renderEvents();
  renderTimeline();
  updateFocusCard();
}

function relatedIds(target, ctx) {
  const ids = new Set([target.id]);
  const hero = target.hero ? state.ultra.heroes.find((h) => h.id === target.hero) : null;
  for (const step of hero?.steps ?? []) ids.add(step.ref);
  for (const key of ["nearby_aircraft", "nearby_vessels", "nearby_weather", "nearby_road"]) {
    for (const o of ctx?.[key] ?? []) ids.add(o.id);
  }
  return ids;
}

async function selectTarget(target, { fly = true, preset = null } = {}) {
  if (!target) return;
  state.selected = target;
  map.getSource("selection")?.setData(fc([pt(target.lat, target.lon, { id: target.id })]));
  renderEvents();
  renderDrawerLoading(target);
  if (fly) preset ? applyPreset(preset, 2400) : flyToTarget(target);
  if (MODE_NOW && target.now) {
    try {
      const data = await nowEvidence(target.id);
      if (!data) throw new Error("left the live cache");
      if (state.selected !== target) return;
      state.evidence = data;
      state.related = new Set([target.id, ...((data.related || []).flatMap((l) => [l.a, l.b]))]);
      nowDrawer(target, data);
      renderTimeline();
      updateFocusCard();
      announce(`${target.title}. Evidence opened.`);
      writeDeepLink();
    } catch (error) {
      $("drawer").innerHTML = `<div class="drawer-top"><h2 id="drawerTitle">${esc(target.title)}</h2></div>
        <div class="empty"><b>Evidence unavailable</b>${esc(error.message)}. The object is still shown on the map.</div>`;
    }
    return;
  }
  const found = findObject(target.id);
  let ev, ctx = null;
  try {
    ev = isWorldId(target.id) && found
      ? worldEvidence(found, target)
      : await getJSON(`/api/ultra/evidence?id=${encodeURIComponent(target.id)}&kind=${encodeURIComponent(target.kind || "object")}`);
    if (target.lat != null) ctx = await getJSON(`/api/ultra/context?lat=${target.lat}&lon=${target.lon}`);
  } catch (error) {
    $("drawer").innerHTML = `<div class="drawer-top"><h2 id="drawerTitle">${esc(target.title)}</h2></div>
      <div class="empty"><b>Evidence unavailable</b>${esc(error.message)}. The object is still shown on the map.</div>`;
    return;
  }
  if (state.selected !== target) return;
  state.evidence = ev;
  state.context = ctx;
  state.related = relatedIds(target, ctx);
  renderDrawer(target, ev, ctx);
  if (state.investigating) applyInvestigationStyle();
  renderTimeline();
  updateFocusCard();
  announce(`${target.title}. ${SEVERITY[target.severity]?.label ?? ""}. Evidence opened.`);
}

function targetFromFeature(feature) {
  const p = feature.properties || {};
  if (MODE_NOW && state.now) {
    // Change pins resolve to their event targets (severity, drawer data).
    if (typeof p.id === "string" && p.id.startsWith("chg:")) {
      const existing = state.events.find((e) => e.id === p.id);
      if (existing) return existing;
    }
    const nowHit = findNowObject(p.id);
    if (nowHit) return { id: p.id, kind: p.kind, title: p.label || p.id, severity: "INFO",
      category: KIND_CATEGORY[p.kind] || "INTELLIGENCE", lat: nowHit.lat, lon: nowHit.lon,
      t: "live", minute: MAX_TICK, sources: 1, hero: null, now: true };
    // WORLD NOW has no replay pools: anything without a live object (e.g. a
    // STATIC reference pin) stays flagged now so selectTarget takes the live
    // evidence path — which reports UNAVAILABLE truthfully instead of
    // opening the replay drawer on a real-data screen.
    const [lon, lat] = feature.geometry.type === "Point" ? feature.geometry.coordinates : [null, null];
    return { id: p.id, kind: p.kind, title: p.label || p.id, severity: "INFO", category: KIND_CATEGORY[p.kind] || "INTELLIGENCE",
      lat, lon, t: "live", minute: MAX_TICK, sources: 1, hero: null, now: true };
  }
  const found = findObject(p.id);
  const existing = state.events.find((e) => e.id === p.id);
  if (existing) return existing;
  const [lon, lat] = feature.geometry.type === "Point" ? feature.geometry.coordinates : [found?.lon, found?.lat];
  return { id: p.id, kind: p.kind, title: p.label || p.id, severity: "INFO", category: KIND_CATEGORY[p.kind] || "INTELLIGENCE",
    lat: found?.lat ?? lat, lon: found?.lon ?? lon, t: `T+${state.tick}m`, minute: state.tick, sources: 1, hero: null };
}

/* ------------------------------------------------------ investigation */

const DIMMABLE = [["air-point", "icon-opacity"], ["sea-point", "icon-opacity"], ["road-point", "icon-opacity"],
  ["camera-point", "icon-opacity"], ["infra-point", "icon-opacity"], ["fire-point", "icon-opacity"],
  ["quake-point", "circle-opacity"], ["event-core", "circle-opacity"], ["change-ring", "circle-opacity"]];

function applyInvestigationStyle() {
  const ids = [...state.related];
  for (const [layer, prop] of DIMMABLE) {
    if (!map.getLayer(layer)) continue;
    map.setPaintProperty(layer, prop, state.investigating ? ["case", ["in", ["get", "id"], ["literal", ids]], 1, 0.16] : 1);
  }
  const contextLayers = {
    "air-cluster": ["circle-opacity", 0.2], "sea-cluster": ["circle-opacity", 0.2],
    "corridor-line": ["line-opacity", ["interpolate", ["linear"], ["zoom"], 1, 0.28, 6, 0.12]],
    "lane-line": ["line-opacity", 0.26],
    "storm-fill": ["fill-opacity", ["interpolate", ["linear"], ["zoom"], 2,
      ["match", ["get", "intensity"], "HIGH", 0.34, "MODERATE", 0.22, 0.13], 7,
      ["match", ["get", "intensity"], "HIGH", 0.18, "MODERATE", 0.11, 0.07], 9, 0.03]],
    "cell-fill": ["fill-opacity", ["interpolate", ["linear"], ["zoom"], 5, 0.14, 8, 0.09, 11, 0.05]],
    "sat-swath-fill": ["fill-opacity", ["interpolate", ["linear"], ["zoom"], 2, 0.07, 7, 0.09, 10, 0.04]],
  };
  for (const [layer, [prop, base]] of Object.entries(contextLayers)) {
    if (!map.getLayer(layer)) continue;
    map.setPaintProperty(layer, prop, state.investigating ? 0.04 : base);
  }
}

function setInvestigation(on, { fly = true } = {}) {
  state.investigating = Boolean(on && state.selected);
  document.body.classList.toggle("investigating", state.investigating);
  applyInvestigationStyle();
  if (state.investigating && fly) flyToTarget(state.selected, 9.4);
  if (!state.investigating && fly && !CAPTURE) applyPreset("hero", 2000);
  if (state.selected && state.evidence) renderDrawer(state.selected, state.evidence, state.context);
  renderTimeline();
  updateLod();
  announce(state.investigating ? "Investigation mode. Unrelated layers dimmed." : "Investigation closed. Back to the world view.");
}

/* ---------------------------------------------------------------- camera */

function chromePadding() {
  if (state.focus) return { top: 70, bottom: 40, left: 40, right: 40 };
  const rect = (id) => $(id).getBoundingClientRect();
  return { top: rect("topbar").height + 16, bottom: rect("timeline").height + 30,
    left: rect("rail").width + 36, right: rect("side").width + 36 };
}

function applyPreset(name, duration = 0) {
  const preset = CAMERA_PRESETS[name] || CAMERA_PRESETS.world;
  const options = { ...preset, padding: chromePadding(), essential: true };
  if (duration <= 0 || REDUCED_MOTION) map.jumpTo(options);
  else map.flyTo({ ...options, duration, curve: 1.3 });
}

function flyToTarget(target, zoom = null) {
  if (!target || target.lat == null) return;
  // WORLD NOW selections keep regional context (nearby activity + geography
  // + open drawer); replay keeps the tighter operational zoom.
  const resolvedZoom = zoom ?? (target.now ? 5.5 : 8.2);
  const options = { center: [target.lon, target.lat], zoom: Math.max(resolvedZoom, Math.min(map.getZoom(), 12)),
    pitch: target.now ? 30 : 45, bearing: map.getBearing(), padding: chromePadding(), essential: true };
  if (REDUCED_MOTION) map.jumpTo(options);
  else map.flyTo({ ...options, duration: 1900, curve: 1.35 });
}

function toggleFollow(target) {
  state.following = state.following === target.id ? null : target.id;
  $("followBtn")?.setAttribute("aria-pressed", String(state.following === target.id));
  if (state.following) followSelected();
  announce(state.following ? `Following ${target.title}` : "Stopped following");
}

function followSelected() {
  const found = findObject(state.following);
  if (!found) return;
  const options = { center: [found.lon, found.lat], padding: chromePadding() };
  if (REDUCED_MOTION) map.jumpTo(options); else map.easeTo({ ...options, duration: 900 });
}

function toggleFocus(force) {
  state.focus = typeof force === "boolean" ? force : !state.focus;
  document.body.classList.toggle("focus", state.focus);
  map.setPadding(chromePadding());
  updateFocusCard();
  announce(state.focus ? "Focus mode. Press F to show panels." : "Panels shown.");
}

function updateFocusCard() {
  const target = state.selected;
  const card = $("focusCard");
  if (!target) {
    card.innerHTML = MODE_NOW && state.now
      ? `<span class="chip real">REAL DATA</span><h2>The world, right now</h2><p class="muted">Live public feeds · Press F to show panels · Ctrl K to search</p>`
      : `<span class="chip syn">SYNTHETIC</span><h2>The world, right now in replay</h2><p class="muted">Press F to show panels · Ctrl K to search</p>`;
    return;
  }
  const sev = SEVERITY[target.severity] || SEVERITY.INFO;
  card.innerHTML = `<span class="sev" style="--sev:${sev.color}">${sev.label}</span> ${MODE_NOW && target.now ? `<span class="chip real">REAL DATA</span>` : `<span class="chip syn">SYNTHETIC</span>`}
    <h2>${esc(target.title)}</h2><p class="muted">${esc(placeName(target.lat, target.lon))} · ${esc(target.t)}${target.now ? "" : ` · ${replayClock(target.minute)}`} · press F to show panels</p>`;
}

/* ------------------------------------------------------------------ time */

async function setTick(next, { animate = true } = {}) {
  const tick = Math.max(0, Math.min(MAX_TICK, Math.round(next)));
  if (state.mode === "current" && tick !== MAX_TICK) state.mode = "replay";
  const previous = state.tick;
  state.tick = tick;
  renderTimeline();
  let payload;
  try {
    payload = await loadTick(tick);
  } catch (error) {
    $("tmNote").textContent = `Replay data for T+${tick}m is unavailable: ${error.message}`;
    return;
  }
  if (state.tick !== tick) return;
  const before = buildData();
  [state.ultra, state.world] = payload;
  const after = buildData();
  if (animate && !REDUCED_MOTION && previous !== tick && after.air.features.length < 3000) {
    await tweenMovers(before, after, Math.min(900, 1400 / state.speed));
  }
  updateSources(after);
  renderEvents();
  renderTimeline();
  updateHud();
  if (state.following) followSelected();
  loadTick(Math.min(MAX_TICK, tick + 1)).catch(() => {});
}

function tweenMovers(before, after, duration) {
  return new Promise((resolve) => {
    const pairs = ["air", "sea"].map((key) => {
      const start = new Map(before[key].features.map((f) => [f.properties.id, f.geometry.coordinates]));
      return [key, after[key], start];
    });
    const t0 = performance.now();
    const frame = (now) => {
      const k = Math.min(1, (now - t0) / duration), e = 1 - (1 - k) ** 3;
      for (const [key, target, start] of pairs) {
        const features = target.features.map((f) => {
          const s = start.get(f.properties.id);
          if (!s) return f;
          const [x2, y2] = f.geometry.coordinates;
          let dx = x2 - s[0];
          if (dx > 180) dx -= 360; else if (dx < -180) dx += 360;
          return { ...f, geometry: { type: "Point", coordinates: [s[0] + dx * e, s[1] + (y2 - s[1]) * e] } };
        });
        map.getSource(key)?.setData(fc(features));
      }
      if (k < 1) requestAnimationFrame(frame); else resolve();
    };
    requestAnimationFrame(frame);
  });
}

function setMode(mode) {
  state.mode = mode;
  if (mode === "current") { stopPlay(); setTick(MAX_TICK); }
  renderEvents();
  renderTimeline();
  announce({ current: "Current world", belief: "Historical belief", replay: "Current replay" }[mode]);
}

function stopPlay() {
  state.playing = false;
  clearInterval(state.timer);
  state.timer = null;
  renderTimeline();
}

function togglePlay(force) {
  const play = typeof force === "boolean" ? force : !state.playing;
  if (!play || state.mode === "current") { stopPlay(); return; }
  if (state.tick >= MAX_TICK) setTick(0, { animate: false });
  state.playing = true;
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    if (state.tick >= MAX_TICK) { stopPlay(); return; }
    setTick(state.tick + 1);
  }, 1600 / state.speed);
  renderTimeline();
}

function wireTimeline() {
  document.querySelectorAll(".tm-modes button").forEach((b) => { b.onclick = () => setMode(b.dataset.mode); });
  document.querySelectorAll(".speed button").forEach((b) => {
    b.onclick = () => { state.speed = Number(b.dataset.speed); if (state.playing) togglePlay(true); renderTimeline(); };
  });
  $("play").onclick = () => togglePlay();
  $("now").onclick = () => setMode("current");
  const track = $("tmTrack");
  const fromPointer = (event) => {
    const rect = track.getBoundingClientRect();
    return ((event.clientX - rect.left) / rect.width) * MAX_TICK;
  };
  let dragging = false;
  track.onpointerdown = (event) => { dragging = true; track.setPointerCapture(event.pointerId); stopPlay(); setTick(fromPointer(event), { animate: false }); };
  track.onpointermove = (event) => { if (dragging) setTick(fromPointer(event), { animate: false }); };
  track.onpointerup = () => { dragging = false; };
  track.onkeydown = (event) => {
    const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 3, PageDown: -3 }[event.key];
    if (step) { event.preventDefault(); setTick(state.tick + step); }
    if (event.key === "Home") setTick(0);
    if (event.key === "End") setTick(MAX_TICK);
  };
}

/* ------------------------------------------------------------ palette */

const COMMANDS = [
  { label: "Go to a place", hint: "cities, ports, airports", icon: "pin", prefix: "go " },
  { label: "Find aircraft", hint: "by callsign or id", icon: "plane", prefix: "aircraft " },
  { label: "Find vessel", hint: "by name or id", icon: "ship", prefix: "vessel " },
  { label: "Find airport", hint: "reference and fictional", icon: "airport", prefix: "airport " },
  { label: "Find port", hint: "fictional harbour", icon: "anchor", prefix: "port " },
  { label: "Show fires", icon: "fire", run: () => { setVisible("wildfire", true); applyPreset("earth", 1800); } },
  { label: "Show earthquakes", icon: "quake", run: () => { setVisible("seismic", true); selectById("SYN-EQ00", "earth"); } },
  { label: "Show severe weather", icon: "cloud", run: () => { setVisible("storm", true); setVisible("weather", true); selectById("SYN-ALERT-01", "port"); } },
  { label: "Show source health", icon: "signal", run: () => openSources() },
  { label: "Show blind spots", icon: "hatch", run: () => setVisible("blind", true) },
  { label: "Replay the scenario from T0", hint: "12-minute replay", icon: "play", run: () => { setMode("replay"); setTick(0, { animate: false }); togglePlay(true); } },
  { label: "Reset globe", hint: "R", icon: "reset", run: () => applyPreset("world", 1800) },
  { label: "Focus mode", hint: "F", icon: "focus", run: () => toggleFocus() },
  { label: "Story: storm at the port", icon: "cloud", run: () => selectById("SYN-ALERT-01", "port") },
  { label: "Story: holding over the airfield", icon: "airport", run: () => selectById("SYN-AC001", "airport") },
  { label: "Story: offshore earthquake", icon: "quake", run: () => selectById("SYN-EQ00", "earth") },
];

function selectById(id, preset) {
  const event = state.events.find((e) => e.id === id);
  if (event) { selectTarget(event, { preset }); return; }
  const found = findObject(id);
  if (found) selectTarget({ id, kind: found.kind, title: id, severity: "INFO", category: KIND_CATEGORY[found.kind] || "INTELLIGENCE",
    lat: found.lat, lon: found.lon, t: `T+${state.tick}m`, minute: state.tick, sources: 1, hero: null }, { preset });
}

function searchItems(query) {
  const q = query.trim().toLowerCase();
  const scope = (/^(go|aircraft|vessel|airport|port) /.exec(q) || [])[1] || "";
  const term = scope ? q.slice(scope.length + 1).trim() : q;
  const u = state.ultra, w = state.world, items = [];
  const push = (kind, label, hint, icon, run) => items.push({ kind, label, hint, icon, run });
  const place = (lat, lon, zoom) => () => { map.flyTo({ center: [lon, lat], zoom, padding: chromePadding(), essential: true, duration: REDUCED_MOTION ? 0 : 1800 }); };
  if (!scope || scope === "go") for (const c of w.cities) push("place", c.name, "City", "pin", place(c.lat, c.lon, 6));
  // Replay objects are synthetic: never offer them while showing WORLD NOW.
  if (!MODE_NOW) {
    if (!scope || scope === "aircraft") for (const a of [...u.aircraft, ...w.aircraft]) push("aircraft", a.callsign, `${a.id} · ${a.route ?? `${fmt(a.alt_ft)} ft`}`, "plane", () => selectById(a.id));
    if (!scope || scope === "vessel") for (const v of [...u.vessels, ...w.vessels]) push("vessel", v.name, `${v.id} · ${v.speed_kt} kt`, "ship", () => selectById(v.id));
    if (!scope || scope === "airport" || scope === "go") {
      for (const a of w.airports) push("airport", `${a.code} · ${a.name}`, "Airport (reference)", "airport", place(a.lat, a.lon, 9));
      for (const a of u.airports) push("airport", `${a.name} (fictional)`, "Scenario airfield", "airport", () => selectById(a.id, "airport"));
    }
    if (!scope || scope === "port" || scope === "go") for (const p of u.ports) push("port", `${p.name} (fictional)`, "Scenario harbour", "anchor", () => selectById(p.id, "port"));
  }
  if (MODE_NOW && state.airNow) {
    for (const o of state.airNow.states || state.airNow.positions || []) {
      if ((o.callsign || "").toLowerCase().includes(term) || o.icao24.includes(term) || (o.type || "").toLowerCase() === term)
        push("aircraft", o.callsign !== "UNKNOWN" ? o.callsign : o.icao24, `${o.icao24} · live ADS-B`, "plane", ((hex) => () => selectNowTarget("AIR:" + hex))(o.icao24));
      if (items.length >= 60) break;
    }
    const sg = state.now?.static_geo || {};
    for (const kind of ["airports", "ports"]) for (const o of sg[kind] || []) {
      const hay = `${o.name || ""} ${o.city || ""} ${o.country || ""} ${o.id || ""}`.toLowerCase();
      if (term && hay.includes(term)) push(kind === "airports" ? "airport" : "port", `${o.name} (static reference)`, o.id, kind === "airports" ? "airport" : "anchor",
        ((la, lo) => () => { map.flyTo({ center: [lo, la], zoom: 7, essential: true }); })(o.lat, o.lon));
    }
  }
  if (!scope) for (const e of state.events) push("event", e.title, `${SEVERITY[e.severity].label} · ${e.t}`, (CATEGORY[e.category] || CATEGORY.INTELLIGENCE).icon, () => selectTarget(e));
  const commands = scope ? [] : COMMANDS
    .filter((c) => !(MODE_NOW && /^Story:/.test(c.label))) // demo stories select synthetic objects
    .map((c) => ({ kind: "command", label: c.label, hint: c.hint ?? "Command", icon: c.icon, run: c.run, prefix: c.prefix }));
  const matches = (item) => !term || item.label.toLowerCase().includes(term) || String(item.hint).toLowerCase().includes(term);
  return [...commands.filter(matches), ...items.filter(matches)].slice(0, 40);
}

function renderPalette() {
  const input = $("paletteInput");
  state.paletteItems = searchItems(input.value);
  state.paletteIndex = Math.min(state.paletteIndex, Math.max(0, state.paletteItems.length - 1));
  $("paletteList").innerHTML = state.paletteItems.length ? state.paletteItems.map((item, i) => `
    <li role="option" id="pal-${i}" data-i="${i}" aria-selected="${i === state.paletteIndex}">
      <span class="ic">${svgIcon(item.icon, "currentColor", 15)}</span><span>${esc(item.label)}</span><small>${esc(item.hint ?? "")}</small></li>`).join("")
    : `<li class="group">No match. Try a city, a callsign such as SYN001, or a command.</li>`;
  input.setAttribute("aria-activedescendant", state.paletteItems.length ? `pal-${state.paletteIndex}` : "");
  document.querySelectorAll("#paletteList li[role=option]").forEach((li) => {
    li.onclick = () => runPaletteItem(Number(li.dataset.i));
    li.onmousemove = () => { if (state.paletteIndex !== Number(li.dataset.i)) { state.paletteIndex = Number(li.dataset.i); renderPalette(); } };
  });
  document.getElementById(`pal-${state.paletteIndex}`)?.scrollIntoView({ block: "nearest" });
}

function runPaletteItem(index) {
  const item = state.paletteItems[index];
  if (!item) return;
  if (item.prefix) { $("paletteInput").value = item.prefix; state.paletteIndex = 0; renderPalette(); return; }
  closeDialog("palette");
  item.run?.();
}

function openPalette() {
  $("palette").hidden = false;
  $("paletteInput").value = "";
  state.paletteIndex = 0;
  renderPalette();
  $("paletteInput").focus();
}

function wirePalette() {
  const input = $("paletteInput");
  input.oninput = () => { state.paletteIndex = 0; renderPalette(); };
  input.onkeydown = (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const n = state.paletteItems.length;
      if (n) state.paletteIndex = (state.paletteIndex + (event.key === "ArrowDown" ? 1 : n - 1)) % n;
      renderPalette();
    } else if (event.key === "Enter") {
      event.preventDefault();
      runPaletteItem(state.paletteIndex);
    }
  };
  $("palette").onclick = (event) => { if (event.target === $("palette")) closeDialog("palette"); };
}

/* -------------------------------------------------------------- dialogs */

function closeDialog(id) {
  $(id).hidden = true;
  if (id === "palette") $("cmd").focus();
}

function sourceStatus(source) {
  if (source.source_id === "synthetic-replay") return ["ONLINE", "Replay running locally", "0 ms (local)"];
  if (source.auth === "user-key" || source.status === "USER_KEY") return ["OFFLINE", "Needs your own key; none is configured", "Not measured"];
  if (source.status === "QUALIFIED") return ["UNKNOWN", "Qualified source, not polled in this demo", "Not measured"];
  return ["UNKNOWN", "Not polled in this demo", "Not measured"];
}

async function openSources() {
  $("sources").hidden = false;
  const body = $("sourcesBody");
  if (MODE_NOW && state.now) {
    const rows = (state.now.health || []).map((h) => [
      h.source_id, h.coverage || h.truth_mode || "",
      h.state, `last ok ${utcLabel(h.last_success)}${h.latency_ms != null ? ` · ${h.latency_ms} ms` : ""} · next ${utcLabel(h.next_refresh)}`,
      h.rights || ""]);
    const air = state.airNow?.source_rollup;
    if (air) rows.push([`adsb.lol (live aviation)`, "regional tiles",
      air.state, `tiles ${air.tiles_online} · ${air.aircraft} aircraft`, air.rights]);
    const counts = rows.reduce((acc, r) => ({ ...acc, [r[2]]: (acc[r[2]] || 0) + 1 }), {});
    body.innerHTML = `<div class="summary-row">${["ONLINE", "DEGRADED", "STALE", "OFFLINE", "RATE_LIMITED", "UNKNOWN"].map((k) => `<span class="hudchip"><span class="state ${k}">${k}</span><b class="mono">${counts[k] || 0}</b></span>`).join("")}</div>
      <table class="health-table"><thead><tr><th>Source</th><th>State</th><th>Freshness / latency</th><th>Rights</th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td><b>${esc(r[0])}</b>${esc(String(r[1]).toLowerCase())}</td><td><span class="state ${r[2]}">${r[2]}</span><br>${esc(r[3])}</td><td>${esc(r[4])}</td><td>${esc(r[5])}</td></tr>`).join("")}
      </tbody></table><p class="note">Live per-leg health from the backend just now. Unavailable domains say KEY REQUIRED or NO QUALIFIED SOURCE instead of hiding.</p>`;
    body.parentElement.querySelector(".close").focus();
    return;
  }
  if (!state.plugins) {
    body.innerHTML = `<div class="skeleton"></div>`;
    try { state.plugins = await getJSON("/api/plugins"); updateHud(); } catch (error) {
      body.innerHTML = `<div class="empty"><b>Source registry unavailable</b>${esc(error.message)}</div>`;
      return;
    }
  }
  const stale = state.ultra.cameras.filter((c) => c.status !== "OK").length;
  const rows = state.plugins.sources.map((s) => [s.title || s.source_id, s.category, ...sourceStatus(s), s.data_rights]);
  rows.unshift(["Synthetic public cameras", "PUBLIC_CAMERA", stale ? "STALE" : "ONLINE",
    stale ? `${stale} of ${state.ultra.cameras.length} snapshots are stale` : "All snapshots fresh", "Replay", "CC0 synthetic"]);
  const counts = rows.reduce((acc, r) => ({ ...acc, [r[2]]: (acc[r[2]] || 0) + 1 }), {});
  body.innerHTML = `<div class="summary-row">${["ONLINE", "DEGRADED", "STALE", "OFFLINE", "UNKNOWN"].map((k) => `<span class="hudchip"><span class="state ${k}">${k}</span><b class="mono">${counts[k] || 0}</b></span>`).join("")}</div>
    <table class="health-table"><thead><tr><th>Source</th><th>State</th><th>Freshness / latency</th><th>Rights</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td><b>${esc(r[0])}</b>${esc(String(r[1]).toLowerCase())}</td><td><span class="state ${r[2]}">${r[2]}</span><br>${esc(r[3])}</td><td>${esc(r[4])}</td><td>${esc(r[5])}</td></tr>`).join("")}
    </tbody></table><p class="note">States describe this demo honestly: nothing live is polled, so real sources show UNKNOWN or OFFLINE.</p>`;
  body.parentElement.querySelector(".close").focus();
}

function openGraph(target) {
  const ents = ENTITY_FOR[target.id] || [];
  const names = Object.fromEntries(state.ultra.entities.map((e) => [e.id, e.label]));
  const rels = state.ultra.relations.filter((r) => ents.includes(r.src) || ents.includes(r.dst)).slice(0, 10);
  const centreId = ents[0];
  const others = [...new Set(rels.map((r) => (r.src === centreId ? r.dst : r.src)))];
  const nodes = others.map((id, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, others.length) - Math.PI / 2;
    return { id, x: 450 + 240 * Math.cos(angle), y: 190 + 130 * Math.sin(angle) };
  });
  const edges = rels.map((r) => {
    const other = nodes.find((n) => n.id === (r.src === centreId ? r.dst : r.src));
    return `<line x1="450" y1="190" x2="${other.x}" y2="${other.y}" stroke="rgba(178,191,206,.35)" stroke-width="1.4"/>
      <text x="${(450 + other.x) / 2}" y="${(190 + other.y) / 2 - 6}" fill="#8290a3" font-size="11" text-anchor="middle" font-family="Inter">${esc(r.type)}</text>`;
  }).join("");
  const node = (id, x, y, main) => `<g><circle cx="${x}" cy="${y}" r="${main ? 26 : 18}" fill="${main ? "#2a1d08" : "#16212f"}" stroke="${main ? "#ffb547" : "#4a6883"}" stroke-width="1.6"/>
    <text x="${x}" y="${y + (main ? 44 : 34)}" fill="#e8eef6" font-size="12.5" text-anchor="middle" font-family="Inter">${esc(names[id] || id)}</text></g>`;
  $("graphBody").innerHTML = `<svg viewBox="0 0 900 380" role="img" aria-label="Relations of ${esc(names[centreId] || centreId)}">${edges}${nodes.map((n) => node(n.id, n.x, n.y, false)).join("")}${node(centreId, 450, 190, true)}</svg>
    <p class="note">Bounded to direct relations. Each edge carries method, evidence, and confidence in the drawer.</p>`;
  $("graphDialog").hidden = false;
  $("graphDialog").querySelector(".close").focus();
}

/* ---------------------------------------------------------------- map UI */

const INTERACTIVE = ["air-point", "sea-point", "air-cluster", "sea-cluster", "sat-pos", "quake-point", "fire-point", "road-point",
  "camera-point", "infra-point", "notice-point", "event-core", "change-ring", "alert-fill", "cell-fill", "storm-fill", "sat-swath-fill", "blind-fill", "notice-fill"];

function featureAt(point) {
  const layers = INTERACTIVE.filter((id) => map.getLayer(id) && map.getLayoutProperty(id, "visibility") !== "none");
  return map.queryRenderedFeatures(point, { layers })[0] || null;
}


/* ------------------------------------------------------- LIVE EARTH —
   GIBS freshness layer (WORLD NOW only). Single active raster source
   under all overlays; STANDARD vector basemap stays the default.
   Imagery is context: it never touches event truth, Important Now,
   changes, or Sentinel evidence. Replay never reaches this code. */

async function loadLiveEarth() {
  // NOW-only entry point: replay returns before any imagery status,
  // tile URL, or layer can load. STANDARD is the default; the user
  // opts into LIVE EARTH explicitly (toolbar or E key).
  if (!MODE_NOW) return false;
  return true;
}

// NOTE: tile URLs arrive exclusively from /api/world/imagery/status
// (verified dates, rights-checked). This file must contain no remote
// tile endpoint literal: the offline UI contract forbids it, and the
// backend stays the single URL source.
function earthAgeText(ageSeconds) {
  if (ageSeconds == null) return "age unknown";
  const h = ageSeconds / 3600;
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} min old`;
  if (h < 48) return `${h.toFixed(1)} h old`;
  return `${(h / 24).toFixed(1)} days old`;
}

function earthClassLabel(cls) {
  return { VERY_FRESH: "very fresh", FRESH: "fresh", AGING: "aging",
    STALE: "stale", NO_COVERAGE: "no coverage" }[cls] || "unknown";
}

function renderEarthInfo() {
  const box = $("earthInfo");
  const live = state.liveEarth;
  if (!MODE_NOW || live.mode !== "live") { box.hidden = true; box.innerHTML = ""; return; }
  if (live.outage) {
    box.hidden = false;
    box.innerHTML = `<span class="hudchip"><i class="dot" style="background:#ff8a5b"></i>LIVE EARTH \u00b7 imagery source unavailable \u2014 vector basemap</span>`;
    box.title = "The imagery provider failed repeatedly just now; the standard vector globe is shown instead. Overlays are unaffected.";
    return;
  }
  const rec = live.layer;
  if (!rec || rec.rights_status !== "ATTRIBUTION_REQUIRED" || !rec.tile_url) {
    box.hidden = false;
    box.innerHTML = `<span class="hudchip"><i class="dot" style="background:#8a93a6"></i>LIVE EARTH · no current imagery — vector basemap</span>`;
    box.title = "No imagery layer verified right now; the standard vector globe is shown instead. No coverage is faked.";
    return;
  }
  const cls = rec.freshness_class || "NO_COVERAGE";
  const dot = { VERY_FRESH: "#3fe0b0", FRESH: "#3fe0b0", AGING: "#ffc857", STALE: "#ff8a5b", NO_COVERAGE: "#8a93a6" }[cls] || "#8a93a6";
  box.hidden = false;
  box.innerHTML = `<span class="hudchip"><i class="dot" style="background:${dot}"></i>LIVE EARTH · ${esc(rec.dataset || rec.layer)} · ${esc(earthClassLabel(cls)).toUpperCase()} · ${esc(earthAgeText(rec.age_seconds))} · NASA GIBS</span>`;
  box.title = `${rec.dataset || rec.layer} · captured ${rec.captured_at} (${earthAgeText(rec.age_seconds)}) · ~${rec.resolution_m ?? "?"} m/px · ${earthClassLabel(cls)} · ${rec.rights?.attribution || "NASA GIBS"}`;
  announce(`Live Earth: ${rec.dataset || rec.layer}, ${earthClassLabel(cls)}, ${earthAgeText(rec.age_seconds)}.`);
}

function applyEarthPaint() {
  if (!map.getLayer("liveearth-raster")) return;
  const cls = state.liveEarth.layer?.freshness_class || "NO_COVERAGE";
  // MapLibre saturation is an OFFSET (-1..1, 0 = unchanged): never boost.
  const paint = { VERY_FRESH: [0, 1], FRESH: [0, 1], AGING: [-0.25, 1], STALE: [-0.55, 0.92], NO_COVERAGE: [0, 0] }[cls] || [0, 0];
  map.setPaintProperty("liveearth-raster", "raster-saturation", paint[0]);
  map.setPaintProperty("liveearth-raster", "raster-opacity", paint[1]);
}

function setLiveEarthSource(rec) {
  state.liveEarth.layer = rec || null;
  if (rec) state.liveEarth.outage = false;
  for (const id of ["land-fill", "country-border", "coastline"]) {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", rec ? "none" : "visible");
  }
  if (map.getLayer("liveearth-raster")) map.removeLayer("liveearth-raster");
  if (map.getSource("liveearth")) map.removeSource("liveearth");
  if (rec && rec.rights_status === "ATTRIBUTION_REQUIRED" && rec.tile_url) {
    map.addSource("liveearth", { type: "raster", tiles: [rec.tile_url], tileSize: 256, maxzoom: rec.matrix?.includes("Level9") ? 9 : 7, attribution: "NASA GIBS" });
    map.addLayer({ id: "liveearth-raster", type: "raster", source: "liveearth",
      paint: { "raster-saturation": 0, "raster-opacity": 1 } }, "night-fill");
    applyEarthPaint();
  }
  renderEarthInfo();
  document.querySelector('[data-camera="earth"]')?.setAttribute("aria-pressed", state.liveEarth.mode === "live" ? "true" : "false");
}

async function refreshLiveEarth(reason) {
  if (!MODE_NOW || state.liveEarth.mode !== "live" || !map) return;
  try {
    const c = map.getCenter();
    const st = await getJSON(`/api/world/imagery/status?lat=${c.lat.toFixed(2)}&lon=${c.lng.toFixed(2)}`);
    state.liveEarth.status = st;
    const rec = (st.layers || []).find((l) => l.layer === st.selected) || null;
    const changed = (rec?.layer || null) !== (state.liveEarth.layer?.layer || null)
      || (rec?.captured_at || null) !== (state.liveEarth.layer?.captured_at || null);
    if (changed || reason === "toggle") setLiveEarthSource(rec);
    else renderEarthInfo();
  } catch (_) {
    setLiveEarthSource(null);
  }
}

function toggleLiveEarth() {
  if (!MODE_NOW) return;
  state.liveEarth.mode = state.liveEarth.mode === "live" ? "standard" : "live";
  if (state.liveEarth.mode === "live") {
    announce("Live Earth imagery on. Standard vector basemap off.");
    refreshLiveEarth("toggle");
  } else {
    setLiveEarthSource(null);
    announce("Standard vector basemap. Live Earth imagery off.");
  }
}

let earthTileErrors = 0;
let earthTileWindow = 0;
function noteEarthTileError() {
  // Single bad tiles (swath edges) are noise; sustained failure
  // (5 errors inside 30 s) falls back to the vector basemap.
  const t = Date.now();
  if (t - earthTileWindow > 30000) { earthTileErrors = 0; earthTileWindow = t; }
  earthTileErrors += 1;
  if (earthTileErrors < 5 || state.liveEarth.mode !== "live") return;
  earthTileErrors = 0;
  state.liveEarth.outage = true;
  setLiveEarthSource(null);
  state.liveEarth.outage = true;
  renderEarthInfo();
  announce("Live Earth imagery source unavailable. Vector basemap shown.");
}

function showEarthPopup(event) {
  const rec = state.liveEarth.layer;
  const tip = $("tooltip");
  if (!rec || rec.rights_status !== "ATTRIBUTION_REQUIRED" || !rec.tile_url) {
    tip.innerHTML = `<b>Live Earth</b>No verified imagery here right now — vector basemap shown. No coverage is faked.`;
  } else {
    tip.innerHTML = `<b>${esc(rec.dataset || rec.layer)}</b>${esc(rec.source)} · captured ${esc(rec.captured_at || "UNKNOWN")} (${esc(earthAgeText(rec.age_seconds))}) · ~${rec.resolution_m ?? "?"} m/px · ${esc(earthClassLabel(rec.freshness_class))}<br><span class="chip real">NASA GIBS · public domain</span>`;
  }
  tip.style.left = `${event.originalEvent.clientX + 14}px`;
  tip.style.top = `${event.originalEvent.clientY + 14}px`;
  tip.hidden = false;
  clearTimeout(showEarthPopup._t);
  showEarthPopup._t = setTimeout(() => { tip.hidden = true; }, 6000);
}

function wireLiveEarth() {
  // NOW-only wiring: moveend reselects the single active source
  // (debounced; backend capabilities are TTL-cached). Replay never
  // calls this, so replay can never load provider-hosted imagery.
  if (!MODE_NOW || !map) return;
  let timer = null;
  map.on("moveend", () => {
    if (state.liveEarth.mode !== "live") return;
    clearTimeout(timer);
    timer = setTimeout(() => refreshLiveEarth("move"), 1000);
  });
}

function wireMap() {
  let pending = null;
  map.on("mousemove", (event) => {
    if (pending) return;
    pending = requestAnimationFrame(() => {
      pending = null;
      const feature = featureAt(event.point);
      map.getCanvas().style.cursor = feature ? "pointer" : "";
      const tip = $("tooltip");
      if (!feature) { tip.hidden = true; return; }
      const p = feature.properties;
      const label = p.point_count ? `${p.point_count_abbreviated} ${feature.layer.id.startsWith("air") ? "aircraft" : "vessels"}` : p.label || p.name || p.id;
      tip.innerHTML = `<b>${esc(label)}</b>${esc(p.point_count ? "Click to zoom in" : p.detail || placeName(event.lngLat.lat, event.lngLat.lng))}<br><span class="chip ${MODE_NOW ? "real" : "syn"}">${MODE_NOW ? "REAL DATA" : "SYNTHETIC"}</span>`;
      tip.style.left = `${event.originalEvent.clientX + 14}px`;
      tip.style.top = `${event.originalEvent.clientY + 14}px`;
      tip.hidden = false;
    });
  });
  map.on("mouseout", () => { $("tooltip").hidden = true; });
  map.on("click", async (event) => {
    const feature = featureAt(event.point);
    if (!feature) {
      if (MODE_NOW && state.liveEarth.mode === "live") showEarthPopup(event);
      return;
    }
    if (feature.properties.point_count) {
      const zoom = await map.getSource(feature.source).getClusterExpansionZoom(feature.properties.cluster_id);
      map.easeTo({ center: feature.geometry.coordinates, zoom: zoom + 0.3, duration: REDUCED_MOTION ? 0 : 700 });
      return;
    }
    selectTarget(targetFromFeature(feature), { fly: false });
  });
  map.on("dblclick", (event) => {
    const feature = featureAt(event.point);
    if (!feature || feature.properties.point_count) return;
    event.preventDefault();
    const target = targetFromFeature(feature);
    selectTarget(target, { fly: false }).then(() => { state.following = null; toggleFollow(target); });
  });
  map.on("zoom", updateLod);
  window.addEventListener("resize", () => map.setPadding(chromePadding()));
}

function startPulse() {
  if (REDUCED_MOTION) return;
  const period = 2600;
  const frame = (now) => {
    if (!document.hidden && map.getLayer("event-halo") && map.getLayoutProperty("event-halo", "visibility") !== "none") {
      const k = (now % period) / period;
      map.setPaintProperty("event-halo", "circle-radius", 9 + k * 24);
      map.setPaintProperty("event-halo", "circle-stroke-opacity", 0.85 * (1 - k));
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function wireChrome() {
  syncTruthChrome();
  document.querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = svgIcon(el.dataset.icon, "currentColor", 16); });
  const cameraIcons = { world: "reset", event: "pin", focus: "focus", earth: "globe" };
  document.querySelectorAll("#camera [data-camera]").forEach((b) => {
    b.innerHTML = svgIcon(cameraIcons[b.dataset.camera], "currentColor", 17);
    if (b.dataset.camera === "earth" && !MODE_NOW) { b.style.display = "none"; return; }
    if (b.dataset.camera === "earth" && !MODE_NOW) { b.style.display = "none"; return; }
    b.onclick = () => {
      if (b.dataset.camera === "world") applyPreset("world", 1800);
      else if (b.dataset.camera === "event") flyToTarget(state.selected || state.events[0]);
      else if (b.dataset.camera === "earth") toggleLiveEarth();
      else toggleFocus();
    };
  });
  document.querySelectorAll("[data-close]").forEach((b) => { b.innerHTML = svgIcon("close"); b.onclick = () => closeDialog(b.dataset.close); });
  for (const id of ["sources", "graphDialog"]) $(id).onclick = (event) => { if (event.target === $(id)) closeDialog(id); };
  $("cmd").onclick = openPalette;
  $("healthBtn").onclick = openSources;
  $("exitInvestigation").onclick = () => setInvestigation(false);
  document.addEventListener("keydown", onKey);
  wirePalette();
  wireTimeline();
}

function onKey(event) {
  const tag = document.activeElement?.tagName;
  const typing = tag === "INPUT" || tag === "TEXTAREA";
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openPalette(); return; }
  if (event.key === "Escape") {
    for (const id of ["palette", "sources", "graphDialog"]) if (!$(id).hidden) { closeDialog(id); return; }
    if (state.investigating) setInvestigation(false);
    else if (state.focus) toggleFocus(false);
    else if (state.selected) closeDrawer();
    return;
  }
  if (typing || event.ctrlKey || event.metaKey || event.altKey) return;
  const key = event.key.toLowerCase();
  if (key === "f") toggleFocus();
  else if (key === "/") { event.preventDefault(); openPalette(); }
  else if (key === " " && tag !== "BUTTON") { event.preventDefault(); togglePlay(); }
  else if (key === "[") setTick(state.tick - 1);
  else if (key === "]") setTick(state.tick + 1);
  else if (key === "r") applyPreset("world", 1800);
  else if (key === "e" && MODE_NOW) toggleLiveEarth();
  else if (key === "i" && state.selected) setInvestigation(!state.investigating);
}

function renderSkeletons() {
  $("layers").innerHTML = Array.from({ length: 7 }, () => `<div class="skeleton" style="height:44px;margin:6px"></div>`).join("");
  $("eventList").innerHTML = Array.from({ length: 5 }, () => `<div class="skeleton"></div>`).join("");
}

function showFatal(error) {
  $("fatalText").textContent = `${error.message}. The classic view uses a lighter renderer.`;
  $("fatal").hidden = false;
}

/* ------------------------------------------------------------------ boot */

function capturePlan() {
  return {
    hero: ["hero", "SYN-ALERT-01", false], world: ["world", null, false], evidence: ["port", "SYN-ALERT-01", false],
    timemachine: ["port", "SYN-ALERT-01", false], investigation: ["port", "SYN-ALERT-01", true],
    focus: ["hero", "SYN-ALERT-01", false], airport: ["airport", "SYN-AC001", false], earth: ["earth", "SYN-EQ00", false],
  }[CAPTURE] || ["hero", "SYN-ALERT-01", false];
}

async function applyCapture() {
  const [preset, eventId, investigate] = capturePlan();
  if (CAPTURE === "timemachine") state.mode = "belief";
  applyPreset(preset);
  const event = eventId && state.events.find((e) => e.id === eventId);
  if (event) await selectTarget(event, { fly: false });
  if (investigate) setInvestigation(true, { fly: false });
  renderEvents();
  renderTimeline();
  const open = QS.get("open");
  if (open === "sources") await openSources();
  if (open === "palette") { openPalette(); $("paletteInput").value = QS.get("q") || ""; renderPalette(); }
  if (open === "relations" && state.selected) openGraph(state.selected);
}

async function openingNow() {
  // Deep-link camera first (numbers only, validated ranges).
  try {
    const la = parseFloat(QS.get("lat") || ""), lo = parseFloat(QS.get("lon") || ""),
      z = parseFloat(QS.get("zoom") || "");
    if (isFinite(la) && isFinite(lo) && Math.abs(la) <= 90 && Math.abs(lo) <= 180)
      map.jumpTo({ center: [lo, la], zoom: (isFinite(z) && z >= 1 && z <= 12) ? z : 2 });
  } catch (_) { /* default globe view */ }
  map.on("moveend", () => {
    try {
      const c = map.getCenter();
      const q = new URLSearchParams(location.search);
      q.set("mode", "now");
      q.set("lat", c.lat.toFixed(2)); q.set("lon", c.lng.toFixed(2));
      q.set("zoom", String(Math.round(map.getZoom() * 10) / 10));
      history.replaceState(null, "", `${location.pathname}?${q.toString()}`);
    } catch (_) { /* share URL is best-effort */ }
  });
  // Deep-linked dialogs open after the selection settles, on every path.
  const finish = async () => { if (QS.get("open") === "sources") await openSources(); };
  const region = QS.get("region") || "";
  if (region) { await openNowRegion(region); await finish(); return; }
  const hex = (QS.get("aircraft") || "").toLowerCase();
  if (/^[0-9a-f]{6}$/.test(hex) && findNowObject("AIR:" + hex)) {
    selectNowTarget("AIR:" + hex);
    await finish();
    return;
  }
  const evKey = (QS.get("event") || "").slice(0, 200);
  if (evKey && findNowObject(evKey)) {
    const ev = state.events.find((e) => e.id === evKey);
    if (ev) { selectTarget(ev); await finish(); return; }
  }
  // Change deep links resolve from the cached change feed (?event=chg:…).
  if (evKey && evKey.startsWith("chg:")) {
    const ev = state.events.find((e) => e.id === evKey);
    if (ev) { selectTarget(ev); await finish(); return; }
  }
  // Default: the highest-ranked Important item that is actually recent, so the
  // first screen shows the world now rather than last week's biggest event.
  const recent = (state.importantV2?.items || [])
    .filter((i) => Number.isFinite(i.freshness_age_h) && i.freshness_age_h <= 24)
    .map((i) => state.events.find((e) => e.id === i.key))
    .find((e) => e && e.lat != null && e.lon != null); // must be framable on the globe
  const located = (e) => e.lat != null && e.lon != null;
  const first = recent || state.events.find((e) => e.severity === "ALERT" && located(e))
    || state.events.find(located) || state.events[0];
  if (first) await selectTarget(first, { fly: false });
  await finish();
}

async function opening() {
  if (CAPTURE) { await applyCapture(); return; }
  setTimeout(() => document.body.classList.remove("booting"), REDUCED_MOTION ? 0 : 1100);
  if (MODE_NOW) { await openingNow(); return; }
  if (!REDUCED_MOTION) map.easeTo({ bearing: 0, zoom: CAMERA_PRESETS.world.zoom, duration: 1300, easing: (t) => 1 - (1 - t) ** 3 });
  const story = STORIES[STORY];
  if (!story) return;
  await wait(REDUCED_MOTION ? 0 : 1100);
  applyPreset("hero", 1500);
  await wait(REDUCED_MOTION ? 0 : 1900);
  const event = state.events.find((e) => e.id === story.event) || state.events[0];
  await selectTarget(event, { preset: story.preset });
}

function idle() {
  // The world pulse animates continuously, so outside capture mode MapLibre may
  // never emit "idle" and the ready flag would never be set. Resolve on
  // whichever comes first: the idle event, or a short deadline.
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => { if (!settled) { settled = true; resolve(); } };
    map.once("idle", finish);
    setTimeout(finish, 3000);
    if (map.loaded() && !map.isMoving()) finish();
  });
}

async function runBench() {
  const frames = [];
  let last = performance.now();
  const end = last + 6000;
  await new Promise((resolve) => {
    const frame = (now) => {
      frames.push(now - last);
      last = now;
      map.setBearing((map.getBearing() + 0.35) % 360);
      if (now < end) requestAnimationFrame(frame); else resolve();
    };
    requestAnimationFrame(frame);
  });
  const sorted = frames.slice(10).sort((a, b) => a - b);
  const avg = sorted.reduce((s, v) => s + v, 0) / sorted.length;
  const gl = map.getCanvas().getContext("webgl2");
  const info = gl?.getExtension("WEBGL_debug_renderer_info");
  window.__tellurionBench = {
    fps_avg: Math.round(10000 / avg) / 10, fps_p5: Math.round(10000 / sorted[Math.floor(sorted.length * 0.95)]) / 10,
    frames: sorted.length, objects: buildData().air.features.length + buildData().sea.features.length,
    renderer: info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : "hidden", scene: SCENE || "default",
  };
  document.documentElement.dataset.bench = "done";
}

/* ================================================== WORLD NOW (live) ==
   Additive live-data mode: ?mode=now (order-independent, combinable
   with ?view= / ?sky= / ?aircraft= / ?event= / ?region= / camera).
   Same-origin public APIs only (the offline test bans remote URLs,
   which this never emits). Replay behavior is untouched: every bridge
   below is gated on MODE_NOW, and renderDrawer stays replay-only
   (live objects use renderNowDrawer). No synthetic object ever
   renders in this mode; uncovered domains say so explicitly.
   (MODE_NOW/NOW_VIEW/NOW_SKY are declared near the top QS consts.) */
const TILE_GEO_NOW = { "eu-central": [50, 10], "us-northeast": [40, -75],
  "us-southwest": [35, -115], "se-asia": [15, 102], "east-asia": [35, 138],
  "south-asia": [22, 79], "mideast": [25, 50], "south-america": [-23, -46],
  "oceania": [-33.9, 151.2] };
const COVERAGE_GAPS_NOW = [
  ["West and Central Africa", 6, 8, "NO RECEIVER COVERAGE — probed empty, not polled"],
  ["Central Asia", 42, 64, "NO RECEIVER COVERAGE — probed empty, not polled"],
  ["North Atlantic", 45, -35, "NOT POLLED — ocean, sparse receivers"],
  ["Pacific", 0, -150, "NOT POLLED — ocean, sparse receivers"],
  ["Arctic and polar", 80, 0, "NOT POLLED — no tile"],
  ["Southern Ocean", -55, 90, "NOT POLLED — no tile"]];

async function loadNowData() {
  if (!MODE_NOW) return false;
  const [now, air] = await Promise.all([
    getJSON("/api/world/now?norefresh=0"),
    getJSON("/api/world/now/aviation?light=1").catch(() => null),
  ]);
  state.now = now;
  state.airNow = air && air.counts ? air : null;
  try {
    state.importantV2 = await getJSON("/api/world/now/important-v2");
  } catch (_) { state.importantV2 = null; }
  try {
    const chg = await getJSON("/api/world/changes?norefresh=1");
    state.changes = chg.changes || [];
    state.changeById = Object.fromEntries(
      state.changes.map((c) => [c.id, c]));
  } catch (_) { state.changes = []; state.changeById = {}; }
  return true;
}

function nowTitle(o) {
  const f = o.fields || {};
  if (o.source === "usgs-earthquakes") return `M${f.mag ?? "?"} — ${f.place || "earthquake"}`;
  if (o.source === "nws-alerts") return f.title || f.headline || o.stable_key;
  if (o.source === "gdelt-doc") return (f.title || "reported event") + (f.domain ? ` — ${f.domain}` : "");
  return f.title || o.stable_key;
}

function nowSeverity(o) {
  const f = o.fields || {};
  if (o.source === "usgs-earthquakes") return (f.mag ?? 0) >= 6 ? "ALERT" : (f.mag ?? 0) >= 5 ? "WATCH" : "INFO";
  if (o.source === "gdacs-alerts") return /red/i.test(f.alert_level || "") ? "ALERT" : (/orange/i.test(f.alert_level || "") ? "WATCH" : "INFO");
  if (o.source === "nws-alerts") return /extreme/i.test(f.severity || "") ? "ALERT" : (/severe/i.test(f.severity || "") ? "WATCH" : "INFO");
  if (o.source === "noaa-swpc") return /warning/i.test(f.title || "") ? "WATCH" : "INFO";
  return "INFO";
}

function nowCategory(o) {
  if (o.source === "usgs-earthquakes") return "EARTH";
  if (o.source === "gdacs-alerts" || o.source === "nasa-eonet") return "EARTH";
  if (o.source === "nws-alerts") return "WEATHER";
  if (o.source === "noaa-swpc") return "SPACE";
  return "INTELLIGENCE";
}

function nowEvents() {
  // Real objects mapped into the app's event shape (feed + drawer).
  // Objects without coordinates join the feed only — never faked pins.
  const out = [];
  const objs = state.now?.objects || {};
  for (const [sid, items] of Object.entries(objs)) {
    for (const o of items || []) {
      if (sid === "gdacs-alerts") {
        const al = String((o.fields || {}).alert_level || "").toLowerCase();
        if (al !== "red" && al !== "orange") continue;
      }
      if (sid === "nws-alerts") {
        const sv = String((o.fields || {}).severity || "").toLowerCase();
        if (sv !== "extreme" && sv !== "severe") continue;
      }
      out.push({ id: o.stable_key, title: nowTitle(o), kind: "event",
        severity: nowSeverity(o), category: nowCategory(o),
        lat: o.lat, lon: o.lon, t: o.source_event_time || "UNKNOWN",
        minute: MAX_TICK, sources: o.corroboration === "CORROBORATED" ? 2 : 1,
        hero: null, now: true, nowRef: o });
    }
  }
  for (const f of state.airNow?.important || []) {
    out.push({ id: "AIR:" + f.icao24, title: `${f.callsign} · ${((f.flags || [])[0] || {}).label || "flagged"}`,
      kind: "aircraft", severity: f.interest === "HIGH" ? "ALERT" : "WATCH", category: "AIR",
      lat: f.lat, lon: f.lon, t: "live", minute: MAX_TICK, sources: 1,
      hero: null, now: true, nowRef: f });
  }
  // First-class change objects: pins render through the shared events
  // source (no minzoom), feed-only when coordinates are absent.
  for (const c of state.changes || []) {
    out.push({ id: c.id, title: c.title, kind: "change",
      severity: SEVERITY[c.severity] ? c.severity : "INFO", category: "CHANGE",
      lat: c.location?.lat ?? null, lon: c.location?.lon ?? null,
      t: c.first_observed || "UNKNOWN", minute: MAX_TICK,
      sources: c.source_count || 1, hero: null, now: true, changeRef: c });
  }
  return out;
}

function nowAircraftPoints() {
  // The boot request is ?light=1, which carries compact `positions` instead of
  // full `states`; without this every counted aircraft stayed undrawn.
  const states = state.airNow?.states || state.airNow?.positions || [];
  const list = Array.isArray(states) ? states : [];
  const seen = new Set();
  const pts = [];
  const push = (o, important) => {
    if (o.lat == null || seen.has(o.icao24)) return;
    seen.add(o.icao24);
    pts.push(pt(o.lat, o.lon, { id: "AIR:" + o.icao24, kind: "aircraft",
      label: o.callsign && o.callsign !== "UNKNOWN" ? o.callsign : o.icao24,
      heading: o.track_deg ?? 0,
      detail: `${o.type !== "UNKNOWN" ? o.type + " · " : ""}${o.baro_alt_ft != null ? Math.round(o.baro_alt_ft) + " ft · " : ""}${o.gs_kt != null ? Math.round(o.gs_kt) + " kt" : ""}REAL DATA`.trim() }));
  };
  // Full snapshot may be capped server-side; important flags render first.
  const imp = new Set((state.airNow?.important || []).map((f) => f.icao24));
  for (const o of list) if (imp.has(o.icao24)) push(o, true);
  for (const o of list) push(o, false);
  return pts.slice(0, 5000);
}

function nowCoverageFeatures() {
  const feats = [];
  for (const t of state.airNow?.coverage || []) {
    if (t.tile === "oceans/africa/polar" || !TILE_GEO_NOW[t.tile]) continue;
    const [lat, lon] = TILE_GEO_NOW[t.tile];
    const ok = t.state === "ONLINE" && (t.aircraft || 0) > 0;
    const limited = t.state === "RATE_LIMITED";
    feats.push(polyLL(closeRing(circleRing(lat, lon, 460).map(([lo, la]) => [la, lo])),
      { id: "COV-" + t.tile, kind: "coverage",
        label: `ADS-B ${t.tile}: ${t.state}${ok ? ` — ${t.aircraft} aircraft` : ""}`,
        state: limited ? "RATE LIMITED" : (ok ? "GOOD" : "PARTIAL") }));
  }
  for (const [name, lat, lon, msg] of COVERAGE_GAPS_NOW) {
    feats.push(polyLL(closeRing(circleRing(lat, lon, 1500).map(([lo, la]) => [la, lo])),
      { id: "COV-GAP-" + name, kind: "coverage", label: `${name}: ${msg}`, state: "NO SOURCE" }));
  }
  return feats;
}

function selectNowTarget(id) {
  if (!id) return;
  const ev = state.events.find((e) => e.id === id);
  if (ev) { selectTarget(ev); return; }
  const found = findNowObject(id);
  if (found) selectTarget({ id, kind: found.kind === "aircraft" ? "aircraft" : "event",
    title: id, severity: "INFO", category: found.kind === "aircraft" ? "AIR" : "INTELLIGENCE",
    lat: found.lat, lon: found.lon, t: "live", minute: MAX_TICK, sources: 1, hero: null, now: true });
}

function findNowObject(id) {
  if (!id) return null;
  if (id.startsWith("AIR:")) {
    const hex = id.slice(4).toLowerCase();
    // Light boot payloads carry `positions`, not `states`; without this only
    // flagged aircraft could be deep-linked, searched or clicked.
    const o = (state.airNow?.states || state.airNow?.positions || []).find((x) => x.icao24 === hex)
      || (state.airNow?.important || []).find((x) => x.icao24 === hex);
    if (o && o.lat != null) return { kind: "aircraft", obj: o, lat: o.lat, lon: o.lon };
    const fl = (state.airNow?.flagged || []).find((x) => x.icao24 === hex);
    if (fl && fl.lat != null) return { kind: "aircraft", obj: fl, lat: fl.lat, lon: fl.lon };
    return null;
  }
  for (const items of Object.values(state.now?.objects || {})) {
    const o = (items || []).find((x) => x.stable_key === id || x.id === id);
    if (o) return { kind: "event", obj: o, lat: o.lat, lon: o.lon };
  }
  return null;
}

async function nowEvidence(id) {
  if (id.startsWith("chg:")) {
    const c = state.changeById?.[id];
    return c ? { kind: "change", change: c } : null;
  }
  if (id.startsWith("AIR:")) {
    const hex = id.slice(4);
    const r = await getJSON(`/api/world/now/trail?hex=${encodeURIComponent(hex)}`);
    if (!r.aircraft) return null;
    return { kind: "aircraft", aircraft: r.aircraft, flags: r.flags, trail: r.trail || [] };
  }
  const r = await getJSON(`/api/world/now/evidence?key=${encodeURIComponent(id)}`);
  return r.evidence ? { kind: "event", evidence: r.evidence, related: r.related || [] } : null;
}

function nowDrawer(target, data) {
  const drawer = $("drawer");
  if (data.kind === "aircraft") {
    const a = data.aircraft, fl = data.flags;
    const flags = ((fl && fl.flags) || []).map((x) => `<div class="rel flag"><b>${esc(x.label)}</b> <span class="muted">${esc(x.level)}</span><br><small class="muted">WHY: ${esc(x.why)}</small><br><code class="mono">${esc(JSON.stringify(x.evidence))}</code></div>`).join("")
      || "<p>No flags — routine public flight state.</p>";
    drawer.innerHTML = `
      <div class="drawer-top">
        <div class="drawer-nav">
          <button class="btn ghost" type="button" id="backToEvents">${svgIcon("back")} Events</button>
          <span class="chip real">REAL DATA</span>
          <button class="icon-btn close" type="button" id="closeDrawer" aria-label="Close evidence">${svgIcon("close")}</button>
        </div>
        <span class="sev" style="--sev:${fl && fl.interest === "HIGH" ? SEVERITY.ALERT.color : SEVERITY.WATCH.color}">${esc(fl ? fl.interest : "LOW")}</span>
        <h2 id="drawerTitle">${esc(a.callsign && a.callsign !== "UNKNOWN" ? a.callsign : a.icao24)}${a.type !== "UNKNOWN" ? ` · ${esc(a.type)}` : ""}</h2>
        <div class="facts">
          <div class="fact"><span class="k">Hex</span><span class="v mono">${esc(a.icao24)}</span></div>
          <div class="fact"><span class="k">Altitude</span><span class="v mono">${a.baro_alt_ft != null ? `${Math.round(a.baro_alt_ft)} ft baro` : "—"}${a.on_ground ? " · ON GROUND" : ""}</span></div>
          <div class="fact"><span class="k">Speed</span><span class="v mono">${a.gs_kt != null ? `${Math.round(a.gs_kt)} kt` : "—"}</span></div>
          <div class="fact"><span class="k">Heading</span><span class="v mono">${a.track_deg != null ? `${Math.round(a.track_deg)}°` : "—"}</span></div>
          <div class="fact"><span class="k">Vertical rate</span><span class="v mono">${a.vrate_fpm != null ? `${Math.round(a.vrate_fpm)} fpm` : "—"}</span></div>
          <div class="fact"><span class="k">Squawk</span><span class="v mono">${esc(a.squawk)}</span></div>
          <div class="fact"><span class="k">Last seen</span><span class="v mono">position age ${a.position_age_s != null ? `${Math.round(a.position_age_s)} s` : "UNKNOWN"}</span></div>
          <div class="fact"><span class="k">Source</span><span class="v mono">${esc(a.source)} · tile ${esc((a.tiles || []).join(","))}</span></div>
        </div>
        <div class="actions">
          <button class="btn" type="button" id="flyBtn">${svgIcon("pin")} Fly to</button>
          <button class="btn" type="button" id="followBtn" aria-pressed="${state.following === target.id}">${svgIcon("follow")} Follow</button>
          <button class="btn" type="button" id="trailBtn">Play recorded track</button>
        </div>
      </div>
      <div class="drawer-body" id="drawerBody">
        <section class="dsec"><h3>Why flagged?</h3>${flags}<p class="note">Interest: ${esc((fl && fl.interest) || "LOW")} · rules are public and human-readable; POSSIBLE means possible.</p></section>
        <section class="dsec"><h3>Trail (RECORDED, memory only)</h3><div id="trailBox"><p class="muted">${data.trail.length} recorded points · never stored on disk.</p></div></section>
        <section class="dsec"><h3>Provenance and rights</h3><dl class="kv">
          <dt>Source</dt><dd>${esc(a.source)} · ${esc(a.attribution || "")}</dd>
          <dt>Rights</dt><dd>${esc(a.rights || "")}</dd>
          <dt>Truth</dt><dd>DELAYED seconds (source-specific, never global LIVE)</dd>
        </dl></section>
      </div>`;
    wireNowDrawer(target, data);
    return;
  }
  if (data.kind === "change") {
    const c = data.change;
    const sev = SEVERITY[c.severity] || SEVERITY.INFO;
    const keys = [...new Set([...Object.keys(c.before || {}), ...Object.keys(c.after || {})])];
    const delta = keys.map((k) => {
      const b = (c.before || {})[k], a = (c.after || {})[k];
      const fmtV = (v) => v == null ? "—" : (typeof v === "object" ? JSON.stringify(v) : String(v));
      return `<div class="rel"><b>${esc(k)}</b><span class="muted">was</span><span>${esc(fmtV(b))} → <b>${esc(fmtV(a))}</b></span></div>`;
    }).join("") || "<p class='muted'>No before/after stated.</p>";
    const why = (c.why_flagged || []).map((w) => `<div class="rel flag"><b>${esc(w)}</b></div>`).join("")
      || "<p class='muted'>No reason recorded.</p>";
    const evd = (c.evidence || []).map((e) => `<div class="rel"><b>${esc(e.title || e.stable_key)}</b><span class="muted">${esc(e.source)}</span><br><small class="muted">${esc(e.source_event_time || "UNKNOWN")} · ${esc(e.observation_type || "")} · ${esc(e.truth_mode || "")}</small></div>`).join("")
      || "<p class='muted'>No evidence rows.</p>";
    const fr = c.freshness || {};
    drawer.innerHTML = `
      <div class="drawer-top">
        <div class="drawer-nav">
          <button class="btn ghost" type="button" id="backToEvents">${svgIcon("back")} Events</button>
          <span class="chip real">REAL DATA</span>
          <span class="chip">CHANGE DETECTED</span>
          <button class="icon-btn close" type="button" id="closeDrawer" aria-label="Close evidence">${svgIcon("close")}</button>
        </div>
        <span class="sev" style="--sev:${sev.color}">${sev.label}</span>
        <h2 id="drawerTitle">${esc(c.title)}</h2>
        <div class="facts">
          <div class="fact"><span class="k">What changed</span><span class="v">${esc(c.type)}</span></div>
          <div class="fact"><span class="k">Where</span><span class="v mono">${c.location?.lat != null && c.location?.lon != null ? formatLatLon(c.location.lat, c.location.lon) : "No coordinates (list only, no map pin)"}</span></div>
          <div class="fact"><span class="k">First observed</span><span class="v mono" title="${esc(c.first_observed ?? "UNKNOWN")}">${esc(utcLabel(c.first_observed))}</span></div>
          <div class="fact"><span class="k">Last observed</span><span class="v mono" title="${esc(c.last_observed ?? "UNKNOWN")}">${esc(utcLabel(c.last_observed))}</span></div>
          <div class="fact"><span class="k">Sources</span><span class="v">${esc(String(c.source_count ?? 1))} · ${esc(c.corroboration || "ONE SOURCE")}</span></div>
          <div class="fact"><span class="k">Confidence</span><span class="v">${esc(c.confidence || "MODERATE")} (${esc(c.observation_type || "OBSERVED")})</span></div>
          <div class="fact"><span class="k">Area</span><span class="v">${c.magnitude?.area_m2 != null ? esc(String(c.magnitude.area_m2)) + " m²" : "Not stated (never estimated)"}</span></div>
          <div class="fact"><span class="k">Freshness</span><span class="v">${esc(fr.age_class || "unknown")}${fr.age_hours != null ? ` · ${fr.age_hours} h` : ""}</span></div>
        </div>
        <div class="actions">
          <button class="btn" type="button" id="flyBtn">${svgIcon("pin")} Fly to</button>
        </div>
      </div>
      <div class="drawer-body" id="drawerBody">
        <section class="dsec"><h3>Satellite evidence</h3><div id="satEvidence"><p class="muted">Loading Sentinel-2 evidence\u2026</p></div></section>
        <section class="dsec"><h3>Before / after</h3>${delta}<p class="note">Only source-stated values. Area is shown only when a source states it.</p></section>
        <section class="dsec"><h3>Why flagged?</h3>${why}<p class="note">Public-interest ranking: ${esc(c.rank?.label || "")} (${esc(String(c.rank?.score ?? ""))}) · severity, freshness, corroboration, rarity, scope. Worth investigating — never financial advice.</p></section>
        <section class="dsec"><h3>Evidence (${esc(String((c.evidence || []).length))})</h3>${evd}</section>
        <section class="dsec"><h3>Provenance and rights</h3><dl class="kv">
          ${((c.rights || {}).sources || []).map((r) => `<dt>${esc(r.source)}</dt><dd>${esc(r.rights)} · ${esc(r.attribution)}</dd>`).join("")}
        </dl><p class="note">${esc((c.rights || {}).note || "")}</p></section>
      </div>`;
    wireNowDrawer(target, data);
    loadSatEvidence(target.id);
    return;
  }
  const ev = data.evidence, f = ev.fields || {};
  const rel = (data.related || []).map((l) => `<div class="rel"><b>${esc(l.relation)}</b> — ${esc(l.independence)}<br><small class="muted">method: ${esc(l.method)} · ${esc(l.independence_note || "")}</small></div>`).join("")
    || "<p class='muted'>ONE SOURCE — no links met the criteria.</p>";
  drawer.innerHTML = `
    <div class="drawer-top">
      <div class="drawer-nav">
        <button class="btn ghost" type="button" id="backToEvents">${svgIcon("back")} Events</button>
        <span class="chip real">REAL DATA</span>
        <button class="icon-btn close" type="button" id="closeDrawer" aria-label="Close evidence">${svgIcon("close")}</button>
      </div>
      <span class="chip">${svgIcon("signal", "currentColor", 12)} ${esc(ev.truth_mode || "DELAYED")}</span>
      <span class="chip">${esc(ev.observation_type || "")}</span>
      <h2 id="drawerTitle">${esc(nowTitle(ev))}</h2>
      <div class="facts">
        <div class="fact"><span class="k">What</span><span class="v">${esc(nowTitle(ev))}</span></div>
        <div class="fact"><span class="k">Where</span><span class="v mono">${ev.lat != null && ev.lon != null ? formatLatLon(ev.lat, ev.lon) : "No coordinates (list only, no map pin)"}</span></div>
        <div class="fact"><span class="k">Source time</span><span class="v mono" title="${esc(ev.source_event_time ?? "UNKNOWN")}">${esc(utcLabel(ev.source_event_time))}</span></div>
        <div class="fact"><span class="k">Published</span><span class="v mono" title="${esc(ev.published_time ?? "UNKNOWN")}">${esc(utcLabel(ev.published_time))}</span></div>
        <div class="fact"><span class="k">First seen</span><span class="v mono" title="${esc(ev.first_seen ?? "UNKNOWN")}">${esc(utcLabel(ev.first_seen))}</span></div>
        <div class="fact"><span class="k">Ingested</span><span class="v mono" title="${esc(ev.ingested_at ?? "UNKNOWN")}">${esc(utcLabel(ev.ingested_at))}</span></div>
        <div class="fact"><span class="k">Freshness</span><span class="v">${esc(ageLabel(ev.source_event_time))}</span></div>
      </div>
      <div class="actions">
        <button class="btn" type="button" id="flyBtn">${svgIcon("pin")} Fly to</button>
      </div>
    </div>
    <div class="drawer-body" id="drawerBody">
      ${importantWhy(target?.id)}
      <section class="dsec"><h3>Source</h3><div class="mono">${esc(ev.source)} ·${esc(ev.attribution || ev.provenance || "")}</div>${ev.source_url && ev.source_url !== "UNKNOWN" ? `<div style="margin-top:6px"><a href="${esc(ev.source_url)}" target="_blank" rel="noopener">open raw source</a></div>` : ""}<div class="note">event time is not ingest time; UNKNOWN stays UNKNOWN</div></section>
      <section class="dsec"><h3>Related public signals</h3>${rel}</section>
      <section class="dsec"><h3>Rights</h3><div>${esc(ev.rights || "")}</div><div class="note">${esc(ev.attribution || "")}</div></section>
    </div>`;
  wireNowDrawer(target, data);
}

function satSideHTML(side) {
  if (!side || !side.thumbnail) return "";
  const t = side.thumbnail;
  const res = side.resolution_m != null
    ? `~${Math.round(side.resolution_m)} m/px preview \u00b7 ${side.native_resolution_m ?? 10} m source`
    : "resolution not stated";
  return `<figure class="satfig">
    <figcaption><b>${esc(side.role)}</b> \u2014 ${esc(side.product_id || "")}</figcaption>
    <img src="/api/world/imagery/thumb/${esc(t.ref)}.jpg" alt="${esc(side.role)} Sentinel-2 view" loading="lazy">
    <dl class="kv">
      <dt>Captured</dt><dd class="mono" title="${esc(side.captured_at ?? "UNKNOWN")}">${esc(utcLabel(side.captured_at))} \u00b7 ${esc(ageLabel(side.captured_at))}</dd>
      <dt>Cloud</dt><dd>${side.cloud_cover_pct != null ? `${side.cloud_cover_pct}% \u00b7 ${esc(side.cloud_state || "")}` : esc(side.cloud_state || "UNKNOWN")}</dd>
      <dt>Resolution</dt><dd>${esc(res)}</dd>
      <dt>Freshness</dt><dd>${esc(side.cloud_state === "CLOUD_LIMITED" ? "usable with caution" : (side.cloud_state || "").toLowerCase() || "unknown")}</dd>
      <dt>Rights</dt><dd>${esc((side.rights || {}).attribution || "")}</dd>
    </dl>
    ${side.source_url ? `<div><a href="${esc(side.source_url)}" target="_blank" rel="noopener">OPEN SOURCE</a> <span class="muted">catalog record, not a portal screenshot</span></div>` : ""}
  </figure>`;
}

function satEvidenceHTML(p) {
  const status = p.status || "NO_SUITABLE_OBSERVATION";
  if (status === "NOT_ELIGIBLE") {
    return `<p class="muted">No satellite evidence for this kind of change. ${esc(p.note || "")}</p>`;
  }
  if (status === "SOURCE_UNAVAILABLE" || status === "RATE_LIMITED") {
    return `<p class="muted">Satellite catalog unreachable (${esc(status)}). ${esc(p.note || "The change itself is unaffected.")}</p>`;
  }
  if (status === "NO_SUITABLE_OBSERVATION" || (!p.before && !p.after)) {
    return `<p class="muted">No suitable Sentinel-2 observation in the search windows. ${esc(p.note || "")}</p>`;
  }
  const limited = ((p.before || {}).cloud_state === "CLOUD_LIMITED") || ((p.after || {}).cloud_state === "CLOUD_LIMITED");
  return `${limited ? `<div class="blindcard"><b>Limited view</b>Satellite evidence limited by cloud cover. Do not infer hidden surface changes.</div>` : ""}
    <div class="satpair">${satSideHTML(p.before)}${satSideHTML(p.after)}</div>
    ${!p.before || !p.after ? `<p class="muted">${esc(!p.before ? "No clear BEFORE scene." : "No clear AFTER scene yet.")} ${esc(p.note || "")}</p>` : ""}
    <p class="note">Same Sentinel-2 tile where possible \u2014 directly comparable. Imagery is evidence, not a conclusion.</p>`;
}

async function loadSatEvidence(changeId) {
  const box = $("satEvidence");
  if (!box) return;
  try {
    const p = await getJSON(`/api/world/changes/${encodeURIComponent(changeId)}/imagery`);
    if (!document.body.contains(box)) return;
    if (state.selected?.id !== changeId) return;
    box.innerHTML = satEvidenceHTML(p);
  } catch (error) {
    if (document.body.contains(box)) {
      box.innerHTML = `<p class="muted">Satellite evidence unavailable (${esc(error.message)}).</p>`;
    }
  }
}

function wireNowDrawer(target, data) {  $("backToEvents").onclick = () => closeDrawer({ keepSelection: true });
  $("closeDrawer").onclick = () => closeDrawer();
  $("flyBtn").onclick = () => flyToTarget(target);
  if ($("followBtn")) $("followBtn").onclick = () => toggleFollow(target);
  const trailBtn = $("trailBtn");
  if (trailBtn) trailBtn.onclick = () => replayNowTrail(data);
  writeDeepLink();
}

let nowTrailAnim = null;
function replayNowTrail(data) {
  if (nowTrailAnim) { clearInterval(nowTrailAnim); nowTrailAnim = null; }
  const pts = (data.trail || []).filter((p) => p.lat != null);
  const box = $("trailBox");
  if (!box || pts.length < 2) { if (box) box.innerHTML = "<p class='muted'>Trail too short to replay.</p>"; return; }
  map.getSource("nowtrail")?.setData(fc([lineLL(pts.map((p) => [p.lat, p.lon]), { id: "nowtrail" })]));
  let i = 0;
  box.innerHTML = `<p class="muted">Playing back recorded real positions (memory only) — not live. <span id="trailPos"></span></p>
    <input id="trailScrub" type="range" min="0" max="${pts.length - 1}" value="0" style="width:100%" aria-label="Scrub recorded trail">`;
  const show = () => {
    const p = pts[i];
    map.getSource("nowsel")?.setData(fc([pt(p.lat, p.lon, { id: "nowtrail-pos" })]));
    const ms = Date.parse(String(p.t ?? ""));
    const clock = Number.isFinite(ms) ? `${new Date(ms).toISOString().slice(11, 19)} UTC` : "UNKNOWN";
    $("trailPos").textContent = `${i + 1}/${pts.length} · ${clock} · ${p.baro_alt_ft != null ? Math.round(p.baro_alt_ft) + " ft" : "—"}`;
    $("trailScrub").value = String(i);
  };
  $("trailScrub").oninput = (e) => { i = Number(e.target.value); show(); };
  show();
  nowTrailAnim = setInterval(() => { i = (i + 1) % pts.length; if (document.body.contains($("trailScrub"))) show(); else { clearInterval(nowTrailAnim); nowTrailAnim = null; } }, 900);
}

function writeDeepLink() {
  try {
    const q = new URLSearchParams(location.search);
    q.set("mode", "now");
    if (state.selected) {
      if (state.selected.id.startsWith("AIR:")) { q.set("aircraft", state.selected.id.slice(4)); q.delete("event"); }
      else { q.set("event", state.selected.id); q.delete("aircraft"); }
    }
    const c = map.getCenter();
    q.set("lat", c.lat.toFixed(2)); q.set("lon", c.lng.toFixed(2)); q.set("zoom", String(Math.round(map.getZoom() * 10) / 10));
    history.replaceState(null, "", `${location.pathname}?${q.toString()}`);
  } catch (_) { /* share URL is best-effort */ }
}

async function openNowRegion(name) {
  try {
    const r = await getJSON(`/api/world/now/region?region=${encodeURIComponent(name)}`);
    if (r.center) map.flyTo({ center: [r.center.lon, r.center.lat], zoom: 5, essential: true, duration: REDUCED_MOTION ? 0 : 1500 });
    const rows = Object.entries(r.real || {}).map(([k, v]) => `<div class="fact"><span class="k">${esc(k)}</span><span class="v mono">${esc(String(v))}</span></div>`).join("");
    $("drawer").innerHTML = `<div class="drawer-top"><div class="drawer-nav">
      <button class="btn ghost" type="button" id="backToEvents">${svgIcon("back")} Events</button>
      <span class="chip real">REAL DATA</span>
      <button class="icon-btn close" type="button" id="closeDrawer" aria-label="Close">${svgIcon("close")}</button></div>
      <h2 id="drawerTitle">Region — ${esc(r.region)} (real)</h2>${rows}
      <div class="fact"><span class="k">Aircraft within ${esc(String(Math.round(r.movement?.radius_km ?? 0)))} km</span><span class="v mono">${esc(String(r.movement?.aircraft_tracked ?? "?"))}</span></div>
      <div class="fact"><span class="k">Vessels / satellites</span><span class="v mono">no live source</span></div>
      <div class="note">STATIC reference geography · missing domains listed, never synthetic fill.</div>
      ${(r.no_coverage || []).map((x) => `<div class="blindcard">${esc(x)}</div>`).join("")}
      ${(r.blind_spots || []).map((b) => `<div class="blindcard">${esc(b.region || "")}: <b>${esc(b.status || "")}</b> — ${esc(b.reason || "")}</div>`).join("")}
      </div><div class="drawer-body"></div>`;
    $("events").hidden = true;
    $("drawer").hidden = false;
    $("backToEvents").onclick = () => closeDrawer({ keepSelection: true });
    $("closeDrawer").onclick = () => closeDrawer();
  } catch (_) { /* region overlay is best-effort */ }
}

async function main() {
  if (CAPTURE) document.body.classList.add("capture");
  if (state.focus) document.body.classList.add("focus");
  renderSkeletons();
  wireChrome();
  let land, countries, payload;
  try {
    [land, countries, payload] = await Promise.all([
      getJSON("/console/data/land-50m.json"), getJSON("/console/data/countries-50m.json"), loadTick(state.tick)]);
  } catch (error) {
    showFatal(error);
    return;
  }
  [state.ultra, state.world] = payload;
  if (MODE_NOW) {
    state.mode = "current";
    try {
      await loadNowData();
    } catch (error) {
      state.nowError = error;
    }
    if (!state.now) {
      showFatal(new Error(`WORLD NOW unavailable (${state.nowError?.message || "offline"}) — remove ?mode=now for DEMO REPLAY`));
      return;
    }
    // Backend truth is authoritative for *metadata*; the URL-derived
    // state.worldMode stays the single UI mode owner.
    state.truth = { mode: state.now.mode ?? "now",
      real_data: state.now.real_data ?? true,
      truth_label: state.now.truth_label ?? "WORLD NOW (real public feeds)" };
    syncTruthChrome();
    // Coverage explains quiet regions at global zoom, so it defaults ON in
    // WORLD NOW (replay keeps blind-spots OFF by default).
    state.visible.blind = true;
    const blindRow = NAV.flatMap((s) => s.rows).find((r) => r.key === "blind");
    if (blindRow) {
      blindRow.label = "Coverage";
      blindRow.sub = "Seen well · partial · not at all (live legs)";
      blindRow.layers = ["coverage-fill", "coverage-line"];
      blindRow.count = () => (buildNowData().coverage?.features || []).length;
    }
  }
  state.events = buildEvents();
  if (MODE_NOW && state.now) {
    // NOW feed is real-only: replay story events must not appear,
    // auto-select, or leak into IDs — they stay available in
    // DEMO REPLAY (no ?mode=now).
    state.events = state.events.filter((e) => e.now);
  }
  const quake = state.ultra.seismic[0];
  if (quake) CAMERA_PRESETS.earth.center = [quake.lon, quake.lat];
  await document.fonts.load("600 12px Inter").catch(() => {});
  const start = CAPTURE ? capturePlan()[0] : "world";
  try {
    map = new maplibregl.Map({
      container: "map", style: { version: 8, projection: { type: "globe" }, sources: {},
        layers: [{ id: "background", type: "background", paint: { "background-color": "#081b2e" } }] },
      ...CAMERA_PRESETS[start], bearing: CAPTURE ? CAMERA_PRESETS[start].bearing : -38,
      zoom: CAPTURE ? CAMERA_PRESETS[start].zoom : CAMERA_PRESETS.world.zoom - 0.35,
      attributionControl: false, maxPitch: 70, fadeDuration: REDUCED_MOTION ? 0 : 200,
    });
  } catch (error) {
    location.replace(`/ultra/classic${location.search}`);
    return;
  }
  map.on("error", (event) => {
    // Provider-hosted live-earth tiles fail independently of the app:
    // they degrade to the vector basemap, never to the fatal dialog.
    // liveearth is the app's only raster source: any tile error while
    // LIVE EARTH is active is an imagery delivery failure, matched
    // without embedding any provider hostname (offline UI contract).
    if ((event && event.sourceId === "liveearth") ||
        (event && event.tile && state.liveEarth.mode === "live")) {
      noteEarthTileError();
      return;
    }
    if (!map.loaded()) showFatal(event.error || new Error("renderer error"));
  });
  map.on("load", async () => {
    try { map.setProjection?.({ type: "globe" }); } catch (_) { /* style projection already applied */ }
    try { map.setSky?.({ "sky-color": "#0a1726", "horizon-color": "#15304c", "fog-color": "#0a1726", "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 0.55, 5, 0.25, 8, 0] }); } catch (_) { /* optional */ }
    registerImages();
    addBaseLayers(topoFeatures(land, "land"), topoFeatures(countries, "countries"));
    addDataLayers(buildData());
    if (MODE_NOW) addNowLayers();
    map.setPadding(chromePadding());
    wireMap();
    await loadLiveEarth();
    wireLiveEarth();
    renderNav();
    renderEvents();
    renderTimeline();
    updateHud();
    updateFocusCard();
    syncTruthChrome();
    startPulse();
    await opening();
    await idle();
    document.documentElement.dataset.ready = "true";
    if (BENCH) runBench();
  });
  getJSON("/api/plugins").then((plugins) => { state.plugins = plugins; updateHud(); renderNav(); }).catch(() => { state.plugins = null; updateHud(); });
}

window.__tellurion = { state, selectById, setTick, setMode, toggleFocus, applyPreset, syncTruthChrome };
main();
