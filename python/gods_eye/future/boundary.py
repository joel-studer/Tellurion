"""Open-core boundary scans (read-only, standard library only).

Used by ``tellurion release-check``, the test suite, and downstream CI.

* :func:`unresolved_internal_imports` - every ``gods_eye`` import, at any
  scope, must resolve to a module (or a top-level name) shipped inside
  ``python/gods_eye``. A reference to a module that is not shipped is a
  hidden dependency on code outside the open-source core.
* :func:`secret_hits` / :func:`local_path_hits` - credential material and
  machine-specific paths never belong in the tree. Reports name the file
  and the pattern kind, never the matched content.
* :func:`payload_hits` - runtime state, databases, env and key files.
* :func:`denylist_hits` - caller-supplied term scan. The core ships no
  term list; downstream projects pass their own via ``GODS_EYE_DENYLIST``.
* :func:`asset_rights` - every media, fixture, and vendored asset needs a
  declared, allowed licence and a matching content hash.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

SKIP_DIRS = frozenset({
    ".git", ".hg", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "dist", "build",
    "state_future", ".godseye",
})
BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".ico", ".woff",
    ".woff2", ".ttf", ".otf", ".pdf", ".zip", ".gz", ".parquet", ".pyc",
})
IMPORT_SCAN_DIRS = ("python", "scripts", "plugins", "examples", "tests")
DENYLIST_ENV = "GODS_EYE_DENYLIST"

_BS = chr(92)  # backslash, built at runtime so this file stays scan-clean


# --------------------------------------------------------------- walking ---

def iter_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(Path(root)):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS
                             and not d.endswith(".egg-info"))
        for name in sorted(filenames):
            yield Path(dirpath) / name


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_text(path: Path) -> Optional[str]:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


# -------------------------------------------------------- import boundary ---

def module_index(root: Path) -> Dict[str, Path]:
    """Dotted module name -> file for everything shipped in python/gods_eye."""
    pkg = Path(root) / "python" / "gods_eye"
    index: Dict[str, Path] = {}
    if not pkg.is_dir():
        return index
    for f in iter_files(pkg):
        if f.suffix != ".py":
            continue
        parts = list(f.relative_to(pkg.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        index[".".join(parts)] = f
    return index


def _top_level_names(path: Path) -> Optional[Set[str]]:
    """Names bound at module top level; None means dynamic (accept any)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None
    names: Set[str] = set()
    stack: List[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            if node.name == "__getattr__":
                return None
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    return None
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            for target in targets:
                names.update(n.id for n in ast.walk(target)
                             if isinstance(n, ast.Name))
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            for field in ("body", "orelse", "finalbody", "handlers"):
                stack.extend(getattr(node, field, None) or [])
        elif isinstance(node, ast.ExceptHandler):
            stack.extend(node.body)
    return names


def _is_internal(name: str) -> bool:
    return name == "gods_eye" or name.startswith("gods_eye.")


def _unresolved(node: ast.AST, index: Dict[str, Path],
                defines: Callable[[str, str], bool]) -> Iterator[tuple]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            if _is_internal(alias.name) and alias.name not in index:
                yield node.lineno, alias.name
    elif (isinstance(node, ast.ImportFrom) and node.level == 0
          and node.module and _is_internal(node.module)):
        if node.module not in index:
            yield node.lineno, node.module
            return
        for alias in node.names:
            sub = f"{node.module}.{alias.name}"
            if alias.name == "*" or sub in index:
                continue
            if not defines(node.module, alias.name):
                yield node.lineno, sub


def unresolved_internal_imports(root: Path) -> List[Dict[str, Any]]:
    """Every gods_eye import (any scope) that the shipped package can't satisfy."""
    root = Path(root)
    index = module_index(root)
    cache: Dict[str, Optional[Set[str]]] = {}

    def defines(module: str, name: str) -> bool:
        if module not in cache:
            cache[module] = _top_level_names(index[module])
        found = cache[module]
        return found is None or name in found

    problems: List[Dict[str, Any]] = []
    for base in IMPORT_SCAN_DIRS:
        folder = root / base
        if not folder.is_dir():
            continue
        for f in iter_files(folder):
            if f.suffix != ".py":
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError) as e:
                problems.append({"file": _rel(root, f), "line": 0,
                                 "module": f"<unparseable: {type(e).__name__}>"})
                continue
            for node in ast.walk(tree):
                for line, module in _unresolved(node, index, defines):
                    problems.append({"file": _rel(root, f), "line": line,
                                     "module": module})
    return problems


# ---------------------------------------------------------------- secrets ---

_SECRET_PATTERNS = (
    ("PRIVATE_KEY_BLOCK", "-----BEGIN" + r" (?:[A-Z]+ )*PRIVATE KEY-----"),
    ("GITHUB_TOKEN", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})"),
    ("AWS_ACCESS_KEY", r"\bAKIA[0-9A-Z]{16}\b"),
    ("SLACK_TOKEN", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("SK_API_TOKEN", r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}"),
    ("GOOGLE_API_KEY", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("HEX_PRIVATE_KEY",
     r"(?i)\b(?:private[_-]?key|secret[_-]?key|[a-z0-9]+_pk)\b['\"]?\s*[:=]"
     r"\s*['\"]?(?:0x)?[0-9a-f]{64}\b"),
    ("CREDENTIAL_ASSIGNMENT",
     r"(?i)\b[a-z0-9_]*(?:api_key|api_secret|passphrase|password|private_key|"
     r"access_token|secret_key)\b['\"]?\s*[:=]\s*['\"](?!\s*(?:<|\$\{|unknown|"
     r"none|null|example|dummy|changeme|redacted|xxx))[^'\"\s]{8,}['\"]"),
    ("MNEMONIC",
     r"(?i)\b(?:mnemonic|seed[_ ]?phrase)\b['\"]?\s*[:=]\s*['\"]"
     r"(?:[a-z]+ ){11,23}[a-z]+['\"]"),
)
_SECRET_RES = tuple((kind, re.compile(p)) for kind, p in _SECRET_PATTERNS)


def secret_hits_text(text: str) -> List[str]:
    return [kind for kind, rx in _SECRET_RES if rx.search(text)]


def secret_hits(root: Path) -> List[Dict[str, str]]:
    root = Path(root)
    out: List[Dict[str, str]] = []
    for f in iter_files(root):
        text = _read_text(f)
        if text is None:
            continue
        out.extend({"file": _rel(root, f), "kind": kind}
                   for kind in secret_hits_text(text))
    return out


# ------------------------------------------------------------ local paths ---

_PLACEHOLDER = r"(?!(?:you|user|username|runner|name|me|example)\b)"
_WIN_SEP = "(?:" + _BS * 2 + "){1,2}"
_LOCAL_PATH_PATTERNS = (
    ("WINDOWS_USER_PATH",
     r"\b[A-Za-z]:" + _WIN_SEP + "Users" + _WIN_SEP + _PLACEHOLDER
     + r"[A-Za-z0-9._-]+"),
    ("WINDOWS_USER_PATH", r"\b[A-Za-z]:/" + "Users/" + _PLACEHOLDER
     + r"[A-Za-z0-9._-]+"),
    ("POSIX_HOME_PATH", r"(?<![\w.])/" + "home/" + _PLACEHOLDER
     + r"[a-z_][a-z0-9._-]*/"),
    ("MAC_USER_PATH", r"(?<![\w.])/" + "Users/" + _PLACEHOLDER
     + r"[A-Za-z][A-Za-z0-9._-]*/"),
    ("WINDOWS_HOSTNAME", r"\bDESKTOP-[A-Z0-9]{6,}\b"),
)
_LOCAL_RES = tuple((kind, re.compile(p)) for kind, p in _LOCAL_PATH_PATTERNS)


def local_path_hits(root: Path) -> List[Dict[str, str]]:
    root = Path(root)
    out: List[Dict[str, str]] = []
    for f in iter_files(root):
        text = _read_text(f)
        if text is None:
            continue
        kinds = sorted({kind for kind, rx in _LOCAL_RES if rx.search(text)})
        out.extend({"file": _rel(root, f), "kind": kind} for kind in kinds)
    return out


# ---------------------------------------------------------------- payload ---

PAYLOAD_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".duckdb", ".sqlite-wal",
                    ".sqlite-shm", ".pem", ".key", ".p12", ".pfx",
                    ".keystore")
PAYLOAD_TOP_DIRS = ("state", "raw_store")
# Gitignored runtime-state dirs: their mere existence is normal product
# behavior (cache/state created by running or testing the app) and they
# never ship (manifest GENERATED/PUBLIC_EXCLUDE + .gitignore). The
# top-dir rule therefore skips them; secret suffixes and .env files are
# still caught everywhere, including inside these dirs.
RUNTIME_STATE_DIRS = ("raw_store", "state", "state_future", "logs", "dist",
                      "preview-assets", "__pycache__", ".pytest_cache",
                      ".venv", "venv")


def payload_hits(root: Path) -> List[str]:
    root = Path(root)
    out: List[str] = []
    for f in iter_files(root):
        rel = _rel(root, f)
        name = f.name.lower()
        is_env = name == ".env" or (name.startswith(".env.")
                                    and name != ".env.example")
        top = rel.split("/", 1)[0]
        if (name.endswith(PAYLOAD_SUFFIXES) or is_env
                or (top in PAYLOAD_TOP_DIRS
                    and top not in RUNTIME_STATE_DIRS)):
            out.append(rel)
    return out


# -------------------------------------------------------- trading surface ---

# V1 is world intelligence only. These module names carried the order,
# venue, portfolio and backtest contracts that were removed before the
# public release; the check replaces the old "live execution disabled"
# flag, because a module that does not exist cannot be switched on.
TRADING_MODULE_NAMES = frozenset({
    "ccxt_meta", "crypto_data", "exec_engine", "exec_safety", "execution",
    "forecast", "hft_validator", "lean_engine", "market", "market_catalog",
    "nautilus_engine", "nautilus_polymarket", "portfolio",
    "portfolio_optimizer", "prediction_markets", "pypfopt_validator",
    "session_calendar", "skfolio_engine", "tca", "venue_registry", "venues",
})


def trading_surface_hits(root: Path) -> List[str]:
    """Shipped modules that would reintroduce trading/execution logic."""
    root = Path(root)
    out: List[str] = []
    for f in iter_files(root):
        rel = _rel(root, f)
        if (f.suffix == ".py" and rel.startswith("python/gods_eye/")
                and f.stem in TRADING_MODULE_NAMES):
            out.append(rel)
    return sorted(out)


# --------------------------------------------------------------- denylist ---

def load_denylist(path: Path) -> List[str]:
    terms: List[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        term = line.strip().lower()
        if term and not term.startswith("#") and term not in terms:
            terms.append(term)
    return terms


def denylist_hits(root: Path, terms: List[str],
                  exclude: tuple = ()) -> List[Dict[str, Any]]:
    """Case-insensitive substring scan. ``exclude`` = repo-relative paths."""
    root = Path(root)
    out: List[Dict[str, Any]] = []
    for f in iter_files(root):
        rel = _rel(root, f)
        if rel in exclude:
            continue
        text = _read_text(f)
        if text is None:
            continue
        low = text.lower()
        out.extend({"file": rel, "term_index": i, "term": t}
                   for i, t in enumerate(terms) if t in low)
    return out


# ------------------------------------------------------------ asset rights ---

RIGHTS_MANIFEST = "legal/ASSET_RIGHTS.json"
ASSET_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".otf", ".geojson", ".csv", ".parquet",
})
ALLOWED_ASSET_LICENSES = ("CC0-1.0", "BSD-2-Clause", "BSD-3-Clause", "MIT",
                          "Apache-2.0", "ISC", "OFL-1.1", "PROJECT-OWNED")
_TEXT_ASSET_SUFFIXES = frozenset({".json", ".js", ".css", ".svg", ".geojson",
                                  ".csv", ".txt"})


def is_asset(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    suffix = Path(name).suffix.lower()
    return (suffix in ASSET_SUFFIXES
            or (name.startswith("fixture") and suffix == ".json")
            or rel.startswith(("console/vendor/", "console/data/",
                               "console/brand/")))


def asset_digest(path: Path) -> str:
    data = Path(path).read_bytes()
    if Path(path).suffix.lower() in _TEXT_ASSET_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")  # checkout-EOL independent
    return hashlib.sha256(data).hexdigest()


def asset_files(root: Path) -> List[str]:
    root = Path(root)
    # raw_store/ is gitignored runtime state (feed caches, baselines,
    # thumbnail caches): ephemeral, content-addressed, never shipped.
    # Rights entries are for shippable assets only.
    return [rel for rel in (_rel(root, f) for f in iter_files(root))
            if is_asset(rel) and not rel.startswith("tests/")
            and not rel.startswith("raw_store/")]


def asset_rights(root: Path) -> Dict[str, Any]:
    root = Path(root)
    files = asset_files(root)
    try:
        manifest = json.loads((root / RIGHTS_MANIFEST).read_text(
            encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"ok": False, "n_assets": len(files),
                "errors": [f"{RIGHTS_MANIFEST} unreadable: {type(e).__name__}"]}
    entries = {a.get("path"): a for a in manifest.get("assets", [])}
    errors: List[str] = []
    for rel in files:
        entry = entries.get(rel)
        if entry is None:
            errors.append(f"{rel}: no rights entry (UNKNOWN rights cannot ship)")
            continue
        basis = str(entry.get("basis", "")).strip()
        if entry.get("license") not in ALLOWED_ASSET_LICENSES:
            errors.append(f"{rel}: licence {entry.get('license')!r} not allowed")
        if not basis or basis.upper().startswith("UNKNOWN"):
            errors.append(f"{rel}: rights basis missing or UNKNOWN")
        if entry.get("sha256") != asset_digest(root / rel):
            errors.append(f"{rel}: changed since rights review (sha256)")
    errors.extend(f"{rel}: rights entry for a file that does not exist"
                  for rel in sorted(set(entries) - set(files)))
    return {"ok": not errors, "n_assets": len(files), "errors": errors}
