"""default_registry() への Phase 7 ルール登録状況のテスト。

TDD: このテストを先に書き、失敗することを確認してから各ルールモジュールを実装する。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import PlanAvailability
from bq_job_diagnose.rules import default_registry, run_rules
from tests.builders import make_job

TH = load_thresholds()

EXPECTED_RULE_FLAGS = {
    "skew.compute_time": {"requires_plan": True, "requires_timeline": False},
    "shuffle.spill": {"requires_plan": True, "requires_timeline": False},
    "shuffle.large_output": {"requires_plan": True, "requires_timeline": False},
    "filter.low_efficiency": {"requires_plan": True, "requires_timeline": False},
    "slot.starvation": {"requires_plan": False, "requires_timeline": True},
    "slot.wait_dominant": {"requires_plan": True, "requires_timeline": False},
}


def _import_all_rule_modules():
    # デコレータによる登録を発火させるため、モジュールを import する。
    import bq_job_diagnose.rules.filter_efficiency
    import bq_job_diagnose.rules.skew
    import bq_job_diagnose.rules.slot_starvation
    import bq_job_diagnose.rules.spill

    assert bq_job_diagnose.rules.filter_efficiency
    assert bq_job_diagnose.rules.skew
    assert bq_job_diagnose.rules.slot_starvation
    assert bq_job_diagnose.rules.spill


class TestAllSixRulesRegisteredExactlyOnce:
    def test_all_expected_rule_ids_present(self):
        _import_all_rule_modules()
        registry = default_registry()
        rule_ids = registry.rule_ids()
        for expected_id in EXPECTED_RULE_FLAGS:
            assert rule_ids.count(expected_id) == 1, (
                f"{expected_id} が正確に1回登録されていません（{rule_ids.count(expected_id)}回）"
            )

    def test_flags_match_expected(self):
        _import_all_rule_modules()
        registry = default_registry()
        for rule_id, expected in EXPECTED_RULE_FLAGS.items():
            spec = registry.get(rule_id)
            assert spec.requires_plan == expected["requires_plan"], rule_id
            assert spec.requires_timeline == expected["requires_timeline"], rule_id


class TestPlanlessJobSkipsPlanRequiringRules:
    def test_planless_job_produces_documented_skip_reasons(self):
        _import_all_rule_modules()
        registry = default_registry()
        job = make_job(plan_availability=PlanAvailability.CACHE_HIT, stages=(), timeline=())
        _findings, skipped = run_rules(job, TH, registry=registry)

        skipped_by_id = {s.rule_id: s.reason for s in skipped}
        for rule_id, expected in EXPECTED_RULE_FLAGS.items():
            if expected["requires_plan"]:
                assert rule_id in skipped_by_id
                assert "cache_hit" in skipped_by_id[rule_id]
            if expected["requires_timeline"]:
                assert rule_id in skipped_by_id
                assert "タイムライン" in skipped_by_id[rule_id]
