"""prod.duckdb への接続ヘルパ(ops スキーマと analytics スキーマが同居)。"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PROD_DB = Path(os.environ.get("PROD_DB", ROOT / "warehouse" / "prod.duckdb"))


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    PROD_DB.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(PROD_DB), read_only=read_only)
