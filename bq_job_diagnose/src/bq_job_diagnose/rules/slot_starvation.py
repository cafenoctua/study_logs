"""スロット関連ルール（slot.starvation / slot.wait_dominant）。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity, TimelineSample
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

_STARVATION_DOC_QUOTE = (
    "Units of work that can be scheduled immediately. Providing additional "
    "slots for these units of work will accelerate the query, if no other "
    "query in the reservation needs additional slots."
)


def _is_starved(sample: TimelineSample, th: Thresholds) -> bool:
    units = sample.estimated_runnable_units
    if units is None:
        return False
    return units >= th.slot.runnable_units_threshold


def _find_longest_starved_run(
    timeline: tuple[TimelineSample, ...], th: Thresholds
) -> list[TimelineSample] | None:
    """連続した starved サンプルのうち最長の run を返す。無ければ None。"""
    best_run: list[TimelineSample] = []
    current_run: list[TimelineSample] = []

    for sample in timeline:
        if _is_starved(sample, th):
            current_run.append(sample)
            if len(current_run) > len(best_run):
                best_run = current_run
        else:
            current_run = []

    return best_run if best_run else None


@rule("slot.starvation", requires_plan=False, requires_timeline=True)
def starvation(job: Job, th: Thresholds) -> Iterable[Finding]:
    """タイムライン上でスロットが慢性的に不足している状態（starvation）を検出する。

    時系列の状態機械: estimated_runnable_units が runnable_units_threshold 以上の
    サンプルが連続する区間（run）を探し、最長の run が consecutive_samples 以上
    続いた場合に、その区間で completed_units の進捗がほぼ止まっているか
    （max_completed_growth_ratio 以下）を確認する。

    重要な注意（jobs.get 経路の構造的な限界）:
    タイムライン全サンプルの estimated_runnable_units が None の場合（jobs.get
    ベースでこのフィールドを取得できない経路など）、starvation の有無は
    構造的に評価不能である。この場合、本関数は Finding を一切生成しない
    （「問題なし」ではなく「評価不能」を意味する）。ルール関数は SkippedRule を
    直接生成する手段を持たない（run_rules の前提条件チェックのみが
    SkippedRule を生成できる）ため、この「全 None → 評価不能」の状態は
    Finding 無しという形でしか表現できない。呼び出し側（Skill 等）は
    timeline が存在するにもかかわらず starvation の Finding が一切無い場合、
    それが「健全」なのか「estimated_runnable_units が取得不能だった」のかを
    区別できないことに留意すること。
    """
    timeline = job.timeline
    if not any(sample.estimated_runnable_units is not None for sample in timeline):
        return

    run = _find_longest_starved_run(timeline, th)
    if run is None or len(run) < th.slot.consecutive_samples:
        return

    first, last = run[0], run[-1]
    start_completed = first.completed_units
    end_completed = last.completed_units
    if start_completed is None or end_completed is None:
        return

    if start_completed == 0:
        # start が 0 かつ end も 0 なら進捗ゼロ。end > 0 なら進捗あり。
        growth_ratio = 0.0 if end_completed == 0 else float("inf")
    else:
        growth_ratio = (end_completed - start_completed) / start_completed

    if growth_ratio > th.slot.max_completed_growth_ratio:
        return

    max_runnable = max(
        sample.estimated_runnable_units
        for sample in run
        if sample.estimated_runnable_units is not None
    )
    elapsed_span = last.elapsed_ms - first.elapsed_ms

    summary = (
        f"estimated_runnable_units が {th.slot.runnable_units_threshold} 以上の状態が "
        f"{len(run)} サンプル連続（{elapsed_span:,}ms）し、その間 completed_units は "
        f"{start_completed:,} から {end_completed:,} までしか進みませんでした"
    )

    yield Finding(
        rule_id="slot.starvation",
        title="スロット starvation（進捗停滞）",
        severity=Severity.WARNING,
        summary=summary,
        evidence=(
            Evidence(label="run_length", value=len(run), unit="samples"),
            Evidence(
                label="estimated_runnable_units_max",
                value=max_runnable,
                unit="units",
                threshold=th.slot.runnable_units_threshold,
            ),
            Evidence(label="completed_units_start", value=start_completed, unit="units"),
            Evidence(label="completed_units_end", value=end_completed, unit="units"),
            Evidence(label="elapsed_span", value=elapsed_span, unit="ms"),
        ),
        doc_url="https://cloud.google.com/bigquery/docs/query-plan-explanation",
        doc_quote=_STARVATION_DOC_QUOTE,
    )


@rule("slot.wait_dominant", requires_plan=True)
def wait_dominant(job: Job, th: Thresholds) -> Iterable[Finding]:
    """ステージの所要時間に占める wait 時間の割合が高い状態を検出する。"""
    for stage in job.stages:
        wait_avg = stage.wait_ms_avg
        duration_ms = stage.duration_ms
        if wait_avg is None or duration_ms is None:
            continue
        if duration_ms <= 0:
            continue

        wait_share = wait_avg / duration_ms

        if wait_share >= th.slot.wait_share_critical:
            severity = Severity.CRITICAL
        elif wait_share >= th.slot.wait_share_warning:
            severity = Severity.WARNING
        else:
            continue

        summary = (
            f"ステージ {stage.name} は所要時間 {duration_ms:,}ms のうち "
            f"平均 {wait_avg:,}ms（{wait_share:.2%}）を wait に費やしました"
        )

        yield Finding(
            rule_id="slot.wait_dominant",
            title="wait 時間が支配的なステージ",
            severity=severity,
            summary=summary,
            evidence=(
                Evidence(
                    label="wait_share",
                    value=wait_share,
                    unit="ratio",
                    stage_id=stage.id,
                    threshold=th.slot.wait_share_warning,
                ),
                Evidence(
                    label="wait_ms_avg",
                    value=wait_avg,
                    unit="ms",
                    stage_id=stage.id,
                ),
                Evidence(
                    label="duration_ms",
                    value=duration_ms,
                    unit="ms",
                    stage_id=stage.id,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url="https://cloud.google.com/bigquery/docs/query-plan-explanation",
        )
