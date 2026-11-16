"""metrics.yml の指標を取得して ops.metric_snapshots に追記する。"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect  # noqa: E402

CONFIG = Path(__file__).with_name("metrics.yml")


def fetch(con, metric: str, target: str) -> float | None:
    if metric == "row_count":
        return con.execute(f"select count(*) from {target}").fetchone()[0]
    if metric == "freshness_minutes":
        row = con.execute(
            "select max(deployed_at) from ops.deployments where status = 'success'"
        ).fetchone()
        if row[0] is None:
            return None
        return (datetime.now() - row[0]).total_seconds() / 60
    if metric == "run_seconds":
        row = con.execute(
            """select execution_seconds from ops.dbt_run_results
               where target = 'prod' and unique_id = ? order by generated_at desc limit 1""",
            [target],
        ).fetchone()
        return None if row is None else row[0]
    raise ValueError(metric)


def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with connect() as con:
        for m in cfg["metrics"]:
            for t in m["targets"]:
                try:
                    v = fetch(con, m["name"], t)
                except Exception as e:  # テーブル未作成など
                    print(f"skip {m['name']} {t}: {e}")
                    continue
                if v is None:
                    continue
                con.execute("insert into ops.metric_snapshots values (?, ?, ?, ?)", [now, m["name"], t, float(v)])
                print(f"collected {m['name']:<18} {t:<35} {v:.2f}")


if __name__ == "__main__":
    main()
