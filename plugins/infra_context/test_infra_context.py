"""Infra context plugin test (offline)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / ".." / ".." / "python"))

from plugin import InfraContext, declaration


def test_manifest_declares():
    from gods_eye.future import plugins as pl
    out = pl.declare(**declaration())
    assert out["kind"] == "Sensor"
    assert pl.production_qualified(out) is True


def test_poll_offline():
    out = InfraContext().poll()
    kinds = {o["kind"] for o in out["items"]}
    assert {"PORT", "AIRPORT", "GRID_ZONE"} <= kinds
