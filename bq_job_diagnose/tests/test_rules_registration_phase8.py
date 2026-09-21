"""default_registry() への Phase 8 ルール登録状況のテスト。

TDD: このテストを先に書き、失敗することを確認してから各ルールモジュールを実装する。

既存の tests/test_rules_registration.py とは別ファイルにすることで、並行して
作業している cost ルール担当エージェントとの変更衝突を避ける。
"""

from __future__ import annotations

from bq_job_diagnose.rules import default_registry

EXPECTED_RULE_FLAGS_PHASE8 = {
    "join.broadcast_large": {"requires_plan": True, "requires_timeline": False},
    "join.shuffle_heavy": {"requires_plan": True, "requires_timeline": False},
    "join.cardinality_explosion": {"requires_plan": True, "requires_timeline": False},
    "plan_shape.repartition_repeat": {"requires_plan": True, "requires_timeline": False},
    "plan_shape.coalesce_repeat": {"requires_plan": True, "requires_timeline": False},
    "job.error": {"requires_plan": False, "requires_timeline": False},
    "job.resource_warning": {"requires_plan": False, "requires_timeline": False},
}


def _import_phase8_rule_modules():
    # デコレータによる登録を発火させるため、モジュールを import する。
    import bq_job_diagnose.rules.job_status
    import bq_job_diagnose.rules.joins
    import bq_job_diagnose.rules.plan_shape

    assert bq_job_diagnose.rules.job_status
    assert bq_job_diagnose.rules.joins
    assert bq_job_diagnose.rules.plan_shape


class TestPhase8RulesRegisteredExactlyOnce:
    def test_all_expected_rule_ids_present(self):
        _import_phase8_rule_modules()
        registry = default_registry()
        rule_ids = registry.rule_ids()
        for expected_id in EXPECTED_RULE_FLAGS_PHASE8:
            assert rule_ids.count(expected_id) == 1, (
                f"{expected_id} が正確に1回登録されていません（{rule_ids.count(expected_id)}回）"
            )

    def test_flags_match_expected(self):
        _import_phase8_rule_modules()
        registry = default_registry()
        for rule_id, expected in EXPECTED_RULE_FLAGS_PHASE8.items():
            spec = registry.get(rule_id)
            assert spec.requires_plan == expected["requires_plan"], rule_id
            assert spec.requires_timeline == expected["requires_timeline"], rule_id
