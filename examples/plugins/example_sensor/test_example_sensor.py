"""Example plugin test (offline, no keys, no private imports)."""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
# Dev-tree convenience only: when this copy still lives inside the repo
# template (examples/plugins/example_sensor), also offer the repo's
# python/ dir. Never assume depth — walk up looking for a marker and
# never raise when scaffolded out-of-tree (e.g. /tmp/smoke_sensor),
# where `gods_eye` comes from the installed package (pip install -e .).
for _cand in (_HERE, *_HERE.parents):
    if ((_cand / "python" / "gods_eye" / "__init__.py").is_file()
            and (_cand / "pyproject.toml").is_file()):
        if str(_cand / "python") not in sys.path:
            sys.path.insert(0, str(_cand / "python"))
        break

from plugin import ExampleSensor, declaration  # noqa: E402


def test_manifest_declares():
    from gods_eye.future import plugins as pl
    d = declaration()
    out = pl.declare(**d)
    assert out["kind"] == "Sensor"
    assert pl.production_qualified(out) is True


def test_poll_offline():
    out = ExampleSensor().poll()
    assert len(out["items"]) == 2
    assert "CC0" in out["rights"] or "cc0" in out["rights"].lower()


def test_register_via_public_api():
    from gods_eye.future import public_api as api
    api.clear_registry()
    try:
        receipt = api.register_sensor(declaration())
        assert receipt["ok"] and receipt["production_qualified"] is True
    finally:
        api.clear_registry()
