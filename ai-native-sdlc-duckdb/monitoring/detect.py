"""最新スナップショットを過去 lookback_days 日と比べて段階判定し、ops.monitor_events へ記録。

MONITOR_MODE=shadow(既定): 記録のみ
MONITOR_MODE=active        : 段階2以上で診断プロンプトを artifacts/diagnose/ に出力
                              (claude CLI があれば `claude -p` に読み取り専用で渡す)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect  # noqa: E402
from severity import classify  # noqa: E402

CONFIG = Path(__file__).with_name("metrics.yml")
OUT_DIR = ROOT / "artifacts" / "diagnose"
LABELS = {2: ["monitor:diagnose"], 3: ["monitor:propose", "needs-approval"]}


def main() -> int:
    cfg = yaml.safe_load(CONFIG.read_text())
    s = cfg["settings"]
    mode = os.environ.get("MONITOR_MODE", "shadow")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    findings = []

    with connect() as con:
        row = con.execute(
            "select git_sha from ops.deployments where status='success' order by deployed_at desc limit 1"
        ).fetchone()
        sha = row[0] if row else None

        for m in cfg["metrics"]:
            for t in m["targets"]:
                rows = con.execute(
                    """select captured_at, value from ops.metric_snapshots
                       where metric = ? and target = ? and captured_at >= ?
                       order by captured_at""",
                    [m["name"], t, now - timedelta(days=s["lookback_days"])],
                ).fetchall()
                if not rows:
                    continue
                *hist, (_, latest) = rows
                v = classify([r[1] for r in hist], latest, m["method"], m["direction"], s["min_history"])
                con.execute(
                    "insert into ops.monitor_events values (?,?,?,?,?,?,?,?,?,?)",
                    [now, m["name"], t, latest, v.baseline,
                     None if v.score in (None, float("inf")) else v.score,
                     v.stage, v.reason, mode, sha],
                )
                print(f"stage={v.stage:>2} {m['name']:<18} {t:<35} {v.reason}")
                if v.stage >= 2:
                    findings.append({"metric": m["name"], "target": t, "value": latest,
                                     "baseline": v.baseline, "stage": v.stage,
                                     "reason": v.reason, "last_deploy_sha": sha,
                                     "labels": LABELS[v.stage]})

    if mode != "active" or not findings:
        if findings:
            print(f"shadow mode: {len(findings)} finding(s) recorded, no diagnosis")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt = (Path(__file__).with_name("diagnose_prompt.md").read_text()
              + "\n\n## findings\n```json\n" + json.dumps(findings, ensure_ascii=False, indent=2, default=str) + "\n```\n")
    path = OUT_DIR / f"{now:%Y%m%dT%H%M%S}.md"
    path.write_text(prompt)
    print(f"diagnosis prompt -> {path}")

    if shutil.which("claude") and os.environ.get("RUN_CLAUDE") == "1":
        # 編集系ツールは渡さない。SELECT は duckdb CLI 経由(read_only で開く)
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools",
             "Read,Grep,Bash(git log:*),Bash(git diff:*),Bash(git show:*),Bash(python scripts/run_sql.py --read-only:*)",
             "--disallowedTools", "Edit,Write,NotebookEdit"],
            capture_output=True, text=True, cwd=ROOT,
        )
        report = path.with_suffix(".report.md")
        report.write_text(result.stdout)
        print(f"diagnosis report -> {report}  (Issue 化はローカル版では手動: gh issue create -F {report})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
