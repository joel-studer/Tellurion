# Clean Linux check

Proves the repository stands alone on a fresh Linux machine: no other
checkout, no credentials, network only for the package index.

## Steps

```bash
git clone <this repository> gods-eye && cd gods-eye
python3.13 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
godseye doctor                                   # verdict PASS
python -m pytest tests plugins examples -q -p no:cacheprovider
python scripts/smoke_demo_api.py                 # SMOKE: OK
python scripts/verify_install.py                 # VERIFY: PASS
godseye release-check                            # RELEASE CHECK: PASS
godseye new-plugin --kind sensor --name smoke-sensor --dir /tmp/smoke_sensor
python -m pytest /tmp/smoke_sensor -q
```

## Record

| Date | OS | Python | Commit | Result |
|---|---|---|---|---|
