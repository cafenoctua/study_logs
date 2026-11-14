"""target/run_results.json を ops.dbt_run_results に保存する。
usage: python ci/upload_run_results.py <ci|prod> [git_sha]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitoring"))
from db import ROOT, connect  # noqa: E402

target = sys.argv[1]
sha = sys.argv[2] if len(sys.argv) > 2 else None
rr = json.loads((ROOT / "target" / "run_results.json").read_text())
meta = rr["metadata"]
rows = [(meta["invocation_id"], target, sha, r["unique_id"], r["status"], r["execution_time"],
         meta["generated_at"].replace("Z", "")) for r in rr["results"]]
if not rows:
    print(f"no run results ({target})")
    raise SystemExit(0)
with connect() as con:
    con.executemany("insert into ops.dbt_run_results values (?,?,?,?,?,?,?)", rows)
print(f"uploaded {len(rows)} run results ({target})")
