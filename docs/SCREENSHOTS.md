# Screenshot / video pipeline (V17, local only, no publishing)

Deterministic source: `godseye demo --hero` (frozen `community-demo-v1`,
`?demo=hero` pins event, camera, selection, timeline).

## Captures

| File | View |
|---|---|
| `docs/screenshots/hero-world.png` | world + event pulse |
| `docs/screenshots/event-evidence.png` | evidence drawer open |
| `docs/screenshots/entity-graph.png` | entity neighbourhood |
| `docs/screenshots/time-machine.png` | as-of applied (belief mode) |
| `docs/screenshots/source-health.png` | source health + blind spots |
| `docs/screenshots/plugin-system.png` | `godseye plugins --dir` output |

## Automated (Playwright, if browsers installed)

```bash
godseye demo --hero --port 8765
python scripts/capture_screenshots.py --port 8765 --out docs/screenshots
```

If browsers are missing (`playwright install` needs network), the script
exits non-zero with the exact manual command list and frame plan instead
of fake captures — never commit placeholder PNGs as real ones.

## Video / GIF (20–30 s)

```bash
python scripts/capture_screenshots.py --port 8765 --out preview-assets/frames --frames-only
ffmpeg -framerate 2 -i preview-assets/frames/frame-%02d.png -vf scale=1280:-1 demo-30s.mp4
```

If ffmpeg is unavailable, keep the frames + command (this file) and
encode later. Nothing uploads anywhere.

## Ultra filmstrip (V18, 20–30 s storyboard)

```bash
python scripts/capture_ultra_film.py   # 7 frames, world → movement → disruption → select → evidence → rewind → gallery
ffmpeg -framerate 2 -i preview-assets/frames-ultra-film/film-%02d.png -vf scale=1280:-1 ultra-30s.mp4
```

Rendered hero loop: `docs/screenshots/ultra-hero.gif` and
`docs/media/ultra-hero.mp4` (rights: `legal/ASSET_RIGHTS.json`).
