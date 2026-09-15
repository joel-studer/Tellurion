"""Camera synth plugin test (offline, incl. safety surface check)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / ".." / ".." / "python"))

import plugin as _mod
from plugin import CameraSynth, declaration


def test_manifest_declares():
    from gods_eye.future import plugins as pl
    out = pl.declare(**declaration())
    assert out["kind"] == "Sensor"
    assert pl.production_qualified(out) is True


def test_poll_offline():
    out = CameraSynth().poll()
    assert len(out["items"]) == 6
    assert out["items"][0]["feed"] == "snapshot"


def test_no_person_capabilities():
    src = (_HERE / "plugin.py").read_text(encoding="utf-8").lower()
    for tok in ("facial", "face_recognition", "person_track",
                "identify_person", "credential", "password"):
        assert tok not in src, tok
    assert "FORBIDDEN" in (_HERE / "plugin.py").read_text(encoding="utf-8")
    _ = _mod.FORBIDDEN
