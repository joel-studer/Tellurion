# WORLD NOW demo (viral loop)

Base URL (localhost-only): `tellurion ultra` serves `/ultra`.
Two top-level modes, toggled in the UI and shareable via URL:

- WORLD NOW (`/ultra?view=world&mode=now`): **real** qualified public
  feeds, green REAL DATA bar. No synthetic object ever renders here.
- DEMO REPLAY (`/ultra?view=world`, harbour `/ultra`): deterministic
  synthetic replay, amber SYNTHETIC REPLAY banner. Works fully offline.

## Presets (shareable URLs — no secrets in state)

- WORLD NOW: `/ultra?view=world&mode=now`
- GLOBAL AVIATION (LIVE): `/ultra?view=world&mode=now&sky=aviation`
- IMPORTANT NOW: `/ultra?view=world&mode=now&sky=important`
- LIVE MOVEMENT: `/ultra?view=world&mode=now&sky=movement`
- Deep links: `&aircraft=<hex>` selects an aircraft, `&event=<key>`
  selects an event, `&region=Austria` frames a region, `&lat=&lon=&zoom=`
  restores camera. Selecting anything updates the URL (public state
  only — never keys or config); the share button copies it.
- WORLD REPLAY: `/ultra?view=world`
- GLOBAL AVIATION (replay density): `/ultra?view=aviation&density=dense`
- GLOBAL SHIPPING (replay density): `/ultra?view=shipping&density=dense`
- EARTH (replay): `/ultra?view=earth`
- SEVERE WEATHER (replay): `/ultra?view=storm`
- DISASTER WATCH (replay): `/ultra?view=disaster`
- SATELLITES (replay): `/ultra?view=satellites`
- AUSTRIA now: `/ultra?region=Austria&mode=now`
- AUSTRIA replay: `/ultra?region=Austria`

Density (`&density=standard|dense|full`: 3k / 5.4k / 11k synthetic
objects) applies to DEMO REPLAY only. Screenshots: `&focus=earthquake`
frames the story in replay mode.

## 30-second script V2 (WORLD NOW)

1. Open `/ultra?view=world&mode=now` — globe with current real public
   events; activity bar shows live-cache counts (quales, disasters,
   US alerts, space weather, reports) plus source-online count.
2. Click an earthquake — evidence drawer shows source time, first
   seen by Tellurion, rights, and a raw-source link.
3. A linked GDACS/GDELT signal appears under Related public signals
   with method + independence (SHARED_UPSTREAM never poses as
   independent; sensor + news may CORROBORATE).
4. Right-click anywhere — What's Happening Here returns only real
   cached signals, plus NO QUALIFIED SOURCE where appropriate.
5. Open source health — per-source ONLINE/STALE/RATE_LIMITED with
   last success, latency, next refresh; unavailable domains say
   KEY REQUIRED / NO QUALIFIED SOURCE instead of hiding.
6. Share the URL — the recipient sees the same mode and view.

No fake claims: DELAYED where delayed, UNKNOWN where unknown,
synthetic only when explicitly synthetic.

## Screenshots

Target set (`docs/screenshots/`):

- world-now-global.png — WORLD NOW globe, real events, health visible
- world-now-event.png — selected real event with evidence drawer open
- world-now-evidence.png — drawer detail (timestamps + source link)
- world-now-health.png — source-health panel (states + rights)
- world-now-coverage.png — coverage layer + blind spots
- demo-replay.png — existing deterministic hero (kept for offline)

Recipe: start the server, open `/ultra?view=world&mode=now`, wait for
the activity bar, capture with OS screenshot (no credentials on
screen by construction). The DEMO REPLAY hero stays for offline use,
tests, and reproducible screenshots.
