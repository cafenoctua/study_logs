"""コストルール（cost.on_demand_bytes / cost.editions_slot_time / cost.model_mismatch）。

いずれもジョブレベルのフィールド（total_bytes_billed / total_slot_ms / edition）
のみで判定できるため `requires_plan=False`（プランやタイムラインが無い
ジョブでも実行できる）。

コスト試算そのものは `bq_job_diagnose.cost`（純粋計算モジュール）に委譲する。
ここでは試算結果を閾値と突き合わせて Finding に変換する薄いレイヤーに徹する。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.cost import (
    CostEstimate,
    compare,
    estimate_editions,
    estimate_on_demand,
)
from bq_job_diagnose.models import Evidence, Finding, Job, Severity
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds


def _cost_evidence(estimate: CostEstimate) -> tuple[Evidence, ...]:
    """CostEstimate から Evidence タプルを組み立てる。

    金額そのものだけでなく、根拠となった生値（basis_value/basis_unit）と
    単価・その出典（unit_price/price_ref）を必ず含める。
    """
    return (
        Evidence(label="amount", value=estimate.amount, unit=estimate.currency),
        Evidence(
            label="basis_value",
            value=estimate.basis_value if estimate.basis_value is not None else 0,
            unit=estimate.basis_unit,
        ),
        Evidence(label="unit_price", value=estimate.unit_price, unit=estimate.price_ref),
    )



def _fmt_amount(amount: float) -> str:
    """金額を桁に応じた精度で整形する。

    BigQuery のコストは 1 クエリ $0.0008 から日次バッチ $600 まで
    5 桁以上またがる。固定の %.2f だと小さい金額が全て "0.00" に潰れ、
    「無料」という誤読を生む。特に model_mismatch は「98.9% 低い」と
    言いながら両方 0.00 と表示すると、比率と絶対値が矛盾して見える。
    """
    if amount == 0:
        return "0.00"
    if amount < 0.01:
        return f"{amount:.6f}"
    if amount < 1:
        return f"{amount:.4f}"
    return f"{amount:,.2f}"

@rule("cost.on_demand_bytes", requires_plan=False)
def on_demand_bytes(job: Job, th: Thresholds) -> Iterable[Finding]:
    """オンデマンド課金換算のコストが閾値を超えていないか検証する。

    `amount is None`（試算不能）の場合はスキップする。0.0（課金ゼロ）は
    閾値未満として自然に無検出になる。
    """
    estimate = estimate_on_demand(job, th)
    if estimate.amount is None:
        return

    if estimate.amount >= th.cost.on_demand_amount_critical:
        severity = Severity.CRITICAL
    elif estimate.amount >= th.cost.on_demand_amount_warning:
        severity = Severity.WARNING
    else:
        return

    summary = (
        f"オンデマンド課金換算で {_fmt_amount(estimate.amount)} {estimate.currency} "
        f"（{estimate.basis_value:,} {estimate.basis_unit}、単価 {estimate.unit_price} "
        f"{estimate.currency}/TiB）"
    )

    yield Finding(
        rule_id="cost.on_demand_bytes",
        title="高額なオンデマンド課金換算コスト",
        severity=severity,
        summary=summary,
        evidence=_cost_evidence(estimate),
    )


@rule("cost.editions_slot_time", requires_plan=False)
def editions_slot_time(job: Job, th: Thresholds) -> Iterable[Finding]:
    """Editions 課金換算のコストが閾値を超えていないか検証する。

    `amount is None`（試算不能）の場合はスキップする。
    """
    estimate = estimate_editions(job, th)
    if estimate.amount is None:
        return

    if estimate.amount >= th.cost.editions_amount_critical:
        severity = Severity.CRITICAL
    elif estimate.amount >= th.cost.editions_amount_warning:
        severity = Severity.WARNING
    else:
        return

    summary = (
        f"Editions（{estimate.edition}）課金換算で {_fmt_amount(estimate.amount)} {estimate.currency} "
        f"（{estimate.basis_value:,} {estimate.basis_unit}、単価 {estimate.unit_price} "
        f"{estimate.currency}/slot-hour、コミットメント割引未反映の上限見積）"
    )

    yield Finding(
        rule_id="cost.editions_slot_time",
        title="高額な Editions 課金換算コスト",
        severity=severity,
        summary=summary,
        evidence=_cost_evidence(estimate),
    )


@rule("cost.model_mismatch", requires_plan=False)
def model_mismatch(job: Job, th: Thresholds) -> Iterable[Finding]:
    """実際の課金モデルより安価なモデルがあるかどうかを検証する。

    `savings_ratio >= th.cost.model_mismatch_savings_ratio` かつ
    `cheaper_model != actual_model` の場合のみ発火する。単発ジョブの試算
    からリザベーション設計を断定するのは飛躍のため、`confidence="medium"`
    を必ず付す（最終判断は Skill 側の責務）。
    """
    comparison = compare(job, th)

    if comparison.savings_ratio is None or comparison.cheaper_model is None:
        return
    if comparison.cheaper_model == comparison.actual_model:
        return
    if comparison.savings_ratio < th.cost.model_mismatch_savings_ratio:
        return

    on_demand = comparison.on_demand
    editions = comparison.editions
    summary = (
        f"実際の課金モデルは {comparison.actual_model.value}。"
        f"オンデマンド換算 {_fmt_amount(on_demand.amount)} {on_demand.currency}、"
        f"Editions 換算 {_fmt_amount(editions.amount)} {editions.currency}"
        f"（{comparison.cheaper_model.value} が {comparison.savings_ratio:.1%} 低い）"
    )

    yield Finding(
        rule_id="cost.model_mismatch",
        title="課金モデル間の試算額の差異",
        severity=Severity.WARNING,
        summary=summary,
        evidence=(
            Evidence(
                label="on_demand_amount",
                value=on_demand.amount,
                unit=on_demand.currency,
            ),
            Evidence(
                label="editions_amount",
                value=editions.amount,
                unit=editions.currency,
            ),
            Evidence(
                label="savings_ratio",
                value=comparison.savings_ratio,
                unit="ratio",
                threshold=th.cost.model_mismatch_savings_ratio,
            ),
        ),
        confidence="medium",
    )
