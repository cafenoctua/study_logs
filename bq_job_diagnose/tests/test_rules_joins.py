"""rules/joins.py のテスト（join.broadcast_large / join.shuffle_heavy / join.cardinality_explosion）。

TDD: このテストを先に書き、失敗することを確認してから joins.py を実装する。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.joins import (
    broadcast_large,
    cardinality_explosion,
    shuffle_heavy,
)
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job, make_stage, make_step

TH = load_thresholds()


class TestBroadcastLarge:
    def test_broadcast_join_over_threshold_warns(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH ALL foo",)),),
            shuffle_output_bytes=TH.join.broadcast_input_bytes_warning,
        )
        job = make_job(stages=(stage,))
        findings = list(broadcast_large(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].confidence == "high"
        assert_no_suggestion_words(findings[0])

    def test_broadcast_join_just_below_threshold_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH ALL foo",)),),
            shuffle_output_bytes=TH.join.broadcast_input_bytes_warning - 1,
        )
        job = make_job(stages=(stage,))
        assert list(broadcast_large(job, TH)) == []

    def test_no_broadcast_substep_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH EACH foo",)),),
            shuffle_output_bytes=TH.join.broadcast_input_bytes_warning,
        )
        job = make_job(stages=(stage,))
        assert list(broadcast_large(job, TH)) == []

    def test_shuffle_output_bytes_none_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH ALL foo",)),),
            shuffle_output_bytes=None,
        )
        job = make_job(stages=(stage,))
        assert list(broadcast_large(job, TH)) == []

    def test_shuffle_output_bytes_zero_treated_as_zero_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH ALL foo",)),),
            shuffle_output_bytes=0,
        )
        job = make_job(stages=(stage,))
        assert list(broadcast_large(job, TH)) == []

    def test_truncated_step_lowers_confidence_to_medium(self):
        stage = make_stage(
            steps=(
                make_step(substeps=("JOIN EACH WITH ALL foo",), truncated=True),
            ),
            shuffle_output_bytes=TH.join.broadcast_input_bytes_warning,
        )
        job = make_job(stages=(stage,))
        findings = list(broadcast_large(job, TH))
        assert len(findings) == 1
        assert findings[0].confidence == "medium"

    def test_truncated_on_different_step_in_same_stage_still_lowers_confidence(self):
        stage = make_stage(
            steps=(
                make_step(substeps=("JOIN EACH WITH ALL foo",)),
                make_step(kind="READ", substeps=(), truncated=True),
            ),
            shuffle_output_bytes=TH.join.broadcast_input_bytes_warning,
        )
        job = make_job(stages=(stage,))
        findings = list(broadcast_large(job, TH))
        assert len(findings) == 1
        assert findings[0].confidence == "medium"

    def test_evidence_and_doc_fields(self):
        stage = make_stage(
            id=7,
            steps=(make_step(substeps=("JOIN EACH WITH ALL foo",)),),
            shuffle_output_bytes=TH.join.broadcast_input_bytes_warning,
        )
        job = make_job(stages=(stage,))
        finding = next(iter(broadcast_large(job, TH)))
        assert finding.stage_ids == (7,)
        assert finding.doc_url == "https://cloud.google.com/bigquery/docs/query-plan-explanation"
        assert finding.doc_quote is not None
        assert any(e.label == "shuffle_output_bytes" for e in finding.evidence)


class TestShuffleHeavy:
    def test_shuffle_join_with_spill_warns(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH EACH foo",)),),
            shuffle_output_bytes_spilled=1,
        )
        job = make_job(stages=(stage,))
        findings = list(shuffle_heavy(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert_no_suggestion_words(findings[0])

    def test_shuffle_join_without_spill_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH EACH foo",)),),
            shuffle_output_bytes_spilled=0,
        )
        job = make_job(stages=(stage,))
        assert list(shuffle_heavy(job, TH)) == []

    def test_spill_none_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH EACH foo",)),),
            shuffle_output_bytes_spilled=None,
        )
        job = make_job(stages=(stage,))
        assert list(shuffle_heavy(job, TH)) == []

    def test_no_shuffle_join_substep_no_finding(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH ALL foo",)),),
            shuffle_output_bytes_spilled=1,
        )
        job = make_job(stages=(stage,))
        assert list(shuffle_heavy(job, TH)) == []

    def test_truncated_lowers_confidence(self):
        stage = make_stage(
            steps=(make_step(substeps=("JOIN EACH WITH EACH foo",), truncated=True),),
            shuffle_output_bytes_spilled=1,
        )
        job = make_job(stages=(stage,))
        findings = list(shuffle_heavy(job, TH))
        assert findings[0].confidence == "medium"


class TestCardinalityExplosion:
    def _join_stage(self, **overrides):
        defaults = {
            "steps": (make_step(substeps=("JOIN foo",)),),
            "records_read": TH.join.min_output_records,
            "records_written": int(TH.join.min_output_records * TH.join.cardinality_explosion_ratio),
        }
        defaults.update(overrides)
        return make_stage(**defaults)

    def test_at_ratio_and_min_output_warns(self):
        stage = self._join_stage()
        job = make_job(stages=(stage,))
        findings = list(cardinality_explosion(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert_no_suggestion_words(findings[0])

    def test_just_below_ratio_no_finding(self):
        stage = self._join_stage(
            records_written=int(TH.join.min_output_records * TH.join.cardinality_explosion_ratio) - 1
        )
        job = make_job(stages=(stage,))
        assert list(cardinality_explosion(job, TH)) == []

    def test_records_written_below_min_output_no_finding(self):
        stage = self._join_stage(
            records_read=1,
            records_written=TH.join.min_output_records - 1,
        )
        job = make_job(stages=(stage,))
        assert list(cardinality_explosion(job, TH)) == []

    def test_records_read_none_no_finding(self):
        stage = self._join_stage(records_read=None)
        job = make_job(stages=(stage,))
        assert list(cardinality_explosion(job, TH)) == []

    def test_records_written_none_no_finding(self):
        stage = self._join_stage(records_written=None)
        job = make_job(stages=(stage,))
        assert list(cardinality_explosion(job, TH)) == []

    def test_records_read_zero_skipped_no_division_error(self):
        stage = self._join_stage(records_read=0, records_written=TH.join.min_output_records)
        job = make_job(stages=(stage,))
        assert list(cardinality_explosion(job, TH)) == []

    def test_no_join_substep_no_finding(self):
        stage = self._join_stage(steps=(make_step(substeps=("READ foo",)),))
        job = make_job(stages=(stage,))
        assert list(cardinality_explosion(job, TH)) == []

    def test_truncated_lowers_confidence(self):
        stage = self._join_stage(
            steps=(make_step(substeps=("JOIN foo",), truncated=True),)
        )
        job = make_job(stages=(stage,))
        findings = list(cardinality_explosion(job, TH))
        assert findings[0].confidence == "medium"

    def test_evidence_contents(self):
        stage = self._join_stage(id=3)
        job = make_job(stages=(stage,))
        finding = next(iter(cardinality_explosion(job, TH)))
        assert finding.stage_ids == (3,)
        labels = {e.label for e in finding.evidence}
        assert "records_read" in labels
        assert "records_written" in labels
