# ULTRA VISUAL DESIGN SYSTEM (V18 — professional intelligence workstation)

> Goal: the first screen impresses, the second click earns trust.
> No neon overload, no unreadable microtype, no random colors, no
> flashing gimmicks.

## Palette (dark ops surface)

- Background: `#0b0e14` (app), `#11161f` (panels), `#181e29` (raised).
- Borders: `1px solid #26303f` (subtle); focus ring `#5aa9ff`.
- Text: `#e8edf5` primary, `#9aa4b2` secondary, `#5f6b7d` muted.
- Accent (selection/links): `#5aa9ff`.
- Status: ok `#4fd1a5`, warn `#ffc857`, fail `#ff6b4a`, blind `#6b7280`.
- Layer colors (fixed, legend-bound): aircraft `#5aa9ff`, vessels
  `#4fd1a5`, satellite `#b48cff`, weather `#ffc857`, wildfire
  `#ff6b4a`, seismic `#ff9f68`, traffic `#ffd166`, cameras `#8fd0ff`,
  ports `#7fe0d4`, airports `#a8c8ff`, infra `#c9b8ff`, energy
  `#ffe08a`, notices `#d7dce3`, disaster `#ff8fa3`, events `#ffffff`,
  entities `#cfe3ff`, blind `#6b7280`.

## Typography / spacing

- Font stack: system UI (`-apple-system, "Segoe UI", Roboto, …`),
  monospace for ids/timestamps (`ui-monospace, Consolas, monospace`).
- Scale: 12px meta, 13px body, 15px panel titles, 20px command bar,
  24px hero numbers. Minimum body 12px — nothing smaller ships.
- Spacing: 4px base (4/8/12/16/24). Panel radius 8px.

## States

- Observation chips: OBSERVED (solid dot), INFERRED (hollow dot),
  CORROBORATED (double dot), UNKNOWN (grey `?`). Never color-only:
  every chip has a text label.
- Source health: OK / DEGRADED / STALE / OFFLINE / RIGHTS_BLOCKED /
  BLIND — each with icon + label + `last_update`.
- Approximate location: dashed outline + "APPROX" tag.
- Blind spots: hatched grey region + reason + "not absence" caption.
- Selection: 2px accent outline + drawer opens; Esc clears.
- Reduced motion: `prefers-reduced-motion` disables pulse/sweep;
  static markers remain fully usable.

## Icons (V18.5)

Hand-drawn inline SVG (plane, ship, satellite dish, cloud, pulse,
cone, flame, camera, tower, anchor, grid, bolt, doc, nodes, file,
blind) — original artwork, no third-party assets, no attribution
debt. Vendored Leaflet BSD-2-Clause (`console/vendor/
LEAFLET_LICENSE.txt`); MapLibre prototype BSD-3-Clause
(MapLibre licence text, prototype only, not
shipped).

- Top command bar (48px): wordmark, LOCAL/REPLAY/DEMO state, active
  source count, active layer count, health dot, clock, search.
- Left panel (280px): layer stack by group, event stream, filters,
  watchlist.
- Center: world surface (dominant, ≥55% width).
- Right drawer (320px, collapsible): selection evidence.
- Bottom (120px): Time Machine (modes, cursor, replay controls).
- 1080p readable, 1440p comfortable; panels scroll independently;
  keyboard: `/` search, `Esc` clear, arrows move time.
