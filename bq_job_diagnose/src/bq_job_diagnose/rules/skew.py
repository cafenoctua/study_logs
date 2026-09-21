"""スキュー検出ルール（skew.compute_time）。

ステージ内のワーカー間で compute 時間に偏りがある場合を検出する。
`Stage.compute_skew_ratio`（= compute_ms_max / compute_ms_avg）のみを使う。
BigQuery の比率フィールド（compute_ratio_*）はクエリ全体基準で正規化されており
ステージ内偏りを表さないため、意図的に使わない（models.py の設計意図参照）。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

_DOC_URL = "https://cloud.google.com/bigquery/docs/query-plan-explanation"
_DOC_QUOTE = (
    "for stages where the compute maximum is significantly higher than the "
    "compute average, this indicates that the stage spent a disproportionate "
    "amount of time processing a few slices of data"
)


@rule("skew.compute_time", requires_plan=True)
def compute_time(job: Job, th: Thresholds) -> Iterable[Finding]:
    """ステージ内 compute 時間のワーカー間スキューを検出する。

    ガード:
    - compute_ms_avg / compute_ms_max / compute_skew_ratio のいずれかが
      None なら対象外（取得不能を 0 として扱わない）。
    - duration_ms が取得できていて min_stage_duration_ms 未満の短時間ステージは
      比率が不安定になりやすいためスキップする。
    - compute_ms_max が min_compute_ms_max 未満なら、比率が高くても絶対的な
      実害が小さいノイズとみなしスキップする。
    - duration_ms が取得できていて 0 より大きい場合のみ、compute が
      ステージの支配的コストか（compute_ms_max / duration_ms が
      min_compute_share_of_stage 以上か）を確認する。取得できなければこの
      ガードは適用しない（判定を継続する）。
    """
    for stage in job.stages:
        avg = stage.compute_ms_avg
        max_ = stage.compute_ms_max
        ratio = stage.compute_skew_ratio
        if avg is None or max_ is None or ratio is None:
            continue

        duration_ms = stage.duration_ms
        if duration_ms is not None and duration_ms < th.global_.min_stage_duration_ms:
            continue

        if max_ < th.skew.min_compute_ms_max:
            continue

        if duration_ms is not None and duration_ms > 0:
            compute_share = max_ / duration_ms
            if compute_share < th.skew.min_compute_share_of_stage:
                continue

        if ratio >= th.skew.ratio_critical:
            severity = Severity.CRITICAL
        elif ratio >= th.skew.ratio_warning:
            severity = Severity.WARNING
        else:
            continue

        summary = (
            f"ステージ {stage.name} は compute_ms の最大値が平均値の "
            f"{ratio:.2f} 倍（平均 {avg:,}ms、最大 {max_:,}ms）"
        )

        yield Finding(
            rule_id="skew.compute_time",
            title="ステージ内 compute 時間のスキュー",
            severity=severity,
            summary=summary,
            evidence=(
                Evidence(
                    label="compute_skew_ratio",
                    value=ratio,
                    unit="ratio",
                    stage_id=stage.id,
                    threshold=th.skew.ratio_warning,
                ),
                Evidence(
                    label="compute_ms_avg",
                    value=avg,
                    unit="ms",
                    stage_id=stage.id,
                ),
                Evidence(
                    label="compute_ms_max",
                    value=max_,
                    unit="ms",
                    stage_id=stage.id,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url=_DOC_URL,
            doc_quote=_DOC_QUOTE,
        )
