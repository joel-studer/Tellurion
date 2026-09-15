# Pull request

## What + why (one paragraph)

## Checklist

- [ ] `godseye doctor` PASS (paste verdict)
- [ ] `python -m pytest -q` green
- [ ] No private-surface imports, no secrets, no outbound calls
- [ ] Rights basis stated honestly (licence ≠ data rights)

## New plugin? also confirm

- [ ] licence + rights + provenance + schema in `manifest.json`
- [ ] offline test shipped and green
- [ ] `godseye plugins validate ./dir` verdict pasted
- [ ] network/secrets needs declared (community: none)
- [ ] screenshot if UI surface changed
