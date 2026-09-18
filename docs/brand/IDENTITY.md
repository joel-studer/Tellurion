# Tellurion identity

The world is the interface. The identity supports it and never competes with
it: calm dark surfaces, one warm accent (sunlight), and colour that always
means something.

## Symbol

A sunlit sphere, its day/night terminator, and an orbit tilted by 23.4°, the
Earth's axial tilt, with one point of light on the orbit.

| Element | Meaning |
|---|---|
| Sphere | the world |
| Lit crescent and terminator | time: the same world, a different moment |
| Tilted orbit | connections and movement |
| Point on the orbit | a signal, an event, a piece of evidence |

Deliberately not used: eyes, crosshairs, shields, radar sweeps, insignia,
latitude/longitude globe clip art, sparkles.

## Files

| File | Use |
|---|---|
| `console/brand/tellurion-mark.svg` | primary mark on dark backgrounds (64 px grid) |
| `console/brand/tellurion-mark-light.svg` | mark on light backgrounds |
| `console/brand/tellurion-wordmark.svg` | mark and name, for headers and the opening |
| `console/brand/favicon.svg` | 16 to 32 px: the orbit ring is dropped for legibility |
| `docs/brand/tellurion-mark-{16,32,64,180,512}.png` | rendered raster sizes |
| `docs/brand/tellurion-social-1200x630.png`, `tellurion-social-square-1080.png` | social cards |

Clear space: at least the diameter of the orbit point on every side. Minimum
size: 16 px (favicon), 24 px (mark with orbit). Do not recolour, rotate,
outline, or add effects.

## Name

**Tellurion**, written with a capital T and the rest lower case. The internal
codename GOD'S EYE is not used on public surfaces. The Python package stays
`gods_eye` for compatibility; the command line answers to both `tellurion`
and `godseye`.

## Colour

All ratios below were measured against the panel surface (`#0e151f`) with the
WCAG 2 formula. Every text and status colour passes AA for normal text.

| Token | Hex | Use | Contrast |
|---|---|---|---|
| text | `#e8eef6` | primary text | 15.7:1 |
| text-2 | `#b2bfce` | secondary text | 9.8:1 |
| text-3 | `#8290a3` | metadata | 5.6:1 |
| sun | `#ffb547` | brand accent, selection, primary action | 10.4:1 |

Category colours (map layers, event icons):

| Category | Hex | Contrast |
|---|---|---|
| Air | `#6aa8ff` | 7.6:1 |
| Maritime | `#37d2b0` | 9.6:1 |
| Space | `#b79cff` | 8.0:1 |
| Weather | `#9ec7e8` | 10.3:1 |
| Earth | `#ff8a5b` | 7.9:1 |
| Infrastructure | `#c9b38a` | 9.0:1 |
| Roads | `#e2c26f` | 10.6:1 |
| Cameras | `#e48fd0` | 8.0:1 |

Severity always pairs colour with a label and a shape (a diamond on cards and
timeline markers):

| Severity | Hex | Contrast |
|---|---|---|
| Info | `#8fa0b6` | 6.9:1 |
| Watch | `#f5c451` | 11.3:1 |
| Alert | `#ff8a3d` | 7.8:1 |
| Critical | `#ff4d5e` | 5.7:1 |

Source health uses a different shape per state as well as colour: a filled
dot for ONLINE, a rounded square for STALE and DEGRADED, a rotated square for
OFFLINE, and a hollow ring for UNKNOWN.

Earth: ocean `#081b2e`, land `#1c2d3f`, coastline `#6283a1`, borders
`#3a536c`, night side `#01040a` at 26 to 42 percent opacity. No neon, no glowing
borders.

## Typography

Inter (variable, SIL OFL 1.1, vendored for offline use) with the system UI
stack as fallback; system monospace for times, counts, and identifiers.

| Role | Size | Weight |
|---|---|---|
| Brand in header | 18 px | 650 |
| Drawer headline | 19 px | 650 |
| Panel title | 15 px | 650 |
| Card headline, layer name | 13.5 px | 580 to 600 |
| Body | 13 px | 400 |
| Metadata | 11.5 to 12 px | 400 to 600 |
| Section label (uppercase, tracked) | 11 to 11.5 px | 650 |

Nothing in the interface is smaller than 10.5 px (timeline tick labels).

## Surfaces and depth

Floating panels over the full-bleed globe: 90 percent opaque surface, 1 px
borders at 16 percent, a 12 px backdrop blur, and one soft shadow. No heavy
glassmorphism, no gradients except a faint severity tint at the top of the
evidence drawer.

## Motion

| Interaction | Duration | Easing |
|---|---|---|
| Hover, toggle, tooltip | 150 ms | ease |
| Drawer, dialog | 160 to 220 ms | cubic-bezier(0.2, 0.7, 0.2, 1) |
| Timeline thumb and fill | 250 ms | same |
| Moving objects between replay ticks | up to 900 ms | ease-out |
| Camera fly-to | 1.8 to 2.4 s | MapLibre flyTo curve 1.3 |
| Opening ("world awakens") | about 1.1 s total | fade and quarter turn |

Every animation represents state: moving objects are replay positions,
the pulse marks an active alert, the camera moves because you asked.
`prefers-reduced-motion` and capture mode turn motion off completely.

## Voice

Plain and exact. Label synthetic data as synthetic, modeled geometry as
modeled, and missing coverage as a blind spot. Never imply live data, AI
analysis, precision, or market claims the product does not have.
