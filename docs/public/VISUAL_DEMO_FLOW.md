# VISUAL WOW-MOMENT (V15 — 30-second public demo flow)

Goal: a developer understands Tellurion in ~30 seconds with no keys,
no private alpha, no network beyond localhost.

## Flow (implemented in console/demo.html + /api/demo)

1. **Open** `tellurion demo` -> http://127.0.0.1:8765/ (dark console).
2. **Globe/map**: synthetic world grid with one pulsing event
   (Harborview bridge inspection announcement, CC0).
3. **Event pulse**: click the pulse -> event card (ts, family, label).
4. **Evidence trace**: evidence drawer lists 2 sourced quotes with ids/ts.
5. **Entity relationships**: OPERATES edge (Transit Authority -> Bridge 7)
   with method + model-version labels.
6. **Time machine**: as-of input + belief/replay toggle relabels the drawer.
7. **Market/source context**: synthetic replay bars (DEMO:XHB @ demo-venue)
   + prediction YES 0.62 / NO 0.38 + venue capability snippet.
8. **Plugin/source status**: source-health UP row + blind-spot row +
   sysbar (dataset, licence, venues, live=disabled).

## Prototype status

Implemented and clickable offline (same-origin `/api/demo` only).
No proprietary alpha required at any step. All numbers synthetic and
labelled as such.

## Remaining wow leverage (V16)

- Capture GIF of the 8-step flow for README.
- Add keyboard walkthrough (`n` = next step) for presentations.
- Optional: second synthetic event to show clustering (keep CC0).
