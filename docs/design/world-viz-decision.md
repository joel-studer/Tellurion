# World visualization decision (V17, community demo)

## Status quo

The community demo renders a dependency-free SVG world grid with one
event pulse (`console/demo.html`). No map library ships: zero bundle,
zero network, fully offline, reviewable in one file.

## Candidates compared

| Criterion | SVG grid (now) | Leaflet | MapLibre GL JS | CesiumJS |
|---|---|---|---|---|
| Visual quality | Functional, abstract | Good 2D tiles | Strong vector 2D | Best 3D globe |
| Offline/demo ability | Full (no fetch) | Needs tiles (network or local pack) | Needs tiles/styles (heavier pack) | Needs tiles + terrain (heaviest) |
| Performance (1 pulse) | Trivial | Fine | Fine | Heavy init |
| Bundle size | 0 KB | ~150 KB + tiles | ~500 KB–1 MB + tiles | Multi-MB + assets |
| Plugin ecosystem | n/a | Large | Growing | Niche |
| 3D value for demo | None needed | None | Tilt lite | Real globe |
| Maintenance burden | Minimal | Low | Medium (styles) | High |

## Decision

**Keep the SVG grid for the community demo; do not adopt a map library
for V17.** Reasons: the demo dataset is one synthetic city-block event
(tile detail adds nothing), offline-first is a launch promise (tile
fetching would break it), and review burden stays minimal.

Operational consoles (Leaflet-based) are unaffected by this
decision. Revisit only when the public demo ships multi-region real
licensed data where tile context earns its weight — via a
`community/demo` prototype first, never by touching operator pages.
