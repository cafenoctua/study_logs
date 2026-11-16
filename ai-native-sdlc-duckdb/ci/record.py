"""ops.deployments / ops.ci_runs に1行記録する。
usage: python ci/record.py deployment <sha> <approver> <status>
       python ci/record.py ci_run <sha> <pr> <attempt> <status>"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitoring"))
from db import connect  # noqa: E402

kind, *a = sys.argv[1:]
now = datetime.now(timezone.utc).replace(tzinfo=None)
with connect() as con:
    if kind == "deployment":
        con.execute("insert into ops.deployments values (?,?,?,?)", [now, *a])
    elif kind == "ci_run":
        con.execute("insert into ops.ci_runs values (?,?,?,?,?)", [now, a[0], a[1], int(a[2]), a[3]])
    else:
        raise SystemExit(f"unknown kind {kind}")
print(f"recorded {kind}: {a}")
