"""FUTURE-ONLY public release manifest V2 (machine-readable, V16).

Single source of truth for what a future clean public repository may
contain. Classes:

  PUBLIC_INCLUDE  — shipped in the community preview artifact
  PUBLIC_EXCLUDE  — explicitly never shipped (private alpha / ops)
  DATA_DEPENDENT  — gated per dataset, never assumed
  GENERATED       — build/runtime output, never shipped
  PRIVATE         — alias marker for exclusion patterns (never shipped)

`classify(repo_relative_posix_path)` is total: every path gets exactly
one class (default PRIVATE for unknown paths — fail closed).
`assert_safe_for_release()` raises on anything that is not PUBLIC_INCLUDE.
The preview build script and the V16 tests both consume this module.
"""

from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import Dict, List, Tuple

CLASSES = ("PUBLIC_INCLUDE", "PUBLIC_EXCLUDE", "DATA_DEPENDENT",
           "GENERATED", "PRIVATE")

# Exact repo-relative POSIX paths shipped in the community preview.
PUBLIC_INCLUDE_FILES: Tuple[str, ...] = (
    # packaging / entry
    "pyproject.toml",
    ".gitignore",
    "python/gods_eye/__init__.py",
    "python/gods_eye/cli.py",
    "python/gods_eye/demo.py",
    # canonical contracts (market / venue / prediction / execution / portfolio)
    "python/gods_eye/future/__init__.py",
    # metadata layers (offline-first)
    # engine boundaries (fixture/disabled shapes only)
    # SDK / API / community / demo
    "python/gods_eye/future/plugins.py",
    "python/gods_eye/future/discovery.py",
    "python/gods_eye/future/public_api.py",
    "python/gods_eye/future/community.py",
    "python/gods_eye/future/demo_dataset.py",
    "python/gods_eye/future/optional_deps.py",
    "python/gods_eye/future/release_manifest.py",
    "python/gods_eye/future/validator.py",
    "python/gods_eye/future/release_check.py",
    "python/gods_eye/future/rights.py",
    "python/gods_eye/future/lineage.py",
    "python/gods_eye/future/isolation.py",
    "python/gods_eye/rights/registry.py",
    "python/gods_eye/rights/__init__.py",
    # ultra world surface (V18, synthetic replay, zero-key demo)
    "python/gods_eye/future/ultra_demo.py",
    "python/gods_eye/future/layers.py",
    "python/gods_eye/future/sensor_sources.py",
    # Tellurion WORLD NOW (real qualified public feeds, backend-only)
    "python/gods_eye/future/world_demo.py",
    # Tellurion globe replay scene + geodesy + boundary (replay backend)
    "python/gods_eye/future/world_scene.py",
    "python/gods_eye/future/geo.py",
    "python/gods_eye/future/boundary.py",
    "python/gods_eye/future/world_live.py",
    "python/gods_eye/future/world_now.py",
    # Tellurion live aviation (adsb.lol ODbL leg + IMPORTANT NOW engine)
    "python/gods_eye/future/world_air.py",
    # Tellurion change engine V1 (generic public change detection sidecar)
    "python/gods_eye/future/world_change.py",
    # Tellurion satellite evidence V2.1 (Sentinel-2 before/after sidecar)
    "python/gods_eye/future/world_imagery.py",
    # Tellurion LIVE EARTH V2.2 (GIBS freshness layer sidecar)
    "python/gods_eye/future/world_earth.py",
    # public UI (demo + landing + ultra + gallery; ops console stays private)
    "console/demo.html",
    "console/landing.html",
    "console/ultra.html",
    "console/gallery.html",
    # vendored map lib (offline demo; licence text ships alongside)
    "console/vendor/leaflet.js",
    "console/vendor/leaflet.css",
    "console/vendor/LEAFLET_LICENSE.txt",
    # local hero captures (deterministic ?demo=hero renders; binary,
    # scan-skipped; README references them so they ship with it)
    "docs/screenshots/time-machine.png",
    "docs/screenshots/source-health.png",
    # ultra captures (V18, synthetic demo frames, scan-skipped binary)
    # Tellurion WORLD NOW captures (real public feeds, local renders)
    "docs/screenshots/world-now-global.png",
    "docs/screenshots/world-now-event.png",
    "docs/screenshots/world-now-coverage.png",
    # WORLD NOW UI-consistency regression captures (defect-fix evidence:
    # mode-synced NOW chrome, regional selection framing, Important count,
    # coverage dialog, replay contrast — local renders, real public feeds)
    "docs/screenshots/world-now-important.png",
    "docs/screenshots/replay-global.png",
    # Tellurion live-aviation captures (real ADS-B, local renders)
    # Tellurion canonical hero (2560x1440, real WORLD NOW + selection)
    "docs/screenshots/hero-world-now.png",
    # Final WORLD NOW captures of the fixed UI (2026-09-17, real feeds,
    # local renders): aircraft drawer, region, recorded-track playback.
    "docs/screenshots/world-now-aircraft.png",
    "docs/screenshots/world-now-region.png",
    "docs/screenshots/world-now-time-machine.png",
    # CHANGE ENGINE V1 visual acceptance (real public feeds, local renders)
    "docs/screenshots/world-now-change-global.png",
    "docs/screenshots/world-now-change-drawer.png",
    "docs/screenshots/change-before-after.png",
    "docs/screenshots/replay-no-live-change-leak.png",
    "docs/screenshots/change-satellite-before-after.png",
    "docs/screenshots/change-satellite-cloud-limited.png",
    "docs/screenshots/change-satellite-no-observation.png",
    # LIVE EARTH V2.2 visual acceptance (NASA GIBS, local renders)
    "docs/screenshots/live-earth-global.png",
    "docs/screenshots/live-earth-goes-americas.png",
    "docs/screenshots/live-earth-himawari-pacific.png",
    "docs/screenshots/live-earth-daily-global.png",
    "docs/screenshots/live-earth-stale-fallback.png",
    "docs/screenshots/live-earth-with-change-pins.png",
    "docs/screenshots/replay-no-live-earth.png",
    # Release-evidence captures (Phase-8 visual gate, local renders)
    # hero loop (V18.5, 960px GIF rendered locally, scan-skipped binary)
    # public docs
    "docs/OPEN_CORE_BOUNDARY.md",
    "docs/public/RIGHTS_POLICY.md",
    "docs/public/SECURITY_DEFAULTS.md",
    # plugin template + contributor task
    "examples/plugins/example_sensor/manifest.json",
    "examples/plugins/example_sensor/plugin.py",
    "examples/plugins/example_sensor/fixture.json",
    "examples/plugins/example_sensor/test_example_sensor.py",
    "examples/contributor_tasks/add_demo_sensor.md",
    # Tellurion legal package lives under legal/ (see entries above);
    # no root preview stubs exist in this repo.
    # launch-candidate root (V17; drafts, sign-off still pending)
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/new_plugin.md",
    ".github/ISSUE_TEMPLATE/data_rights.md",
    ".github/pull_request_template.md",
    # public docs (V17; shipped only where present in this repo)
    "docs/TECH_STACK.md",
    "docs/ARCHITECTURE.md",
    "docs/RELEASE_NOTES_v1.0.0-beta.2.md",
    "docs/SCREENSHOTS.md",
    "docs/README.md",
    "docs/GOVERNANCE.md",
    "docs/guides/security-defaults.md",
    "docs/guides/rights-policy.md",
    # Tellurion globe UI (authoritative world surface + assets)
    "console/world.html",
    "console/world/app.js",
    "console/world/styles.css",
    "console/vendor/maplibre/maplibre-gl.mjs",
    "console/vendor/maplibre/maplibre-gl-worker.mjs",
    "console/vendor/maplibre/maplibre-gl.css",
    "console/vendor/maplibre/MAPLIBRE_LICENSE.txt",
    "console/vendor/fonts/inter-latin-wght-normal.woff2",
    "console/vendor/fonts/inter-latin-ext-wght-normal.woff2",
    "console/vendor/fonts/INTER_OFL_LICENSE.txt",
    "console/brand/favicon.svg",
    "console/brand/tellurion-mark.svg",
    "console/brand/tellurion-mark-light.svg",
    "console/brand/tellurion-wordmark.svg",
    "console/data/land-50m.json",
    "console/data/countries-50m.json",
    "console/data/WORLD_ATLAS_LICENSE.txt",
    "console/media/hero.png",
    "console/vendor/maplibre/maplibre-gl-shared.mjs",
    "docs/brand/tellurion-mark-16.png",
    "docs/brand/tellurion-mark-180.png",
    "docs/brand/tellurion-mark-32.png",
    "docs/brand/tellurion-mark-512.png",
    "docs/brand/tellurion-mark-64.png",
    "docs/brand/tellurion-social-1200x630.png",
    "docs/brand/tellurion-social-square-1080.png",
    "docs/media/tellurion-hero.mp4",
    "docs/screenshots/airport-story.png",
    "docs/screenshots/command-palette.png",
    "docs/screenshots/earth-story.png",
    "docs/screenshots/evidence-drawer.png",
    "docs/screenshots/focus-mode.png",
    "docs/screenshots/gallery.png",
    "docs/screenshots/investigation.png",
    "docs/screenshots/landing.png",
    "docs/screenshots/relations.png",
    "docs/screenshots/tellurion-hero-2560.png",
    "docs/screenshots/tellurion-hero.gif",
    "docs/screenshots/tellurion-hero.png",
    "docs/screenshots/tellurion-laptop-1440.png",
    "docs/screenshots/world-globe.png",
    ".gitattributes",
    "docs/guides/demo-performance.md",
    # Tellurion legal package (canonical; previews live here, not root)
    "legal/ASSET_RIGHTS.json",
    "LICENSE",
    "NOTICE",
    "legal/LICENSE_REVIEW.md",
    "legal/LICENSE_SIGNOFF.md",
    "legal/LICENSE_SIGNOFF_PACKET.md",
    "legal/SBOM.spdx.json",
    "legal/THIRD_PARTY_NOTICES.md",
    # AI-agent contributor task + checkers (V17)
    "examples/contributor_tasks/ai_sensor_task.md",
    "scripts/smoke_demo_api.py",
    "scripts/check_ai_task.py",
    "scripts/capture_screenshots.py",
    "scripts/bench_demo_perf.py",
    # ultra tooling (V18, offline, never publishes)
    "scripts/scout_sensors.py",
    "scripts/import_public_apis.py",
    "scripts/bench_ultra_density.py",
    "scripts/capture_ultra.py",
    # first-party sensor plugin pack (V18, CC0 fixtures, offline)
    "plugins/aviation_synth/manifest.json",
    # Tellurion live-leg plugins (fixture-backed, user opt-in, offline)
    "plugins/weather_nws/manifest.json",
    "plugins/weather_nws/plugin.py",
    "plugins/weather_nws/fixture.json",
    "plugins/disaster_eonet/manifest.json",
    "plugins/disaster_eonet/plugin.py",
    "plugins/disaster_eonet/fixture.json",
    "plugins/space_swpc/manifest.json",
    "plugins/space_swpc/plugin.py",
    "plugins/space_swpc/fixture.json",
    "plugins/austria_pack/manifest.json",
    "plugins/austria_pack/plugin.py",
    "plugins/austria_pack/fixture.json",
    "plugins/aviation_synth/plugin.py",
    "plugins/aviation_synth/fixture.json",
    "plugins/aviation_synth/test_aviation_synth.py",
    "plugins/maritime_synth/manifest.json",
    "plugins/maritime_synth/plugin.py",
    "plugins/maritime_synth/fixture.json",
    "plugins/maritime_synth/test_maritime_synth.py",
    "plugins/satellite_synth/manifest.json",
    "plugins/satellite_synth/plugin.py",
    "plugins/satellite_synth/fixture.json",
    "plugins/satellite_synth/test_satellite_synth.py",
    "plugins/weather_synth/manifest.json",
    "plugins/weather_synth/plugin.py",
    "plugins/weather_synth/fixture.json",
    "plugins/weather_synth/test_weather_synth.py",
    "plugins/seismic_usgs/manifest.json",
    "plugins/seismic_usgs/plugin.py",
    "plugins/seismic_usgs/fixture.json",
    "plugins/seismic_usgs/test_seismic_usgs.py",
    "plugins/wildfire_synth/manifest.json",
    "plugins/wildfire_synth/plugin.py",
    "plugins/wildfire_synth/fixture.json",
    "plugins/wildfire_synth/test_wildfire_synth.py",
    "plugins/traffic_synth/manifest.json",
    "plugins/traffic_synth/plugin.py",
    "plugins/traffic_synth/fixture.json",
    "plugins/traffic_synth/test_traffic_synth.py",
    "plugins/camera_synth/manifest.json",
    "plugins/camera_synth/plugin.py",
    "plugins/camera_synth/fixture.json",
    "plugins/camera_synth/test_camera_synth.py",
    "plugins/infra_context/manifest.json",
    "plugins/infra_context/plugin.py",
    "plugins/infra_context/fixture.json",
    "plugins/infra_context/test_infra_context.py",
    # Tellurion test lane (this repo's suites; green standalone)
    "tests/test_boundary.py",
    "tests/test_preview_surface.py",
    "tests/test_ultra.py",
    "tests/test_world.py",
    # Tellurion verification + capture tooling (offline, never publishes)
    "scripts/verify_candidate.py",
    "scripts/build_public_candidate.py",
    "scripts/smoke_real_sources.py",
    "scripts/smoke_aviation.py",
    # Tellurion standalone test lane (green without private tree)
    "tests/test_aviation_v21.py",
    "tests/test_world_now_v20.py",
    "tests/test_world_coverage_v19.py",
    "tests/test_future_preview_v16.py",
    "tests/test_future_ultra_v18.py",
    # WORLD NOW UI truth contract + final-pass browser-defect regressions
    "tests/test_world_now_ui.py",
    # CHANGE ENGINE V1 contract (detectors, idempotency, schema gates)
    "tests/test_world_change_v22.py",
    # SATELLITE EVIDENCE V2.1 contract (selection, rights, API, drawer)
    "tests/test_world_imagery_v23.py",
    # LIVE EARTH V2.2 contract (selection, freshness, API, mode)
    "tests/test_world_earth_v24.py",
    # SATELLITE EVIDENCE V2.1 contract (selection, rights, API, drawer)
    # SATELLITE EVIDENCE V2.1 contract (selection, rights, API, drawer)
    # Tellurion public source docs (terms evidence, decisions, demos)
    "docs/public/TERMS_SNAPSHOTS.md",
    "docs/public/WORLD_NOW_DEMO.md",
    "docs/public/WORLD_SOURCE_MATRIX.md",
    "docs/public/SOURCE_REGISTRY_V2.md",
    "docs/public/AUSTRIA_PACK.md",
    "docs/public/REGIONAL_PACKS.md",
    "docs/public/CONTRIBUTING_SOURCES.md",
    "docs/public/USER_KEYS.md",
    "docs/public/LIVE_AVIATION_SOURCE_DECISION.md",
    "docs/public/LIVE_MARITIME_SOURCE_DECISION.md",
    "docs/public/SATELLITE_SOURCE_DECISION.md",
    "docs/public/ADSB_LOL_PRODUCTION_CONTACT.md",
    "docs/public/HUMAN_PILOT_PACKAGE.md",
    "docs/public/HUMAN_REVIEW_PACKAGE.md",
    ".github/RELEASE_GATES.json",
    "conftest.py",
    # Docs and tools linked from shipped README/docs (link check 2026-09-17:
    # every relative link in a shipped page must resolve inside the candidate).
    "docs/brand/BRAND_NAMING_STUDY.md",
    "docs/brand/IDENTITY.md",
    "docs/design/PRODUCT_DESIGN_AUDIT.md",
    "docs/design/maplibre-vs-leaflet.md",
    "docs/design/ultra-design-system.md",
    "docs/design/world-renderer-decision.md",
    "docs/design/world-viz-decision.md",
    "docs/guides/clean-linux-check.md",
    "docs/guides/demo-script-30s.md",
    "docs/guides/external-plugin-pilot.md",
    "docs/guides/plugin-trust-model.md",
    "docs/guides/plugin-walkthrough.md",
    "docs/guides/public-api-stability.md",
    "docs/guides/sensor-source-catalogs.md",
    "scripts/verify_install.py",
    "scripts/capture_world.py",
)

# Generic directory prefixes that are never shipped (runtime state, ops,
# data). Private module names are deliberately NOT listed here: the public
# tree must not name private code, and classify() is fail-closed anyway —
# any path not in PUBLIC_INCLUDE_FILES is never shippable.
PUBLIC_EXCLUDE_PREFIXES: Tuple[str, ...] = (
    "state/",
    "state_future/",
    "evals/",
    "raw_store/",
    "logs/",
    "scripts/",
    "src/",
    "proto/",
    "harvest/",
    "console/vendor/",
)

# Exact never-ship files. Intentionally empty in the public tree: naming
# specific private artefacts would itself leak them. Fail-closed
# classification plus the generic prefixes above already exclude them.
PUBLIC_EXCLUDE_FILES: Tuple[str, ...] = ()

# Gated per dataset (never assumed redistributable).
DATA_DEPENDENT_PREFIXES: Tuple[str, ...] = (
    "state_future/market/",
    "state_future/lse/",
    "state_future/replay/",
)

# Build/runtime output (never shipped).
GENERATED_PREFIXES: Tuple[str, ...] = (
    "dist/",
    "preview-assets/",
    "__pycache__/",
    ".pytest_cache/",
    ".venv/",
    "venv/",
    "*.egg-info/",
)

# (file suffix, hit prefix, reason) triples for scanner allowlists:
# defensive boundary references (deny-list literals, import guards,
# guard paths, boundary docs) that name private surface without
# exposing contents. Anything not listed stays a violation.
# Shared by scripts/build_preview_artifact.py and
# gods_eye.future.release_check (single source of truth).
SCAN_ALLOWLIST: Tuple[Tuple[str, str, str], ...] = (
    ("python/gods_eye/future/exec_safety.py", "SECRET_PATTERN",
     "FORBIDDEN_CREDENTIAL_KEYS deny-list (names refused, no values)"),
    ("python/gods_eye/future/demo_dataset.py", "SECRET_PATTERN",
     "validate_no_holdout_refs forbidden-token tuple (names only)"),
    ("python/gods_eye/future/community.py", "PRIVATE_NAME",
     "PRIVATE_SUBSTRINGS import guard (names refused, no imports)"),
    ("python/gods_eye/cli.py", "PRIVATE_NAME",
     "user-facing fix hint naming the boundary (no import, no values)"),
    ("python/gods_eye/future/isolation.py", "PRIVATE_NAME",
     "PROTECTED_FILES guard paths (fail-closed write guard)"),
    ("python/gods_eye/future/isolation.py", "HOLDOUT_REF",
     "HOLDOUT_PATHS read guard (never reads contents)"),
    ("python/gods_eye/future/__init__.py", "HOLDOUT_REF",
     "boundary docstring (names the guard, no contents)"),
    ("python/gods_eye/future/execution.py", "PRIVATE_NAME",
     "docstring stating no private research logic (descriptive, no logic)"),
    ("python/gods_eye/future/lineage.py", "PRIVATE_NAME",
     "manifest-tuple field name (generic research term, no private import)"),
    ("python/gods_eye/future/plugins.py", "PRIVATE_NAME",
     "forbidden-capability tokens refused at declaration"),
    ("python/gods_eye/future/discovery.py", "PRIVATE_NAME",
     "docstring (no auto-execute policy text)"),
    ("python/gods_eye/future/validator.py", "SECRET_PATTERN",
     "credential deny-list tokens refused in plugin code (names only)"),
    ("python/gods_eye/future/validator.py", "PRIVATE_NAME",
     "private-surface guard tokens refused in plugins (names only)"),
    ("python/gods_eye/future/release_check.py", "SECRET_PATTERN",
     "release scan patterns (names only, never values)"),
    ("python/gods_eye/future/release_check.py", "PRIVATE_NAME",
     "release scan allowlist-definition literals (names only)"),
    ("python/gods_eye/future/release_check.py", "HOLDOUT_REF",
     "release scan patterns (names only, never contents)"),
    ("python/gods_eye/future/release_manifest.py", "PRIVATE_NAME",
     "PRIVATE_MARKERS exclusion patterns (names only)"),
    ("python/gods_eye/future/release_manifest.py", "HOLDOUT_REF",
     "exclusion list entries (names only, never contents)"),
    ("python/gods_eye/rights/registry.py", "PRIVATE_NAME",
     "rights-basis prose (no private logic)"),
    ("docs/OPEN_CORE_BOUNDARY.md", "PRIVATE_NAME",
     "boundary doc: names what stays private (no contents)"),
    ("docs/OPEN_CORE_BOUNDARY.md", "HOLDOUT_REF",
     "boundary doc: holdout named as excluded (no contents)"),
    ("docs/public/COMMUNITY_PACKAGE_MAP.md", "PRIVATE_NAME",
     "package map: private lane named as never-published"),
    ("docs/public/COMMUNITY_PACKAGE_MAP.md", "HOLDOUT_REF",
     "package map: holdout named as never-published"),
    ("docs/public/CONTRIBUTING_DRAFT.md", "PRIVATE_NAME",
     "contributor rule: never import private modules"),
    ("docs/public/SECURITY_DEFAULTS.md", "SECRET_PATTERN",
     "security doc: credential names listed as refused"),
    ("docs/public/SECURITY_DEFAULTS.md", "PRIVATE_NAME",
     "security doc: private modules named as forbidden"),
    ("docs/public/RIGHTS_POLICY.md", "PRIVATE_NAME",
     "rights doc: refused capability tokens named"),
    ("docs/public/PLUGIN_TRUST_MODEL.md", "PRIVATE_NAME",
     "trust doc: private modules named as forbidden"),
    ("docs/public/PLUGIN_TRUST_MODEL.md", "SECRET_PATTERN",
     "trust doc: credential names listed as refused"),
    ("docs/public/PUBLIC_API_STABILITY.md", "PRIVATE_NAME",
     "stability doc: internal surface named as non-public"),
    ("docs/public/PUBLIC_REPO_EXTRACTION_PLAN.md", "PRIVATE_NAME",
     "extraction doc: excluded paths named"),
    ("docs/public/PUBLIC_REPO_EXTRACTION_PLAN.md", "HOLDOUT_REF",
     "extraction doc: holdout named as excluded"),
    ("docs/public/EXTERNAL_PLUGIN_PILOT.md", "PRIVATE_NAME",
     "pilot doc: private modules named as forbidden"),
    ("docs/public/README_DRAFT.md", "PRIVATE_NAME",
     "readme: private edge named as excluded"),
    ("docs/public/OSS_LAUNCH_READINESS.md", "PRIVATE_NAME",
     "readiness doc: private lane named"),
    ("docs/public/DEMO_SCRIPT_30S.md", "PRIVATE_NAME",
     "demo script: private modules named as forbidden"),
    ("examples/contributor_tasks/add_demo_sensor.md", "PRIVATE_NAME",
     "task doc: private modules named as forbidden"),
    ("console/demo.html", "PRIVATE_NAME",
     "UI footer: private edge named as excluded (no logic)"),
    ("console/landing.html", "PRIVATE_NAME",
     "landing footer: private edge named as excluded"),
    ("docs/public/PRIVATE_LEAKAGE_AUDIT.md", "PRIVATE_NAME",
     "leak audit: refused tokens named as inspected-and-absent"),
    ("docs/public/PRIVATE_LEAKAGE_AUDIT.md", "HOLDOUT_REF",
     "leak audit: holdout named as inspected-and-absent"),
    ("scripts/build_preview_artifact.py", "SECRET_PATTERN",
     "preview scanner: pattern-definition literals (names only)"),
    ("scripts/build_preview_artifact.py", "PRIVATE_NAME",
     "preview scanner: pattern-definition literals (names only)"),
    ("scripts/build_preview_artifact.py", "HOLDOUT_REF",
     "preview scanner: pattern-definition literals (names only)"),
    ("tests/test_future_preview_v16.py", "HOLDOUT_REF",
     "manifest fail-closed test: holdout paths asserted NOT includable"),
    ("tests/test_future_venues_v15.py", "SECRET_PATTERN",
     "negative tests: credential tokens asserted ABSENT from demo "
     "source (names only, never values)"),
    ("tests/test_future_venues_v15.py", "PRIVATE_NAME",
     "negative tests: private-surface tokens asserted ABSENT from "
     "demo source (names only, no imports)"),
    ("tests/test_future_venues_v15.py", "HOLDOUT_REF",
     "isolation guard test: holdout path asserted guarded (no contents)"),
)


# Generic substrings that prove a path is private (defence in depth).
# Project-specific private markers are injected at run time by the private
# side via TELLURION_DENY_MARKERS (comma-separated) and never ship here.
PRIVATE_MARKERS: Tuple[str, ...] = (
    "holdout",
    ".env",
    "credentials",
    "secrets/",
    "wallets",
)


def private_markers() -> Tuple[str, ...]:
    """Generic markers plus any injected via TELLURION_DENY_MARKERS."""
    extra = tuple(m.strip() for m in
                  os.environ.get("TELLURION_DENY_MARKERS", "").split(",")
                  if m.strip())
    return PRIVATE_MARKERS + extra


class ReleaseViolation(Exception):
    """Raised when a path is not safe for the public release artifact."""


def classify(rel_posix: str) -> str:
    """Total classification (fail-closed: unknown -> PRIVATE)."""
    p = rel_posix.replace("\\", "/")
    # Strip a single leading "./" (or absolute "/") only. A blanket
    # strip of "." would mangle dotfiles (".github/..." must stay
    # addressable for exact-include matching).
    if p.startswith("./"):
        p = p[2:]
    p = p.lstrip("/")
    low = p.lower()
    for marker in private_markers():
        if marker.lower() in low and p not in PUBLIC_INCLUDE_FILES:
            return "PRIVATE"
    if p in PUBLIC_INCLUDE_FILES:
        return "PUBLIC_INCLUDE"
    if p in PUBLIC_EXCLUDE_FILES:
        return "PUBLIC_EXCLUDE"
    for prefix in PUBLIC_EXCLUDE_PREFIXES:
        if p == prefix.rstrip("/") or p.startswith(prefix):
            return "PUBLIC_EXCLUDE"
    for prefix in DATA_DEPENDENT_PREFIXES:
        if p.startswith(prefix):
            return "DATA_DEPENDENT"
    for prefix in GENERATED_PREFIXES:
        pre = prefix.replace("*", "")
        if pre in p:
            return "GENERATED"
    return "PRIVATE"


def assert_safe_for_release(rel_posix: str) -> str:
    cls = classify(rel_posix)
    if cls != "PUBLIC_INCLUDE":
        raise ReleaseViolation(
            f"not safe for public release ({cls}): {rel_posix}")
    return cls


def manifest_summary() -> Dict[str, object]:
    counts: Dict[str, int] = {c: 0 for c in CLASSES}
    for f in PUBLIC_INCLUDE_FILES:
        counts[classify(f)] += 1
    return {"schema": "release-manifest-v1",
            "n_public_include": len(PUBLIC_INCLUDE_FILES),
            "all_included_classify_clean": all(
                classify(f) == "PUBLIC_INCLUDE"
                for f in PUBLIC_INCLUDE_FILES),
            "counts": counts,
            "rule": "unknown paths default to PRIVATE (fail closed)"}


def public_include() -> List[str]:
    return sorted(PUBLIC_INCLUDE_FILES)
