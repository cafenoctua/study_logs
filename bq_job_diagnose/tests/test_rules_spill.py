"""rules/spill.py のテスト（shuffle.spill / shuffle.large_output）。

TDD: このテストを先に書き、失敗することを確認してから spill.py を実装する。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.spill import large_output, spill
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job, make_stage

TH = load_thresholds()


class TestSpillFires:
    def test_spilled_bytes_gt_zero_fires_advisory(self):
        stage = make_stage(shuffle_output_bytes_spilled=1)
        job = make_job(stages=(stage,))
        findings = list(spill(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.ADVISORY

    def test_spilled_bytes_zero_no_finding(self):
        stage = make_stage(shuffle_output_bytes_spilled=0)
        job = make_job(stages=(stage,))
        assert list(spill(job, TH)) == []

    def test_spilled_bytes_none_no_finding(self):
        stage = make_stage(shuffle_output_bytes_spilled=None)
        job = make_job(stages=(stage,))
        assert list(spill(job, TH)) == []

    def test_huge_spill_is_still_advisory_not_escalated(self):
        # spill は非決定的なシグナルのため、どれだけ大きくても ADVISORY のまま。
        stage = make_stage(shuffle_output_bytes_spilled=TH.shuffle.spill_bytes_notable * 1000)
        job = make_job(stages=(stage,))
        findings = list(spill(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.ADVISORY

    def test_evidence_includes_spill_bytes_and_notable_threshold(self):
        stage = make_stage(shuffle_output_bytes_spilled=TH.shuffle.spill_bytes_notable + 1, id=3)
        job = make_job(stages=(stage,))
        findings = list(spill(job, TH))
        f = findings[0]
        assert f.stage_ids == (3,)
        spill_evidence = [e for e in f.evidence if e.value == TH.shuffle.spill_bytes_notable + 1]
        assert spill_evidence
        assert any(e.threshold == TH.shuffle.spill_bytes_notable for e in f.evidence)

    def test_doc_quote(self):
        stage = make_stage(shuffle_output_bytes_spilled=1)
        job = make_job(stages=(stage,))
        findings = list(spill(job, TH))
        assert "isn't stored effectively" in findings[0].doc_quote

    def test_summary_has_no_suggestion_words(self):
        stage = make_stage(shuffle_output_bytes_spilled=1)
        job = make_job(stages=(stage,))
        for f in spill(job, TH):
            assert_no_suggestion_words(f)


class TestLargeOutputBoundaries:
    def test_exactly_at_warning_threshold_fires_warning(self):
        stage = make_stage(shuffle_output_bytes=TH.shuffle.output_bytes_warning)
        job = make_job(stages=(stage,))
        findings = list(large_output(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_just_below_warning_threshold_no_finding(self):
        stage = make_stage(shuffle_output_bytes=TH.shuffle.output_bytes_warning - 1)
        job = make_job(stages=(stage,))
        assert list(large_output(job, TH)) == []

    def test_none_shuffle_output_bytes_no_finding(self):
        stage = make_stage(shuffle_output_bytes=None)
        job = make_job(stages=(stage,))
        assert list(large_output(job, TH)) == []

    def test_zero_shuffle_output_bytes_treated_as_zero_no_finding(self):
        stage = make_stage(shuffle_output_bytes=0)
        job = make_job(stages=(stage,))
        assert list(large_output(job, TH)) == []

    def test_evidence_and_stage_id(self):
        stage = make_stage(shuffle_output_bytes=TH.shuffle.output_bytes_warning, id=9)
        job = make_job(stages=(stage,))
        findings = list(large_output(job, TH))
        f = findings[0]
        assert f.stage_ids == (9,)
        assert all(e.stage_id == 9 for e in f.evidence)

    def test_summary_has_no_suggestion_words(self):
        stage = make_stage(shuffle_output_bytes=TH.shuffle.output_bytes_warning)
        job = make_job(stages=(stage,))
        for f in large_output(job, TH):
            assert_no_suggestion_words(f)
