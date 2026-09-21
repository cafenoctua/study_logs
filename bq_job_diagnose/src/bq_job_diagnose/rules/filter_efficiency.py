"""フィルタ効率ルール（filter.low_efficiency）。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

_DOC_QUOTE = (
    "Scan of a large table with a small filter ratio: this suggests that "
    "the filter isn't effectively reducing the data scanned"
)


def _has_read_step(stage) -> bool:
    return any(step.kind == "READ" for step in stage.steps)


@rule("filter.low_efficiency", requires_plan=True)
def low_efficiency(job: Job, th: Thresholds) -> Iterable[Finding]:
    """READ ステップを含むステージのフィルタ効率（records_written / records_read）を検証する。

    ガード:
    - READ ステップを含まないステージは対象外。
    - records_read / records_written のいずれかが None なら対象外
      （取得不能を 0 として扱わない）。
    - records_read が min_records_read 未満なら、小さいテーブルの
      フルスキャンとみなしスキップする。
    - records_read が 0 ならゼロ除算を避けるためスキップする
      （0 は「読み込み0件」であり、この量では効率評価に意味がない）。
    """
    for stage in job.stages:
        if not _has_read_step(stage):
            continue

        records_read = stage.records_read
        records_written = stage.records_written
        if records_read is None or records_written is None:
            continue
        if records_read < th.filter.min_records_read:
            continue
        if records_read == 0:
            continue

        efficiency = records_written / records_read

        if efficiency <= th.filter.efficiency_critical:
            severity = Severity.CRITICAL
        elif efficiency <= th.filter.efficiency_warning:
            severity = Severity.WARNING
        else:
            continue

        summary = (
            f"ステージ {stage.name} は {records_read:,} 行読み込み "
            f"{records_written:,} 行を出力（フィルタ効率 {efficiency:.4f}）"
        )

        yield Finding(
            rule_id="filter.low_efficiency",
            title="低いフィルタ効率",
            severity=severity,
            summary=summary,
            evidence=(
                Evidence(
                    label="filter_efficiency",
                    value=efficiency,
                    unit="ratio",
                    stage_id=stage.id,
                    threshold=th.filter.efficiency_warning,
                ),
                Evidence(
                    label="records_read",
                    value=records_read,
                    unit="rows",
                    stage_id=stage.id,
                ),
                Evidence(
                    label="records_written",
                    value=records_written,
                    unit="rows",
                    stage_id=stage.id,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url="https://cloud.google.com/bigquery/docs/query-plan-explanation",
            doc_quote=_DOC_QUOTE,
        )
