"""prod.duckdb に SQL を流す。--read-only なら読み取り専用接続(診断用。SELECT 以外は DuckDB が拒否)。

usage: python scripts/run_sql.py [--read-only] <file.sql | "select ...">
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitoring"))
from db import connect  # noqa: E402

args = sys.argv[1:]
ro = "--read-only" in args
args = [a for a in args if a != "--read-only"]
sql = Path(args[0]).read_text() if args[0].endswith(".sql") else args[0]
with connect(read_only=ro) as con:
    rel = con.sql(sql)
    if rel is not None:
        rel.show(max_rows=100)
