"""Demo API smoke probe for CI (V17, localhost only, no browser).

Starts `gods_eye.demo` on an ephemeral localhost port in-process,
hits /api/health + /api/demo, asserts the safety contract, exits 0/1.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def main() -> int:
    from gods_eye import demo as _demo
    assert _demo.HOST == "127.0.0.1", _demo.HOST
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://{_demo.HOST}:{port}"
        health = json.load(urllib.request.urlopen(
            base + "/api/health", timeout=5))
        assert health["ok"] is True, health
        # Beta contract: no allow_live key on /api/health (live mode is
        # declared once, in /api/demo safety.ALLOW_LIVE=false below).
        assert "allow_live" not in health, health
        assert health["community_mode"] is True, health
        payload = json.load(urllib.request.urlopen(
            base + "/api/demo", timeout=5))
        assert payload["demo"]["dataset_id"] == "community-demo-v1", payload
        assert payload["safety"]["ALLOW_LIVE"] is False, payload
        assert payload["community_mode"] is True, payload
    except Exception as e:
        print(f"SMOKE: FAIL ({type(e).__name__}: {e})")
        return 1
    finally:
        server.shutdown()
    print(f"SMOKE: OK (health+demo on 127.0.0.1:{port}, live disabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
