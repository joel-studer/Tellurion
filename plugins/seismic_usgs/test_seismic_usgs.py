"""Seismic plugin test (offline, incl. USGS mapping over canned text)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / ".." / ".." / "python"))

from plugin import SeismicUsgs, declaration, from_usgs_geojson

CANNED = ('{"type":"FeatureCollection","features":[{"id":"us123","properties":'
          '{"mag":5.1,"place":"offshore","time":1726000000000},"geometry":'
          '{"coordinates":[-4.2,51.0,15.0]}}]}')


def test_manifest_declares():
    from gods_eye.future import plugins as pl
    out = pl.declare(**declaration())
    assert out["kind"] == "Sensor"
    assert pl.production_qualified(out) is True


def test_poll_offline():
    out = SeismicUsgs().poll()
    assert len(out["items"]) == 2
    assert out["items"][0]["mag"] == 4.2


def test_usgs_mapping_no_network():
    rows = from_usgs_geojson(CANNED)
    assert rows[0]["id"] == "us123"
    assert rows[0]["mag"] == 5.1
    assert rows[0]["rights"] == "US public domain"
