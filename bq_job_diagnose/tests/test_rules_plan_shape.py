"""rules/plan_shape.py のテスト（plan_shape.repartition_repeat / plan_shape.coalesce_repeat）。

TDD: このテストを先に書き、失敗することを確認してから plan_shape.py を実装する。

これらのルールは「REPARTITION / COALESCE が繰り返し出現するステージ数」でのみ発火し、
単発の出現では発火しない（BigQuery が自動挿入する正常な形状のため）。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.plan_shape import coalesce_repeat, repartition_repeat
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job, make_stage, make_step

TH = load_thresholds()


def _stages_with_marker(marker: str, count: int, *, in_kind: bool = True):
    stages = []
    for i in range(count):
        if in_kind:
            step = make_step(kind=f"{marker}_STEP", substeps=())
        else:
            step = make_step(kind="OTHER", substeps=(f"{marker} foo",))
        stages.append(make_stage(id=i + 1, steps=(step,)))
    return tuple(stages)


class TestRepartitionRepeat:
    def test_single_occurrence_no_finding(self):
        stages = _stages_with_marker("REPARTITION", 1)
        job = make_job(stages=stages)
        assert list(repartition_repeat(job, TH)) == []

    def test_just_below_min_stages_no_finding(self):
        stages = _stages_with_marker("REPARTITION", TH.plan_shape.repartition_min_stages - 1)
        job = make_job(stages=stages)
        assert list(repartition_repeat(job, TH)) == []

    def test_at_min_stages_warns(self):
        stages = _stages_with_marker("REPARTITION", TH.plan_shape.repartition_min_stages)
        job = make_job(stages=stages)
        findings = list(repartition_repeat(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert_no_suggestion_words(findings[0])

    def test_marker_in_substeps_also_counts(self):
        stages = _stages_with_marker(
            "REPARTITION", TH.plan_shape.repartition_min_stages, in_kind=False
        )
        job = make_job(stages=stages)
        findings = list(repartition_repeat(job, TH))
        assert len(findings) == 1

    def test_no_marker_no_finding(self):
        stage = make_stage(steps=(make_step(kind="READ", substeps=()),))
        job = make_job(stages=(stage, stage, stage))
        assert list(repartition_repeat(job, TH)) == []

    def test_evidence_contains_stage_ids(self):
        n = TH.plan_shape.repartition_min_stages
        stages = _stages_with_marker("REPARTITION", n)
        job = make_job(stages=stages)
        finding = next(iter(repartition_repeat(job, TH)))
        assert finding.stage_ids == tuple(s.id for s in stages)
        assert any(e.label == "stage_count" and e.value == n for e in finding.evidence)

    def test_doc_fields(self):
        n = TH.plan_shape.repartition_min_stages
        stages = _stages_with_marker("REPARTITION", n)
        job = make_job(stages=stages)
        finding = next(iter(repartition_repeat(job, TH)))
        assert finding.doc_url == "https://cloud.google.com/bigquery/docs/query-plan-explanation"
        assert finding.doc_quote is not None


class TestCoalesceRepeat:
    def test_single_occurrence_no_finding(self):
        stages = _stages_with_marker("COALESCE", 1)
        job = make_job(stages=stages)
        assert list(coalesce_repeat(job, TH)) == []

    def test_just_below_min_stages_no_finding(self):
        stages = _stages_with_marker("COALESCE", TH.plan_shape.coalesce_min_stages - 1)
        job = make_job(stages=stages)
        assert list(coalesce_repeat(job, TH)) == []

    def test_at_min_stages_warns(self):
        stages = _stages_with_marker("COALESCE", TH.plan_shape.coalesce_min_stages)
        job = make_job(stages=stages)
        findings = list(coalesce_repeat(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert_no_suggestion_words(findings[0])

    def test_marker_in_substeps_also_counts(self):
        stages = _stages_with_marker(
            "COALESCE", TH.plan_shape.coalesce_min_stages, in_kind=False
        )
        job = make_job(stages=stages)
        findings = list(coalesce_repeat(job, TH))
        assert len(findings) == 1

    def test_no_marker_no_finding(self):
        stage = make_stage(steps=(make_step(kind="READ", substeps=()),))
        job = make_job(stages=(stage, stage, stage))
        assert list(coalesce_repeat(job, TH)) == []

    def test_evidence_contains_stage_ids(self):
        n = TH.plan_shape.coalesce_min_stages
        stages = _stages_with_marker("COALESCE", n)
        job = make_job(stages=stages)
        finding = next(iter(coalesce_repeat(job, TH)))
        assert finding.stage_ids == tuple(s.id for s in stages)
        assert any(e.label == "stage_count" and e.value == n for e in finding.evidence)
