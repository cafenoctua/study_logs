"""cost.py（コスト試算の純粋計算モジュール）のテスト。

TDD: このテストを先に書き、失敗することを確認してから cost.py を実装する。

方針: 期待値は実装のロジックをなぞるのではなく、テスト側で手計算した
リテラル値と比較する（実装のコピーになるとバグを検出できないため）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.cost import (
    BillingModel,
    compare,
    estimate_editions,
    estimate_on_demand,
)
from tests.builders import make_job

TH = load_thresholds()


class TestEstimateOnDemand:
    def test_known_bytes_produces_exact_amount(self):
        # 1 TiB ちょうど分を課金 → 単価そのものが金額になる
        one_tib = 2**40
        job = make_job(total_bytes_billed=one_tib, edition=None)
        est = estimate_on_demand(job, TH)
        assert est.model is BillingModel.ON_DEMAND
        assert est.amount == pytest.approx(6.25)
        assert est.amount is not None
        assert est.currency == "USD"
        assert est.basis_value == one_tib
        assert est.basis_unit == "bytes_billed"
        assert est.unit_price == pytest.approx(6.25)
        assert est.price_ref == "pricing.on_demand_price_per_tib"
        assert est.unavailable_reason is None
        assert est.is_upper_bound is False

    def test_half_tib_produces_half_price(self):
        half_tib = 2**39
        job = make_job(total_bytes_billed=half_tib)
        est = estimate_on_demand(job, TH)
        # 手計算: 0.5 TiB * $6.25/TiB = $3.125
        assert est.amount == pytest.approx(3.125)

    def test_arbitrary_bytes_matches_hand_computed_value(self):
        # 手計算: 123_456_789_012 bytes / 2**40 TiB * $6.25/TiB
        billed = 123_456_789_012
        job = make_job(total_bytes_billed=billed)
        est = estimate_on_demand(job, TH)
        expected = 0.7017705969019516  # (123456789012 / 1099511627776) * 6.25
        assert est.amount == pytest.approx(expected, rel=1e-9)

    def test_none_bytes_billed_gives_unavailable(self):
        job = make_job(total_bytes_billed=None, cache_hit=False)
        est = estimate_on_demand(job, TH)
        assert est.amount is None
        assert est.unavailable_reason is not None
        assert "total_bytes_billed" in est.unavailable_reason

    def test_cache_hit_true_gives_zero_not_none_even_with_bytes(self):
        job = make_job(total_bytes_billed=999_999_999, cache_hit=True)
        est = estimate_on_demand(job, TH)
        assert est.amount == 0.0
        assert est.amount is not None
        assert est.unavailable_reason is None

    def test_cache_hit_true_gives_zero_even_with_none_bytes(self):
        job = make_job(total_bytes_billed=None, cache_hit=True)
        est = estimate_on_demand(job, TH)
        assert est.amount == 0.0
        assert est.amount is not None

    def test_cache_hit_true_gives_zero_even_with_zero_bytes(self):
        job = make_job(total_bytes_billed=0, cache_hit=True)
        est = estimate_on_demand(job, TH)
        assert est.amount == 0.0

    def test_price_comes_from_yaml_not_constant(self, tmp_path: Path):
        one_tib = 2**40
        job = make_job(total_bytes_billed=one_tib)
        override = tmp_path / "override.yaml"
        override.write_text(
            "version: 1\npricing:\n  on_demand_price_per_tib: 12.5\n",
            encoding="utf-8",
        )
        th_override = load_thresholds(override)
        est_default = estimate_on_demand(job, TH)
        est_override = estimate_on_demand(job, th_override)
        assert est_default.amount == pytest.approx(6.25)
        assert est_override.amount == pytest.approx(12.5)
        assert est_default.amount != est_override.amount


class TestEstimateEditions:
    def test_known_slot_ms_with_explicit_edition_matches_hand_computed(self):
        # 1 時間分の STANDARD スロット (3600 * 1000 slot_ms)
        job = make_job(total_slot_ms=3_600_000, edition="STANDARD")
        est = estimate_editions(job, TH)
        assert est.model is BillingModel.EDITIONS
        # 手計算: 3_600_000 / 1000 / 3600 = 1.0 時間 * $0.04/時間 = $0.04
        assert est.amount == pytest.approx(0.04)
        assert est.basis_value == 3_600_000
        assert est.basis_unit == "slot_ms"
        assert est.unit_price == pytest.approx(0.04)
        assert est.price_ref == "pricing.editions_price_per_slot_hour.STANDARD"
        assert est.edition == "STANDARD"
        assert est.is_upper_bound is True
        assert est.unavailable_reason is None

    def test_arbitrary_slot_ms_matches_hand_computed_value(self):
        slot_ms = 7_200_500
        job = make_job(total_slot_ms=slot_ms, edition="ENTERPRISE_PLUS")
        est = estimate_editions(job, TH)
        # 手計算: 7200500 / 1000 / 3600 hours * 0.10 $/hour
        expected = (7200500 / 1000 / 3600) * 0.10
        assert est.amount == pytest.approx(expected, rel=1e-9)

    def test_no_edition_falls_back_to_default_for_estimate(self):
        job = make_job(total_slot_ms=3_600_000, edition=None)
        est = estimate_editions(job, TH)
        assert est.edition == TH.pricing.default_edition_for_estimate
        assert est.amount == pytest.approx(0.06)  # ENTERPRISE default
        assert "default_edition_for_estimate" in est.price_ref

    def test_unknown_edition_falls_back_to_default_and_records_it(self):
        job = make_job(total_slot_ms=3_600_000, edition="NONEXISTENT_EDITION")
        est = estimate_editions(job, TH)
        # 未知の edition は例外を投げずデフォルトにフォールバック
        assert est.edition == TH.pricing.default_edition_for_estimate
        assert est.amount == pytest.approx(0.06)
        assert "default_edition_for_estimate" in est.price_ref
        assert TH.pricing.default_edition_for_estimate in est.price_ref

    def test_none_slot_ms_gives_unavailable(self):
        job = make_job(total_slot_ms=None, cache_hit=False)
        est = estimate_editions(job, TH)
        assert est.amount is None
        assert est.unavailable_reason is not None
        assert "total_slot_ms" in est.unavailable_reason

    def test_cache_hit_true_gives_zero_not_none(self):
        job = make_job(total_slot_ms=999_999, cache_hit=True)
        est = estimate_editions(job, TH)
        assert est.amount == 0.0
        assert est.amount is not None

    def test_cache_hit_true_gives_zero_even_with_none_slot_ms(self):
        job = make_job(total_slot_ms=None, cache_hit=True)
        est = estimate_editions(job, TH)
        assert est.amount == 0.0

    def test_always_upper_bound(self):
        job = make_job(total_slot_ms=1000, edition="STANDARD")
        est = estimate_editions(job, TH)
        assert est.is_upper_bound is True

    def test_price_comes_from_yaml_not_constant(self, tmp_path: Path):
        job = make_job(total_slot_ms=3_600_000, edition="STANDARD")
        override = tmp_path / "override.yaml"
        override.write_text(
            "version: 1\npricing:\n"
            "  editions_price_per_slot_hour:\n"
            "    STANDARD: 1.0\n"
            "    ENTERPRISE: 0.06\n"
            "    ENTERPRISE_PLUS: 0.10\n",
            encoding="utf-8",
        )
        th_override = load_thresholds(override)
        est_default = estimate_editions(job, TH)
        est_override = estimate_editions(job, th_override)
        assert est_default.amount == pytest.approx(0.04)
        assert est_override.amount == pytest.approx(1.0)


class TestCompare:
    def test_actual_model_is_editions_when_edition_set(self):
        job = make_job(
            edition="STANDARD",
            total_slot_ms=3_600_000,
            total_bytes_billed=2**40,
        )
        cmp = compare(job, TH)
        assert cmp.actual_model is BillingModel.EDITIONS

    def test_actual_model_is_on_demand_when_edition_none(self):
        job = make_job(edition=None, total_bytes_billed=2**40, total_slot_ms=1000)
        cmp = compare(job, TH)
        assert cmp.actual_model is BillingModel.ON_DEMAND

    def test_cheaper_model_and_savings_ratio_hand_computed(self):
        # on-demand: 1 TiB -> $6.25
        # editions (STANDARD, 1h): $0.04
        # editions is cheaper. ratio = (6.25 - 0.04) / 6.25
        job = make_job(
            edition="STANDARD",
            total_bytes_billed=2**40,
            total_slot_ms=3_600_000,
        )
        cmp = compare(job, TH)
        assert cmp.on_demand.amount == pytest.approx(6.25)
        assert cmp.editions.amount == pytest.approx(0.04)
        assert cmp.cheaper_model is BillingModel.EDITIONS
        expected_ratio = (6.25 - 0.04) / 6.25
        assert cmp.savings_ratio == pytest.approx(expected_ratio, rel=1e-9)

    def test_either_amount_none_gives_none_comparison(self):
        job = make_job(total_bytes_billed=None, total_slot_ms=3_600_000, cache_hit=False)
        cmp = compare(job, TH)
        assert cmp.on_demand.amount is None
        assert cmp.cheaper_model is None
        assert cmp.savings_ratio is None

    def test_both_zero_no_crash_cheaper_model_none(self):
        job = make_job(cache_hit=True, total_bytes_billed=0, total_slot_ms=0)
        cmp = compare(job, TH)
        assert cmp.on_demand.amount == 0.0
        assert cmp.editions.amount == 0.0
        assert cmp.cheaper_model is None
        assert cmp.savings_ratio is None

    def test_worked_example_for_manual_sanity_check(self):
        """レポート用のサンプル: compare() の出力を手計算で検算する。"""
        job = make_job(
            edition="ENTERPRISE",
            total_bytes_billed=5 * 2**40,  # 5 TiB
            total_slot_ms=10 * 3_600_000,  # 10 時間分
        )
        cmp = compare(job, TH)
        # on-demand: 5 TiB * $6.25/TiB = $31.25
        assert cmp.on_demand.amount == pytest.approx(31.25)
        # editions ENTERPRISE: 10h * $0.06/h = $0.60
        assert cmp.editions.amount == pytest.approx(0.60)
        assert cmp.actual_model is BillingModel.EDITIONS
        assert cmp.cheaper_model is BillingModel.EDITIONS
        expected_ratio = (31.25 - 0.60) / 31.25
        assert cmp.savings_ratio == pytest.approx(expected_ratio, rel=1e-9)
