"""rules/cost.py のテスト（cost.on_demand_bytes / cost.editions_slot_time / cost.model_mismatch）。

TDD: このテストを先に書き、失敗することを確認してから rules/cost.py を実装する。
"""

from __future__ import annotations

import math

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.cost import (
    editions_slot_time,
    model_mismatch,
    on_demand_bytes,
)
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job

TH = load_thresholds()

_TIB = 2**40
_HOUR_SLOT_MS = 1000 * 3600


class TestOnDemandBytesRule:
    def test_below_warning_no_finding(self):
        # warning は $6.0。それより十分小さい額にする。
        bytes_billed = int((TH.cost.on_demand_amount_warning * 0.5 / TH.pricing.on_demand_price_per_tib) * _TIB)
        job = make_job(total_bytes_billed=bytes_billed, edition=None)
        assert list(on_demand_bytes(job, TH)) == []

    def test_at_warning_fires_warning(self):
        bytes_billed = math.ceil(
            (TH.cost.on_demand_amount_warning / TH.pricing.on_demand_price_per_tib) * _TIB
        )
        job = make_job(total_bytes_billed=bytes_billed, edition=None)
        findings = list(on_demand_bytes(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_at_critical_fires_critical(self):
        bytes_billed = math.ceil(
            (TH.cost.on_demand_amount_critical / TH.pricing.on_demand_price_per_tib) * _TIB
        )
        job = make_job(total_bytes_billed=bytes_billed, edition=None)
        findings = list(on_demand_bytes(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_amount_none_is_skipped_no_crash(self):
        job = make_job(total_bytes_billed=None, cache_hit=False)
        assert list(on_demand_bytes(job, TH)) == []

    def test_cache_hit_zero_amount_no_finding(self):
        job = make_job(total_bytes_billed=999_999_999_999, cache_hit=True)
        assert list(on_demand_bytes(job, TH)) == []

    def test_evidence_has_amount_basis_and_unit_price(self):
        bytes_billed = int(
            (TH.cost.on_demand_amount_critical / TH.pricing.on_demand_price_per_tib) * _TIB
        )
        job = make_job(total_bytes_billed=bytes_billed, edition=None)
        f = next(iter(on_demand_bytes(job, TH)))
        labels = {e.label for e in f.evidence}
        assert "amount" in labels
        assert "basis_value" in labels
        assert "unit_price" in labels
        price_ref_evidence = next(e for e in f.evidence if e.label == "unit_price")
        assert price_ref_evidence.unit == "pricing.on_demand_price_per_tib"

    def test_summary_has_no_suggestion_words(self):
        bytes_billed = int(
            (TH.cost.on_demand_amount_critical / TH.pricing.on_demand_price_per_tib) * _TIB
        )
        job = make_job(total_bytes_billed=bytes_billed, edition=None)
        for f in on_demand_bytes(job, TH):
            assert_no_suggestion_words(f)


class TestEditionsSlotTimeRule:
    def test_below_warning_no_finding(self):
        price = TH.pricing.editions_price_per_slot_hour["STANDARD"]
        slot_ms = int((TH.cost.editions_amount_warning * 0.5 / price) * _HOUR_SLOT_MS)
        job = make_job(total_slot_ms=slot_ms, edition="STANDARD")
        assert list(editions_slot_time(job, TH)) == []

    def test_at_warning_fires_warning(self):
        price = TH.pricing.editions_price_per_slot_hour["STANDARD"]
        slot_ms = math.ceil((TH.cost.editions_amount_warning / price) * _HOUR_SLOT_MS)
        job = make_job(total_slot_ms=slot_ms, edition="STANDARD")
        findings = list(editions_slot_time(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_at_critical_fires_critical(self):
        price = TH.pricing.editions_price_per_slot_hour["STANDARD"]
        slot_ms = math.ceil((TH.cost.editions_amount_critical / price) * _HOUR_SLOT_MS)
        job = make_job(total_slot_ms=slot_ms, edition="STANDARD")
        findings = list(editions_slot_time(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_amount_none_is_skipped_no_crash(self):
        job = make_job(total_slot_ms=None, cache_hit=False, edition="STANDARD")
        assert list(editions_slot_time(job, TH)) == []

    def test_cache_hit_zero_amount_no_finding(self):
        job = make_job(total_slot_ms=999_999_999, cache_hit=True, edition="STANDARD")
        assert list(editions_slot_time(job, TH)) == []

    def test_evidence_has_amount_basis_and_unit_price(self):
        price = TH.pricing.editions_price_per_slot_hour["STANDARD"]
        slot_ms = int((TH.cost.editions_amount_critical / price) * _HOUR_SLOT_MS)
        job = make_job(total_slot_ms=slot_ms, edition="STANDARD")
        f = next(iter(editions_slot_time(job, TH)))
        labels = {e.label for e in f.evidence}
        assert "amount" in labels
        assert "basis_value" in labels
        assert "unit_price" in labels

    def test_summary_has_no_suggestion_words(self):
        price = TH.pricing.editions_price_per_slot_hour["STANDARD"]
        slot_ms = int((TH.cost.editions_amount_critical / price) * _HOUR_SLOT_MS)
        job = make_job(total_slot_ms=slot_ms, edition="STANDARD")
        for f in editions_slot_time(job, TH):
            assert_no_suggestion_words(f)


class TestModelMismatchRule:
    def test_fires_when_ratio_at_threshold_and_models_differ(self):
        # actual = on_demand (edition=None). editions は大幅に安くする。
        # on_demand: 1 TiB -> $6.25. editions(STANDARD, 微小 slot_ms) -> ~0
        job = make_job(total_bytes_billed=_TIB, total_slot_ms=1, edition=None)
        findings = list(model_mismatch(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].confidence == "medium"

    def test_no_finding_when_ratio_below_threshold(self):
        # 金額をほぼ同じにして savings_ratio を小さくする。
        # on_demand と editions がほぼ同額になるよう調整。
        # on_demand: bytes -> amount X. editions: STANDARD slot_ms -> amount ~X
        target_amount = 10.0
        bytes_billed = int((target_amount / TH.pricing.on_demand_price_per_tib) * _TIB)
        price = TH.pricing.editions_price_per_slot_hour["ENTERPRISE"]
        slot_ms = int((target_amount / price) * _HOUR_SLOT_MS)
        job = make_job(total_bytes_billed=bytes_billed, total_slot_ms=slot_ms, edition=None)
        assert list(model_mismatch(job, TH)) == []

    def test_no_finding_when_either_amount_none(self):
        job = make_job(total_bytes_billed=None, total_slot_ms=1000, edition=None, cache_hit=False)
        assert list(model_mismatch(job, TH)) == []

    def test_no_finding_when_cheaper_model_equals_actual_model(self):
        # actual = editions（安い方）で、on_demand の方が高い場合、
        # cheaper_model == actual_model なので mismatch は発火しない。
        job = make_job(total_bytes_billed=_TIB, total_slot_ms=1, edition="STANDARD")
        assert list(model_mismatch(job, TH)) == []

    def test_both_zero_no_crash_no_finding(self):
        job = make_job(cache_hit=True, total_bytes_billed=0, total_slot_ms=0, edition=None)
        assert list(model_mismatch(job, TH)) == []

    def test_summary_has_no_suggestion_words_and_states_figures(self):
        job = make_job(total_bytes_billed=_TIB, total_slot_ms=1, edition=None)
        findings = list(model_mismatch(job, TH))
        assert len(findings) == 1
        assert_no_suggestion_words(findings[0])

    def test_evidence_has_both_amounts_and_ratio(self):
        job = make_job(total_bytes_billed=_TIB, total_slot_ms=1, edition=None)
        f = next(iter(model_mismatch(job, TH)))
        labels = {e.label for e in f.evidence}
        assert "on_demand_amount" in labels
        assert "editions_amount" in labels
        assert "savings_ratio" in labels
