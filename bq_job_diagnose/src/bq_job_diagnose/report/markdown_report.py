"""JSON レポート dict から日本語 Markdown レポートを生成する。

`build_json_report` が返す dict（dataclass ではない）を入力に取ることで、
JSON と Markdown の2つのレンダラーが同じデータから生成され、内容が
食い違う（divergeする）ことを防ぐ。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import jinja2

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)

_SEVERITY_ORDER = ["critical", "warning", "advisory", "info"]
_SEVERITY_LABELS_JA = {
    "critical": "重大",
    "warning": "警告",
    "advisory": "参考",
    "info": "情報",
}


def _group_findings_by_severity(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """findings（既に severity→rule_id 順にソート済み）を severity ごとにグルーピングする。"""
    groups: dict[str, list[dict[str, Any]]] = {sev: [] for sev in _SEVERITY_ORDER}
    for finding in findings:
        groups.setdefault(finding["severity"], []).append(finding)

    result = []
    for sev in _SEVERITY_ORDER:
        items = groups.get(sev, [])
        if not items:
            continue
        result.append(
            {"severity": sev, "label": _SEVERITY_LABELS_JA.get(sev, sev), "findings": items}
        )
    return result


def _compute_elapsed_ms(job_dict: dict[str, Any]) -> int | None:
    """`start_time` / `end_time`（ISO8601 文字列）から経過時間（ミリ秒）を計算する。

    `Job.elapsed_ms` は dataclass のフィールドではなくプロパティのため
    JSON レポートには含まれない。Markdown 表示用にここで計算し直す。
    """
    start_raw = job_dict.get("start_time")
    end_raw = job_dict.get("end_time")
    if start_raw is None or end_raw is None:
        return None
    start = datetime.fromisoformat(start_raw)
    end = datetime.fromisoformat(end_raw)
    return int((end - start).total_seconds() * 1000)



def _fmt_amount(amount: float | None) -> str:
    """金額を桁に応じた精度で整形する。

    BigQuery のコストは 1 クエリ $0.0000027 から日次バッチ $600 まで
    桁が大きくまたがる。固定の %.4f だと小さい金額が "0.0000" に潰れ、
    「課金ゼロ」と誤読される（実データで実際に発生した）。
    """
    if amount is None:
        return "-"
    if amount == 0:
        return "0.00"
    if amount < 0.000001:
        return f"{amount:.2e}"
    if amount < 0.01:
        return f"{amount:.6f}"
    if amount < 1:
        return f"{amount:.4f}"
    return f"{amount:,.2f}"

def build_markdown_report(report: dict[str, Any]) -> str:
    """`build_json_report` の戻り値（dict）から日本語 Markdown レポート文字列を生成する。"""
    _env.filters["fmt_amount"] = _fmt_amount
    template = _env.get_template("report.md.j2")

    jobs = []
    for entry in report["jobs"]:
        job_dict = {**entry["job"], "elapsed_ms": _compute_elapsed_ms(entry["job"])}
        jobs.append(
            {
                **entry,
                "job": job_dict,
                "finding_groups": _group_findings_by_severity(entry["findings"]),
            }
        )

    return template.render(
        schema_version=report["schema_version"],
        generated_at=report["generated_at"],
        config_digest=report["config_digest"],
        mode=report["mode"],
        jobs=jobs,
        scan_summary=report.get("scan_summary"),
    )
