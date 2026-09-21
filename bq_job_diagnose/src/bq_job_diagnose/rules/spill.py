"""シャッフル関連ルール（shuffle.spill / shuffle.large_output）。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

_SPILL_DOC_QUOTE = (
    "Shuffle bytes spilled over to disk: this suggests that the data isn't "
    "stored effectively using optimization techniques such as clustering"
)


@rule("shuffle.spill", requires_plan=True)
def spill(job: Job, th: Thresholds) -> Iterable[Finding]:
    """シャッフル出力のディスクスピルを検出する。

    spill は BigQuery 内部の動的な最適化アルゴリズムに依存し、同じクエリでも
    再実行のたびに発生有無・量が変わりうる非決定的なシグナルのため、
    severity は常に ADVISORY とし、spill 量の大小で昇格させない
    （default_thresholds.yaml の shuffle.spill_always_advisory 参照）。
    """
    for stage in job.stages:
        spilled = stage.shuffle_output_bytes_spilled
        if spilled is None or spilled <= 0:
            continue

        is_notable = spilled >= th.shuffle.spill_bytes_notable
        notable_text = "規模の大きい" if is_notable else "小規模な"
        summary = (
            f"ステージ {stage.name} でシャッフル出力 {spilled:,} バイトが"
            f"ディスクにスピルしました（{notable_text}スピル）"
        )

        yield Finding(
            rule_id="shuffle.spill",
            title="シャッフル出力のディスクスピル",
            severity=Severity.ADVISORY,
            summary=summary,
            evidence=(
                Evidence(
                    label="shuffle_output_bytes_spilled",
                    value=spilled,
                    unit="bytes",
                    stage_id=stage.id,
                    threshold=th.shuffle.spill_bytes_notable,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url="https://cloud.google.com/bigquery/docs/query-plan-explanation",
            doc_quote=_SPILL_DOC_QUOTE,
        )


@rule("shuffle.large_output", requires_plan=True)
def large_output(job: Job, th: Thresholds) -> Iterable[Finding]:
    """シャッフル出力バイト数が大きいステージを検出する。"""
    for stage in job.stages:
        output_bytes = stage.shuffle_output_bytes
        if output_bytes is None:
            continue
        if output_bytes < th.shuffle.output_bytes_warning:
            continue

        summary = f"ステージ {stage.name} のシャッフル出力は {output_bytes:,} バイトです"

        yield Finding(
            rule_id="shuffle.large_output",
            title="大規模なシャッフル出力",
            severity=Severity.WARNING,
            summary=summary,
            evidence=(
                Evidence(
                    label="shuffle_output_bytes",
                    value=output_bytes,
                    unit="bytes",
                    stage_id=stage.id,
                    threshold=th.shuffle.output_bytes_warning,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url="https://cloud.google.com/bigquery/docs/query-plan-explanation",
        )
