"""コスト試算の純粋計算モジュール（Phase 7.5）。

設計上の制約（重要）:
- このモジュールは `models` と `config` のみに依存する。I/O を行わず、
  `google`（google-cloud-bigquery 等）も import しない。`rules/` と同じ
  「純粋関数」の制約に従う（ただしこのモジュール自体はルールではない）。
- `amount` の `None` と `0.0` は意味が異なる。`None` は「試算不能」
  （必要な入力値が取得できていない）、`0.0` は「課金額が実際にゼロ」
  （キャッシュヒット等）を表す。この2つを混同しないこと。
- Editions の試算は `is_upper_bound=True` を常に付す。コミットメント割引や
  オートスケーラーの挙動をモデル化していないため、実際の請求額はこれより
  低くなりうる「上限見積」に過ぎない。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds
    from bq_job_diagnose.models import Job

_BYTES_PER_TIB = 2**40
_MS_PER_HOUR = 1000 * 3600


class BillingModel(StrEnum):
    """課金モデル。"""

    ON_DEMAND = "on_demand"
    EDITIONS = "editions"


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """1つの課金モデルに基づくコスト試算結果。

    `amount` が `None` の場合は試算不能（必要なフィールドが取得できていない）、
    `0.0` の場合は課金額が実際にゼロ（キャッシュヒット等）であることを表す。
    この区別は呼び出し側が必ず維持しなければならない。
    """

    model: BillingModel
    amount: float | None
    currency: str
    basis_value: int | None
    basis_unit: str
    unit_price: float
    price_ref: str
    edition: str | None
    unavailable_reason: str | None
    is_upper_bound: bool = False


@dataclass(frozen=True, slots=True)
class CostComparison:
    """on-demand と Editions の試算を突き合わせた結果。"""

    actual_model: BillingModel
    on_demand: CostEstimate
    editions: CostEstimate
    cheaper_model: BillingModel | None
    savings_ratio: float | None


def estimate_on_demand(job: Job, thresholds: Thresholds) -> CostEstimate:
    """オンデマンド課金でのコストを試算する。

    `total_bytes_billed / 2**40 * pricing.on_demand_price_per_tib` で計算する。

    - `job.cache_hit is True` の場合、`total_bytes_billed` の値に関わらず
      課金額は 0.0（キャッシュヒットは課金対象外）。これは「試算不能」
      （None）とは明確に区別する。
    - `total_bytes_billed is None` かつ `cache_hit` が True でない場合は
      試算不能として `amount=None` を返す。
    """
    unit_price = thresholds.pricing.on_demand_price_per_tib
    currency = thresholds.pricing.currency
    price_ref = "pricing.on_demand_price_per_tib"

    if job.cache_hit is True:
        return CostEstimate(
            model=BillingModel.ON_DEMAND,
            amount=0.0,
            currency=currency,
            basis_value=job.total_bytes_billed,
            basis_unit="bytes_billed",
            unit_price=unit_price,
            price_ref=price_ref,
            edition=None,
            unavailable_reason=None,
            is_upper_bound=False,
        )

    if job.total_bytes_billed is None:
        return CostEstimate(
            model=BillingModel.ON_DEMAND,
            amount=None,
            currency=currency,
            basis_value=None,
            basis_unit="bytes_billed",
            unit_price=unit_price,
            price_ref=price_ref,
            edition=None,
            unavailable_reason="total_bytes_billed が取得できません",
            is_upper_bound=False,
        )

    amount = (job.total_bytes_billed / _BYTES_PER_TIB) * unit_price
    return CostEstimate(
        model=BillingModel.ON_DEMAND,
        amount=amount,
        currency=currency,
        basis_value=job.total_bytes_billed,
        basis_unit="bytes_billed",
        unit_price=unit_price,
        price_ref=price_ref,
        edition=None,
        unavailable_reason=None,
        is_upper_bound=False,
    )


def _resolve_edition(job: Job, thresholds: Thresholds) -> tuple[str, float, str]:
    """Editions の試算に使う edition と単価、price_ref を決定する。

    `job.edition` が価格表に存在すればそれを使う。存在しない（None または
    未知の値）場合は `default_edition_for_estimate` にフォールバックし、
    その旨を `price_ref` に記録する。未知の edition でも例外は送出しない。
    """
    price_table = thresholds.pricing.editions_price_per_slot_hour
    default_edition = thresholds.pricing.default_edition_for_estimate

    if job.edition is not None and job.edition in price_table:
        edition = job.edition
        price_ref = f"pricing.editions_price_per_slot_hour.{edition}"
        return edition, price_table[edition], price_ref

    edition = default_edition
    price_ref = (
        f"pricing.editions_price_per_slot_hour.{edition} (default_edition_for_estimate)"
    )
    return edition, price_table[edition], price_ref


def estimate_editions(job: Job, thresholds: Thresholds) -> CostEstimate:
    """Editions 課金でのコストを試算する。

    `total_slot_ms / 1000 / 3600 * editions_price_per_slot_hour[edition]` で計算する。
    コミットメント割引やオートスケーラーの挙動は反映しないため、常に
    `is_upper_bound=True`（実際の請求額はこれより低くなりうる上限見積）。

    - `job.cache_hit is True` の場合、`total_slot_ms` の値に関わらず課金額は
      0.0。
    - `total_slot_ms is None` かつ `cache_hit` が True でない場合は試算不能
      として `amount=None` を返す。
    """
    edition, unit_price, price_ref = _resolve_edition(job, thresholds)
    currency = thresholds.pricing.currency

    if job.cache_hit is True:
        return CostEstimate(
            model=BillingModel.EDITIONS,
            amount=0.0,
            currency=currency,
            basis_value=job.total_slot_ms,
            basis_unit="slot_ms",
            unit_price=unit_price,
            price_ref=price_ref,
            edition=edition,
            unavailable_reason=None,
            is_upper_bound=True,
        )

    if job.total_slot_ms is None:
        return CostEstimate(
            model=BillingModel.EDITIONS,
            amount=None,
            currency=currency,
            basis_value=None,
            basis_unit="slot_ms",
            unit_price=unit_price,
            price_ref=price_ref,
            edition=edition,
            unavailable_reason="total_slot_ms が取得できません",
            is_upper_bound=True,
        )

    amount = (job.total_slot_ms / 1000 / 3600) * unit_price
    return CostEstimate(
        model=BillingModel.EDITIONS,
        amount=amount,
        currency=currency,
        basis_value=job.total_slot_ms,
        basis_unit="slot_ms",
        unit_price=unit_price,
        price_ref=price_ref,
        edition=edition,
        unavailable_reason=None,
        is_upper_bound=True,
    )


def compare(job: Job, thresholds: Thresholds) -> CostComparison:
    """on-demand と Editions の両方を試算し、比較する。

    `actual_model` はジョブが実際に使った課金モデル（`job.edition` の有無で
    判定）。`cheaper_model` / `savings_ratio` は、どちらかの試算額が None の
    場合、または両方が 0.0（比較しても意味がない）の場合は None にする。
    """
    on_demand = estimate_on_demand(job, thresholds)
    editions = estimate_editions(job, thresholds)

    actual_model = BillingModel.EDITIONS if job.edition is not None else BillingModel.ON_DEMAND

    cheaper_model: BillingModel | None = None
    savings_ratio: float | None = None

    if on_demand.amount is not None and editions.amount is not None:
        if on_demand.amount == 0.0 and editions.amount == 0.0:
            cheaper_model = None
            savings_ratio = None
        elif on_demand.amount < editions.amount:
            cheaper_model = BillingModel.ON_DEMAND
            higher, lower = editions.amount, on_demand.amount
            savings_ratio = (higher - lower) / higher
        elif editions.amount < on_demand.amount:
            cheaper_model = BillingModel.EDITIONS
            higher, lower = on_demand.amount, editions.amount
            savings_ratio = (higher - lower) / higher
        else:
            # 金額が等しい（0.0 同士以外のケースも含む）場合は
            # どちらが安いとも言えないため None のまま。
            cheaper_model = None
            savings_ratio = 0.0

    return CostComparison(
        actual_model=actual_model,
        on_demand=on_demand,
        editions=editions,
        cheaper_model=cheaper_model,
        savings_ratio=savings_ratio,
    )
