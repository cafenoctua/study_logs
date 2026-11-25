"""監視デモ用: 過去28日分の擬似スナップショット(1日1点)を投入する。
--anomaly を付けると最新値に異常(行数3倍)を入れる。"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitoring"))
from db import connect  # noqa: E402

random.seed(42)
now = datetime.now(timezone.utc).replace(tzinfo=None)
series = {
    ("row_count", "analytics.fct_orders"): (10, 0.5),
    ("row_count", "analytics.dim_customers"): (5, 0.3),
    ("run_seconds", "model.sdlc_sample.fct_orders"): (0.05, 0.01),
}
with connect() as con:
    con.execute("delete from ops.metric_snapshots where captured_at < ?", [now - timedelta(minutes=5)])
    for (metric, target), (mu, sd) in series.items():
        for d in range(28, 0, -1):
            con.execute("insert into ops.metric_snapshots values (?,?,?,?)",
                        [now - timedelta(days=d), metric, target, max(0.0, random.gauss(mu, sd))])
    if "--anomaly" in sys.argv:
        con.execute("insert into ops.metric_snapshots values (?,?,?,?)",
                    [now, "row_count", "analytics.fct_orders", 30.0])
print("history seeded")
