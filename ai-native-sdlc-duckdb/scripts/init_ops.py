"""warehouse/prod.duckdb に ops スキーマとテーブルを作る(冪等)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitoring"))
from db import ROOT, connect  # noqa: E402

with connect() as con:
    con.execute((ROOT / "monitoring/sql/ops_tables.sql").read_text())
print("ops schema ready")
