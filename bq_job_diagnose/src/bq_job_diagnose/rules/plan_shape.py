"""プラン形状ルール（plan_shape.repartition_repeat / plan_shape.coalesce_repeat）。

REPARTITION / COALESCE ステップはクエリプランに単発で現れる分には BigQuery が
自動挿入する正常な形状であり、問題を意味しない。これらが**繰り返し**出現する
（対象ステップを含むステージが複数ある）場合にのみ、データ分布の不安定さや
過剰なシャッフルの兆候とみなす。単発の出現では Finding を生成しない。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity, Stage
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

_DOC_URL = "https://cloud.google.com/bigquery/docs/query-plan-explanation"
_DOC_QUOTE = (
    "If you see REPARTITION or COALESCE steps in your query plan, it doesn't "
    "necessarily mean there's a problem... However, if you see these operations "
    "repeatedly, it might indicate that your data is inherently skewed or that "
    "your query is causing excessive data shuffling."
)


def _stage_mentions(stage: Stage, marker: str) -> bool:
    for step in stage.steps:
        if marker in step.kind:
            return True
        if any(marker in substep for substep in step.substeps):
            return True
    return False


def _matching_stages(job: Job, marker: str) -> list[Stage]:
    return [stage for stage in job.stages if _stage_mentions(stage, marker)]


def _make_finding(rule_id: str, title: str, marker_label: str, stages: list[Stage]) -> Finding:
    stage_ids = tuple(stage.id for stage in stages)
    count = len(stages)
    summary = (
        f"{marker_label} を含むステージが {count} 個あります"
        f"（ステージ ID: {', '.join(str(i) for i in stage_ids)}）"
    )
    return Finding(
        rule_id=rule_id,
        title=title,
        severity=Severity.WARNING,
        summary=summary,
        evidence=(
            Evidence(
                label="stage_count",
                value=count,
                unit="stages",
            ),
        ),
        stage_ids=stage_ids,
        doc_url=_DOC_URL,
        doc_quote=_DOC_QUOTE,
    )


@rule("plan_shape.repartition_repeat", requires_plan=True)
def repartition_repeat(job: Job, th: Thresholds) -> Iterable[Finding]:
    """REPARTITION ステップを含むステージが繰り返し出現する状態を検出する。

    対象ステップを含むステージ数が repartition_min_stages 未満なら
    Finding を生成しない（単発出現は正常）。
    """
    stages = _matching_stages(job, "REPARTITION")
    if len(stages) < th.plan_shape.repartition_min_stages:
        return
    yield _make_finding(
        "plan_shape.repartition_repeat",
        "REPARTITION の繰り返し出現",
        "REPARTITION",
        stages,
    )


@rule("plan_shape.coalesce_repeat", requires_plan=True)
def coalesce_repeat(job: Job, th: Thresholds) -> Iterable[Finding]:
    """COALESCE ステップを含むステージが繰り返し出現する状態を検出する。

    対象ステップを含むステージ数が coalesce_min_stages 未満なら
    Finding を生成しない（単発出現は正常）。
    """
    stages = _matching_stages(job, "COALESCE")
    if len(stages) < th.plan_shape.coalesce_min_stages:
        return
    yield _make_finding(
        "plan_shape.coalesce_repeat",
        "COALESCE の繰り返し出現",
        "COALESCE",
        stages,
    )
