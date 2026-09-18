"""Fail-closed path isolation guard (generic, profile-driven).

The open-source core ships with NO hardcoded protected paths. A downstream
project that keeps protected state next to a Tellurion checkout registers
an isolation profile at startup:

    from gods_eye.future import isolation

    isolation.configure(
        name="my-lab",
        protected_dirs=("state",),               # never writable
        protected_files=("config/frozen.json",),  # never writable
        read_forbidden=("evals/sealed.json",),    # never readable
    )

Without a profile only the structural rules apply: future-state writes
stay inside ``state_future/`` and path escapes are refused. All checks
resolve symlinks/``..`` via :meth:`Path.resolve` and fail CLOSED on OS
errors.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

_DEFAULT_ROOT = Path(__file__).resolve().parents[3]  # python/gods_eye/future/x.py

ROOT = _DEFAULT_ROOT
FUTURE_ROOT_NAME = "state_future"
PROFILE_NAME = "none"
PROTECTED_DIRS: tuple = ()
PROTECTED_FILES: tuple = ()
HOLDOUT_PATHS: tuple = ()  # read-forbidden paths (name kept for API stability)


class IsolationViolation(Exception):
    """Raised when future code attempts a forbidden path access."""


def _repo_relative(paths: Iterable[str]) -> tuple:
    out = []
    for raw in paths:
        rel = str(raw).replace(chr(92), "/").strip("/")
        if not rel or Path(rel).is_absolute() or ".." in rel.split("/"):
            raise ValueError(f"profile paths must be repo-relative: {raw!r}")
        out.append(rel)
    return tuple(out)


def configure(*, name: str, root: Optional[str | Path] = None,
              protected_dirs: Iterable[str] = (),
              protected_files: Iterable[str] = (),
              read_forbidden: Iterable[str] = ()) -> dict:
    """Install an isolation profile (replaces any previous profile)."""
    global ROOT, PROFILE_NAME, PROTECTED_DIRS, PROTECTED_FILES, HOLDOUT_PATHS
    new_root = Path(root).resolve() if root is not None else _DEFAULT_ROOT
    dirs = _repo_relative(protected_dirs)
    files = _repo_relative(protected_files)
    forbidden = _repo_relative(read_forbidden)
    ROOT, PROFILE_NAME = new_root, str(name)
    PROTECTED_DIRS, PROTECTED_FILES, HOLDOUT_PATHS = dirs, files, forbidden
    return read_only_active_state()


def reset() -> None:
    """Remove the active profile (back to structural rules only)."""
    global ROOT, PROFILE_NAME, PROTECTED_DIRS, PROTECTED_FILES, HOLDOUT_PATHS
    ROOT, PROFILE_NAME = _DEFAULT_ROOT, "none"
    PROTECTED_DIRS, PROTECTED_FILES, HOLDOUT_PATHS = (), (), ()


def _resolve(path: str | Path) -> Path:
    try:
        return Path(path).resolve()
    except OSError as e:  # fail closed: unresolvable -> deny
        raise IsolationViolation(f"unresolvable path denied: {path} ({e})")


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _matches(p: Path, rels: tuple) -> bool:
    for rel in rels:
        try:
            if p == (ROOT / rel).resolve():
                return True
        except OSError:
            return True
    return False


def is_protected(path: str | Path) -> bool:
    """True if future code must not WRITE this path. Fail-closed helper."""
    p = _resolve(path)
    for d in PROTECTED_DIRS:
        if _under(p, (ROOT / d).resolve()):
            return True
    return _matches(p, PROTECTED_FILES)


def is_holdout(path: str | Path) -> bool:
    """True if future code must not even READ this path."""
    return _matches(_resolve(path), HOLDOUT_PATHS)


is_read_forbidden = is_holdout


def assert_future_writable(path: str | Path) -> Path:
    """Return the resolved path if future code may write it, else raise."""
    p = _resolve(path)
    if is_holdout(p):
        raise IsolationViolation(f"read-forbidden path is never writable: {p}")
    if is_protected(p):
        raise IsolationViolation(
            f"protected path is never writable by future code: {p}")
    return p


def future_root() -> Path:
    """Future-state root (created on demand)."""
    root = ROOT / FUTURE_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def future_path(*parts: str) -> Path:
    """Resolve a future-state path under state_future/ (parents created)."""
    p = (future_root() / Path(*parts)).resolve()
    if not _under(p, future_root().resolve()):
        raise IsolationViolation(f"future path escapes state_future/: {parts}")
    assert_future_writable(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def open_ro_sqlite(path: str | Path) -> sqlite3.Connection:
    """Read-only sqlite open (query_only + busy timeout) for ops views.

    Refuses read-forbidden paths outright. Refuses missing files with
    IsolationViolation (callers treat as UNKNOWN, never fabricate).
    """
    p = _resolve(path)
    if is_holdout(p):
        raise IsolationViolation(f"read-forbidden path: {p}")
    if not p.is_file():
        raise IsolationViolation(f"store absent (treated as UNKNOWN): {p}")
    db = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10.0,
                         check_same_thread=False)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON;")
        db.execute("PRAGMA busy_timeout=5000;")
    except sqlite3.Error:
        pass
    return db


def read_only_active_state() -> dict:
    """Describe the active isolation profile (no file access)."""
    return {
        "profile": PROFILE_NAME,
        "root": str(ROOT),
        "protected_dirs": list(PROTECTED_DIRS),
        "protected_files": list(PROTECTED_FILES),
        "holdout_paths": list(HOLDOUT_PATHS),
        "future_root": FUTURE_ROOT_NAME,
    }
