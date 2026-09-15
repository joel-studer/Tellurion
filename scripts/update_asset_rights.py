"""Maintain legal/ASSET_RIGHTS.json (rights basis + content hash per asset).

  python scripts/update_asset_rights.py --check   # exit 1 on any drift
  python scripts/update_asset_rights.py           # rewrite after review

Every asset needs a rule below. An asset without a rule fails: UNKNOWN
rights cannot ship. Plugin fixtures take their rights basis from the
sibling ``manifest.json`` (``data_rights``) and must be synthetic or CC0.
Changing a screenshot or fixture changes its hash, which forces a fresh
rights review before release-check passes again.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import boundary  # noqa: E402

RENDER_BASIS = (
    "Rendered by the project maintainer from the bundled synthetic CC0 demo "
    "(procedural geography; no third-party map tiles, imagery, or fonts).")

RULES = (
    ("docs/screenshots/*", "PROJECT-OWNED", RENDER_BASIS),
    ("docs/media/*", "PROJECT-OWNED", RENDER_BASIS),
    ("console/vendor/*", "BSD-2-Clause",
     "Leaflet 1.9.4 upstream release; licence text shipped as "
     "console/vendor/LEAFLET_LICENSE.txt."),
)


def _fixture_rule(root: Path, rel: str):
    manifest = (root / rel).parent / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rights = str(data.get("data_rights", "UNKNOWN"))
    low = rights.lower()
    if "unknown" in low or not ("synthetic" in low or "cc0" in low):
        return None
    return "CC0-1.0", f"Plugin fixture ({data.get('name', '?')}): {rights}"


def build(root: Path = ROOT):
    entries, errors = [], []
    for rel in boundary.asset_files(root):
        rule = next(((lic, basis) for pattern, lic, basis in RULES
                     if fnmatch.fnmatch(rel, pattern)), None)
        if rule is None and Path(rel).name.startswith("fixture"):
            rule = _fixture_rule(root, rel)
        if rule is None:
            errors.append(f"{rel}: no rights rule (add one to RULES, or "
                          "declare synthetic/CC0 data_rights in manifest.json)")
            continue
        entries.append({"path": rel, "license": rule[0], "basis": rule[1],
                        "sha256": boundary.asset_digest(root / rel)})
    manifest = {
        "schema": "asset-rights-v1",
        "policy": "UNKNOWN rights cannot ship; any content change requires "
                  "a new rights review (sha256).",
        "allowed_licenses": list(boundary.ALLOWED_ASSET_LICENSES),
        "assets": entries,
    }
    return manifest, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="compare only; exit 1 on drift")
    args = ap.parse_args()
    manifest, errors = build()
    for err in errors:
        print("RIGHTS:", err)
    if errors:
        return 1
    target = ROOT / boundary.RIGHTS_MANIFEST
    text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
    if args.check:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        ok = current.replace("\r\n", "\n") == text
        print("ASSET RIGHTS:", "OK" if ok else "DRIFT (review, then rerun "
              "without --check)")
        return 0 if ok else 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"ASSET RIGHTS: wrote {len(manifest['assets'])} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
