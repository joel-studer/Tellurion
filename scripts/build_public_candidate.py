"""Build the standalone public-repo candidate (V17, local only).

Copies exactly `release_manifest.public_include()` into
`dist/tellurion-public-candidate/`, then layers candidate-only launch files
(.gitignore + public-layout alias packages) that keep the private
source repository untouched.

Nothing is published (no network, no upload, no git push).

Usage:
  python scripts/build_public_candidate.py [--out dist/tellurion-public-candidate]
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import release_manifest as rm  # noqa: E402

CANDIDATE_GITIGNORE = """\
# Tellurion public candidate — local only, never commit secrets
dist/
preview-assets/
# runtime state written by a running instance (live feed cache, local state)
raw_store/
state/
state_future/
.godseye/
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
*.egg-info/
*.log
.env
.DS_Store
Thumbs.db
"""

# Candidate-first public layout (V17-3): thin alias packages over the
# canonical modules. Private repo keeps canonical paths untouched.
# NOTE (V16 hardening): `gods_eye.demo` is intentionally NOT an alias
# directory — canonical `python/gods_eye/demo.py` already provides
# `gods_eye.demo`, and a same-named package dir would shadow the file
# module (breaking HOST/DEFAULT_PORT imports, doctor, smoke, release-check).
# The demo dataset alias lives under `gods_eye.future.demo_dataset`.
LAYOUT_ALIASES = {
    "gods_eye/core": "from gods_eye.future import venues  # noqa: F401\n",
    "gods_eye/plugins": (
        "from gods_eye.future import discovery  # noqa: F401\n"
        "from gods_eye.future import plugins  # noqa: F401\n"
        "from gods_eye.future import public_api  # noqa: F401\n"
        "from gods_eye.future import validator  # noqa: F401\n"),
}

LAYOUT_README = """\
# Public layout (candidate-first, V17)

Canonical modules live under `gods_eye.future.*` (stable import paths,
see `docs/guides/public-api-stability.md`). The alias packages in this
directory are thin re-exports for the friendlier layout:

- `gods_eye.core` — canonical event/world surface
- `gods_eye.plugins` — SDK + discovery + validator + public API
- `gods_eye.demo` — canonical demo server module (`gods_eye/demo.py`) +
- synthetic dataset via `gods_eye.future.demo_dataset`
- `gods_eye.market` — venues, prediction markets, catalog
- `gods_eye.execution` — execution contracts + safety gate
- `gods_eye.portfolio` — portfolio contracts + optimizer

New code should import from the alias packages; canonical paths keep
working (STABLE_PREVIEW promise).
"""


def build(out_dir: Path) -> dict:
    out_dir = out_dir.resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    copied: list[str] = []
    missing: list[str] = []
    for rel in rm.public_include():
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied.append(rel)
    # candidate-only launch files (not in the private manifest on purpose:
    # they describe the candidate, and the private repo must stay put)
    # newline="\n": generated files must hash identically on every OS.
    (out_dir / ".gitignore").write_text(CANDIDATE_GITIGNORE,
                                        encoding="utf-8", newline="\n")
    for alias, body in LAYOUT_ALIASES.items():
        pkg = out_dir / "python" / Path(*alias.split("/"))
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text(
            '"""Candidate alias package (V17, re-exports only)."""\n\n'
            + body, encoding="utf-8", newline="\n")
    (out_dir / "python" / "gods_eye" / "LAYOUT.md").write_text(
        LAYOUT_README, encoding="utf-8", newline="\n")
    report = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "out_dir": str(out_dir),
        "copied": len(copied),
        "missing": missing,
        "alias_packages": sorted(LAYOUT_ALIASES),
        "ok": not missing,
        "published": False,
        "note": "LOCAL candidate only. Not published, not pushed.",
    }
    (out_dir.parent / "candidate-build-report.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    return report


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def write_archive(out_dir: Path) -> dict:
    """Deterministic zip plus a per-file SHA-256 manifest of the built tree.

    Sorted POSIX names, fixed timestamps, fixed permissions and a fixed
    compression level: identical input bytes give an identical archive with
    the same Python/zlib. The technical checkpoint hash is computed over the
    sorted `sha256  path` lines, so it depends on file contents only, never on
    the compressor.
    """
    import hashlib
    import zipfile
    files = sorted((p for p in out_dir.rglob("*") if p.is_file()),
                   key=lambda p: p.relative_to(out_dir).as_posix())
    checksums = {p.relative_to(out_dir).as_posix():
                 hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    zip_path = out_dir.parent / f"{out_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        for p in files:
            info = zipfile.ZipInfo(p.relative_to(out_dir).as_posix(),
                                   date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes(), compresslevel=9)
    manifest = out_dir.parent / "tellurion-candidate-checksums.json"
    manifest.write_text(json.dumps(checksums, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    lines = "".join(f"{digest}  {rel}\n" for rel, digest in sorted(checksums.items()))
    return {"files": len(files), "archive": zip_path.name,
            "archive_bytes": zip_path.stat().st_size,
            "archive_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "checksum_manifest": manifest.name,
            "checksum_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "technical_checkpoint_sha256": hashlib.sha256(lines.encode("utf-8")).hexdigest()}


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(ROOT / "dist" / "tellurion-public-candidate"))
    p.add_argument("--no-archive", action="store_true",
                   help="skip the deterministic zip + checksum manifest")
    args = p.parse_args()
    report = build(Path(args.out))
    if report["ok"] and not args.no_archive:
        report["archive"] = write_archive(Path(args.out).resolve())
        (Path(args.out).resolve().parent / "candidate-build-report.json").write_text(
            json.dumps(report, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=1)[:1500])
    if not report["ok"]:
        print("CANDIDATE BUILD: FAIL", file=sys.stderr)
        return 1
    print(f"CANDIDATE BUILD: OK ({report['copied']} files + "
          f"{len(report['alias_packages'])} alias packages, NOT published)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
