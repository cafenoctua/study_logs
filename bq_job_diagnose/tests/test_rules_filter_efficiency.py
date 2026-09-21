"""rules/filter_efficiency.py のテスト（filter.low_efficiency）。

TDD: このテストを先に書き、失敗することを確認してから filter_efficiency.py を実装する。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.filter_efficiency import low_efficiency
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job, make_stage, make_step

TH = load_thresholds()


def _read_stage(**overrides):
    defaults = {
        "steps": (make_step(kind="READ"),),
        "records_read": TH.filter.min_records_read,
        "records_written": TH.filter.min_records_read,  # efficiency = 1.0 by default
    }
    defaults.update(overrides)
    return make_stage(**defaults)


class TestFilterEfficiencyOnlyConsidersReadStages:
    def test_stage_without_read_step_is_ignored(self):
        stage = make_stage(
            steps=(make_step(kind="COMPUTE"),),
            records_read=TH.filter.min_records_read,
            records_written=1,
        )
        job = make_job(stages=(stage,))
        assert list(low_efficiency(job, TH)) == []

    def test_stage_with_read_step_among_others_is_considered(self):
        stage = _read_stage(
            steps=(make_step(kind="COMPUTE"), make_step(kind="READ")),
            records_written=int(TH.filter.min_records_read * TH.filter.efficiency_warning) - 1,
        )
        job = make_job(stages=(stage,))
        findings = list(low_efficiency(job, TH))
        assert len(findings) == 1


class TestFilterEfficiencyGuards:
    def test_records_read_none_no_finding(self):
        stage = _read_stage(records_read=None)
        job = make_job(stages=(stage,))
        assert list(low_efficiency(job, TH)) == []

    def test_records_written_none_no_finding(self):
        stage = _read_stage(records_written=None)
        job = make_job(stages=(stage,))
        assert list(low_efficiency(job, TH)) == []

    def test_records_read_below_min_skips(self):
        stage = _read_stage(
            records_read=TH.filter.min_records_read - 1,
            records_written=1,
        )
        job = make_job(stages=(stage,))
        assert list(low_efficiency(job, TH)) == []

    def test_records_read_at_min_does_not_skip_by_this_guard(self):
        stage = _read_stage(
            records_read=TH.filter.min_records_read,
            records_written=TH.filter.min_records_read,  # efficiency 1.0, no finding by ratio though
        )
        job = make_job(stages=(stage,))
        # 効率が1.0なので低効率ルールとしては発火しないが、例外は起きないこと
        assert list(low_efficiency(job, TH)) == []

    def test_records_read_zero_no_finding_no_division_error(self):
        stage = _read_stage(records_read=0, records_written=0)
        job = make_job(stages=(stage,))
        assert list(low_efficiency(job, TH)) == []


class TestFilterEfficiencyBoundaries:
    def test_efficiency_exactly_at_warning_fires_warning(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_warning)
        stage = _read_stage(records_read=read, records_written=written)
        job = make_job(stages=(stage,))
        findings = list(low_efficiency(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_efficiency_just_above_warning_no_finding(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_warning) + max(
            1, int(read * 0.0001)
        )
        # ensure ratio strictly above warning threshold
        while written / read <= TH.filter.efficiency_warning:
            written += 1
        stage = _read_stage(records_read=read, records_written=written)
        job = make_job(stages=(stage,))
        assert list(low_efficiency(job, TH)) == []

    def test_efficiency_exactly_at_critical_fires_critical(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_critical)
        stage = _read_stage(records_read=read, records_written=written)
        job = make_job(stages=(stage,))
        findings = list(low_efficiency(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_efficiency_just_above_critical_fires_warning(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_critical) + 1
        # keep it within warning bound
        assert written / read <= TH.filter.efficiency_warning
        stage = _read_stage(records_read=read, records_written=written)
        job = make_job(stages=(stage,))
        findings = list(low_efficiency(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING


class TestFilterEfficiencyEvidenceAndSummary:
    def test_evidence_contains_efficiency_read_written_with_stage_id(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_critical)
        stage = _read_stage(records_read=read, records_written=written, id=5)
        job = make_job(stages=(stage,))
        findings = list(low_efficiency(job, TH))
        f = findings[0]
        assert f.stage_ids == (5,)
        assert any(e.unit == "ratio" for e in f.evidence)
        assert any(e.unit == "rows" and e.value == read for e in f.evidence)
        assert any(e.unit == "rows" and e.value == written for e in f.evidence)
        assert all(e.stage_id == 5 for e in f.evidence)

    def test_doc_quote(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_critical)
        stage = _read_stage(records_read=read, records_written=written)
        job = make_job(stages=(stage,))
        findings = list(low_efficiency(job, TH))
        assert "filter ratio" in findings[0].doc_quote

    def test_summary_has_no_suggestion_words(self):
        read = TH.filter.min_records_read
        written = int(read * TH.filter.efficiency_critical)
        stage = _read_stage(records_read=read, records_written=written)
        job = make_job(stages=(stage,))
        for f in low_efficiency(job, TH):
            assert_no_suggestion_words(f)
