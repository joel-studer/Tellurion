"""FUTURE-ONLY DuckDB metadata/query layer over state_future/market.

Raw stays immutable Parquet/files. DuckDB owns the *index*: dataset
catalog, snapshot/rights/quality metadata, instrument/time-range
inventory, experiment lookup. Graceful fallback when duckdb is absent
(in-memory lists; same read shapes). Never touches protected research state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "market-catalog-v1"


def duckdb_available() -> bool:
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class MarketCatalog:
    path: Path  # duckdb file under state_future/market/catalog.duckdb
    _con: Any = None
    _fallback_rows: Any = None

    @classmethod
    def open(cls, path: Path) -> "MarketCatalog":
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if duckdb_available():
            import duckdb
            con = duckdb.connect(str(path))
            con.execute(
                "CREATE TABLE IF NOT EXISTS datasets("
                "dataset_id VARCHAR, version VARCHAR, provider VARCHAR, "
                "snapshot_id VARCHAR, rights_id VARCHAR, quality VARCHAR, "
                "instruments VARCHAR, start_time VARCHAR, end_time VARCHAR, "
                "resolution VARCHAR, schema_version VARCHAR)")
            con.execute(
                "CREATE TABLE IF NOT EXISTS experiments("
                "manifest_id VARCHAR, dataset_id VARCHAR, engine VARCHAR, "
                "created_at VARCHAR)")
            return cls(path, con, None)
        return cls(path, None, {"datasets": [], "experiments": []})

    def upsert_dataset(self, row: Dict[str, Any]) -> None:
        row = dict(row)
        row.setdefault("schema_version", SCHEMA_VERSION)
        if self._con is not None:
            self._con.execute(
                "DELETE FROM datasets WHERE dataset_id=? AND version=?",
                [row.get("dataset_id"), row.get("version")])
            self._con.execute(
                "INSERT INTO datasets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [row.get("dataset_id"), row.get("version"),
                 row.get("provider"), row.get("snapshot_id"),
                 row.get("rights_id"), row.get("quality"),
                 row.get("instruments"), row.get("start_time"),
                 row.get("end_time"), row.get("resolution"),
                 row.get("schema_version")])
        else:
            tbl = self._fallback_rows["datasets"]
            tbl[:] = [r for r in tbl if not (
                r.get("dataset_id") == row.get("dataset_id")
                and r.get("version") == row.get("version"))]
            tbl.append(row)

    def list_datasets(self) -> List[Dict[str, Any]]:
        if self._con is not None:
            cols = ["dataset_id", "version", "provider", "snapshot_id",
                    "rights_id", "quality", "instruments", "start_time",
                    "end_time", "resolution", "schema_version"]
            rows = self._con.execute(
                "SELECT * FROM datasets ORDER BY dataset_id, version").fetchall()
            return [dict(zip(cols, r)) for r in rows]
        return list(self._fallback_rows["datasets"])

    def record_experiment(self, manifest_id: str, dataset_id: str,
                          engine: str, created_at: str = "UNKNOWN") -> None:
        if self._con is not None:
            self._con.execute("INSERT INTO experiments VALUES (?,?,?,?)",
                              [manifest_id, dataset_id, engine, created_at])
        else:
            self._fallback_rows["experiments"].append(
                {"manifest_id": manifest_id, "dataset_id": dataset_id,
                 "engine": engine, "created_at": created_at})

    def find_experiments(self, dataset_id: str) -> List[Dict[str, Any]]:
        if self._con is not None:
            rows = self._con.execute(
                "SELECT * FROM experiments WHERE dataset_id=?", [dataset_id]).fetchall()
            return [{"manifest_id": r[0], "dataset_id": r[1], "engine": r[2],
                     "created_at": r[3]} for r in rows]
        return [e for e in self._fallback_rows["experiments"]
                if e["dataset_id"] == dataset_id]

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None


def default_catalog_path(root: Optional[Path] = None) -> Path:
    from gods_eye.future.isolation import future_path
    # future_path creates parents; resolve catalog location under it.
    base = future_path("market", "catalog.duckdb")
    return base
