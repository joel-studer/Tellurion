"""Weather synth plugin test (offline)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / ".." / ".." / "python"))

from plugin import WeatherSynth, declaration


def test_manifest_declares():
    from gods_eye.future import plugins as pl
    out = pl.declare(**declaration())
    assert out["kind"] == "Sensor"
    assert pl.production_qualified(out) is True


def test_poll_offline():
    out = WeatherSynth().poll()
    assert len(out["items"]) == 8
    assert len(out["alerts"]) == 1
