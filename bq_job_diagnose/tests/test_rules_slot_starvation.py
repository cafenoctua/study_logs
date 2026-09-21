"""rules/slot_starvation.py のテスト（slot.starvation / slot.wait_dominant）。

TDD: このテストを先に書き、失敗することを確認してから slot_starvation.py を実装する。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.slot_starvation import starvation, wait_dominant
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job, make_stage, make_timeline_sample

TH = load_thresholds()


def _starved_run(
    n: int,
    *,
    start_elapsed: int = 0,
    step_ms: int = 1000,
    runnable: int | None = None,
    completed_start: int = 0,
    completed_end: int | None = None,
):
    """`n` 個の連続した starved サンプルを作る。completed_units は線形に補間する。"""
    if runnable is None:
        runnable = TH.slot.runnable_units_threshold
    if completed_end is None:
        completed_end = completed_start
    samples = []
    for i in range(n):
        elapsed = start_elapsed + i * step_ms
        if n == 1:
            completed = completed_start
        else:
            completed = completed_start + (completed_end - completed_start) * i // (n - 1)
        samples.append(
            make_timeline_sample(
                elapsed_ms=elapsed,
                estimated_runnable_units=runnable,
                completed_units=completed,
            )
        )
    return samples


class TestStarvationAllNoneReturnsNothing:
    def test_all_samples_estimated_runnable_units_none_no_finding(self):
        samples = tuple(
            make_timeline_sample(estimated_runnable_units=None, elapsed_ms=i * 1000)
            for i in range(5)
        )
        job = make_job(timeline=samples)
        assert list(starvation(job, TH)) == []


class TestStarvationRunLength:
    def test_run_exactly_at_consecutive_samples_with_no_progress_fires_warning(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(n, completed_start=0, completed_end=0)
        job = make_job(timeline=tuple(samples))
        findings = list(starvation(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_run_just_below_consecutive_samples_no_finding(self):
        n = TH.slot.consecutive_samples - 1
        samples = _starved_run(n, completed_start=0, completed_end=0)
        job = make_job(timeline=tuple(samples))
        assert list(starvation(job, TH)) == []

    def test_non_starved_sample_breaks_the_run(self):
        n = TH.slot.consecutive_samples
        starved = _starved_run(n, completed_start=0, completed_end=0)
        # 真ん中に非starvedサンプルを挟んで連続run を壊す
        mid = n // 2
        starved[mid] = make_timeline_sample(
            elapsed_ms=starved[mid].elapsed_ms,
            estimated_runnable_units=TH.slot.runnable_units_threshold - 1,
            completed_units=0,
        )
        job = make_job(timeline=tuple(starved))
        assert list(starvation(job, TH)) == []

    def test_runnable_units_exactly_at_threshold_counts_as_starved(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(
            n, runnable=TH.slot.runnable_units_threshold, completed_start=0, completed_end=0
        )
        job = make_job(timeline=tuple(samples))
        findings = list(starvation(job, TH))
        assert len(findings) == 1

    def test_runnable_units_just_below_threshold_not_starved(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(
            n,
            runnable=TH.slot.runnable_units_threshold - 1,
            completed_start=0,
            completed_end=0,
        )
        job = make_job(timeline=tuple(samples))
        assert list(starvation(job, TH)) == []


class TestStarvationProgress:
    def test_growth_ratio_exactly_at_max_fires_warning(self):
        n = TH.slot.consecutive_samples
        start = 1000
        end = start + int(start * TH.slot.max_completed_growth_ratio)
        samples = _starved_run(n, completed_start=start, completed_end=end)
        job = make_job(timeline=tuple(samples))
        findings = list(starvation(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_growth_ratio_above_max_no_finding(self):
        n = TH.slot.consecutive_samples
        start = 1000
        end = start + int(start * TH.slot.max_completed_growth_ratio) + max(
            2, int(start * 0.01)
        )
        while (end - start) / start <= TH.slot.max_completed_growth_ratio:
            end += 1
        samples = _starved_run(n, completed_start=start, completed_end=end)
        job = make_job(timeline=tuple(samples))
        assert list(starvation(job, TH)) == []

    def test_start_zero_end_zero_is_zero_progress_fires(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(n, completed_start=0, completed_end=0)
        job = make_job(timeline=tuple(samples))
        findings = list(starvation(job, TH))
        assert len(findings) == 1

    def test_start_zero_end_positive_is_progress_no_finding(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(n, completed_start=0, completed_end=100)
        job = make_job(timeline=tuple(samples))
        assert list(starvation(job, TH)) == []

    def test_completed_units_none_in_run_no_crash_no_finding(self):
        n = TH.slot.consecutive_samples
        samples = [
            make_timeline_sample(
                elapsed_ms=i * 1000,
                estimated_runnable_units=TH.slot.runnable_units_threshold,
                completed_units=None,
            )
            for i in range(n)
        ]
        job = make_job(timeline=tuple(samples))
        assert list(starvation(job, TH)) == []


class TestStarvationLongestRunSelection:
    def test_picks_longest_run_when_multiple_runs_exist(self):
        short_n = TH.slot.consecutive_samples - 2
        long_n = TH.slot.consecutive_samples + 3
        short_run = _starved_run(short_n, start_elapsed=0, completed_start=0, completed_end=0)
        gap = [
            make_timeline_sample(
                elapsed_ms=short_n * 1000,
                estimated_runnable_units=0,
                completed_units=0,
            )
        ]
        long_run = _starved_run(
            long_n,
            start_elapsed=(short_n + 1) * 1000,
            completed_start=0,
            completed_end=0,
        )
        job = make_job(timeline=tuple(short_run + gap + long_run))
        findings = list(starvation(job, TH))
        assert len(findings) == 1
        run_length_evidence = [e for e in findings[0].evidence if e.unit == "samples"]
        assert run_length_evidence
        assert run_length_evidence[0].value == long_n


class TestStarvationEvidenceAndSummary:
    def test_evidence_fields(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(n, completed_start=0, completed_end=0)
        job = make_job(timeline=tuple(samples))
        findings = list(starvation(job, TH))
        f = findings[0]
        units = {e.unit for e in f.evidence}
        assert "samples" in units
        assert "ms" in units

    def test_doc_quote(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(n, completed_start=0, completed_end=0)
        job = make_job(timeline=tuple(samples))
        findings = list(starvation(job, TH))
        assert "scheduled immediately" in findings[0].doc_quote

    def test_summary_has_no_suggestion_words(self):
        n = TH.slot.consecutive_samples
        samples = _starved_run(n, completed_start=0, completed_end=0)
        job = make_job(timeline=tuple(samples))
        for f in starvation(job, TH):
            assert_no_suggestion_words(f)


class TestWaitDominantBoundaries:
    def test_wait_share_exactly_at_warning_fires_warning(self):
        duration = 10000
        wait = int(duration * TH.slot.wait_share_warning)
        stage = make_stage(start_ms=0, end_ms=duration, wait_ms_avg=wait)
        job = make_job(stages=(stage,))
        findings = list(wait_dominant(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_wait_share_just_below_warning_no_finding(self):
        duration = 10000
        wait = int(duration * TH.slot.wait_share_warning) - 1
        stage = make_stage(start_ms=0, end_ms=duration, wait_ms_avg=wait)
        job = make_job(stages=(stage,))
        assert list(wait_dominant(job, TH)) == []

    def test_wait_share_exactly_at_critical_fires_critical(self):
        duration = 10000
        wait = int(duration * TH.slot.wait_share_critical)
        stage = make_stage(start_ms=0, end_ms=duration, wait_ms_avg=wait)
        job = make_job(stages=(stage,))
        findings = list(wait_dominant(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_wait_share_just_below_critical_fires_warning(self):
        duration = 10000
        wait = int(duration * TH.slot.wait_share_critical) - 1
        assert wait / duration >= TH.slot.wait_share_warning
        stage = make_stage(start_ms=0, end_ms=duration, wait_ms_avg=wait)
        job = make_job(stages=(stage,))
        findings = list(wait_dominant(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_wait_ms_avg_none_no_finding(self):
        stage = make_stage(start_ms=0, end_ms=10000, wait_ms_avg=None)
        job = make_job(stages=(stage,))
        assert list(wait_dominant(job, TH)) == []

    def test_duration_none_no_finding(self):
        stage = make_stage(start_ms=None, end_ms=None, wait_ms_avg=1000)
        job = make_job(stages=(stage,))
        assert list(wait_dominant(job, TH)) == []

    def test_duration_zero_no_finding_no_division_error(self):
        stage = make_stage(start_ms=1000, end_ms=1000, wait_ms_avg=100)
        job = make_job(stages=(stage,))
        assert list(wait_dominant(job, TH)) == []

    def test_evidence_and_stage_id(self):
        duration = 10000
        wait = int(duration * TH.slot.wait_share_critical)
        stage = make_stage(start_ms=0, end_ms=duration, wait_ms_avg=wait, id=4)
        job = make_job(stages=(stage,))
        findings = list(wait_dominant(job, TH))
        f = findings[0]
        assert f.stage_ids == (4,)
        assert all(e.stage_id == 4 for e in f.evidence)

    def test_summary_has_no_suggestion_words(self):
        duration = 10000
        wait = int(duration * TH.slot.wait_share_critical)
        stage = make_stage(start_ms=0, end_ms=duration, wait_ms_avg=wait)
        job = make_job(stages=(stage,))
        for f in wait_dominant(job, TH):
            assert_no_suggestion_words(f)
