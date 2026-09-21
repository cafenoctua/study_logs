"""rules/skew.py のテスト。

TDD: このテストを先に書き、失敗することを確認してから skew.py を実装する。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.skew import compute_time
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job, make_stage

TH = load_thresholds()


def _stage_for_skew(**overrides):
    """スキューガードを全て通過する健全なベースのステージを作る。

    duration_ms >= min_stage_duration_ms(1000)、compute_ms_max >= min_compute_ms_max(5000)、
    compute が dominant (compute_ms_max/duration_ms >= min_compute_share_of_stage(0.3)) を満たす。
    """
    defaults = {
        "start_ms": 0,
        "end_ms": 10000,  # duration_ms = 10000
        "compute_ms_avg": 1000,
        "compute_ms_max": 8000,  # ratio = 8.0, share = 8000/10000=0.8
    }
    defaults.update(overrides)
    return make_stage(**defaults)


class TestSkewBoundaries:
    def test_ratio_exactly_at_warning_fires_warning(self):
        ratio = TH.skew.ratio_warning
        avg = 2000
        max_ = int(avg * ratio)
        stage = _stage_for_skew(compute_ms_avg=avg, compute_ms_max=max_)
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_ratio_just_below_warning_no_finding(self):
        ratio = TH.skew.ratio_warning
        avg = 2000
        max_ = int(avg * ratio) - 1
        stage = _stage_for_skew(compute_ms_avg=avg, compute_ms_max=max_)
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert findings == []

    def test_ratio_exactly_at_critical_fires_critical(self):
        ratio = TH.skew.ratio_critical
        avg = 2000
        max_ = int(avg * ratio)
        stage = _stage_for_skew(compute_ms_avg=avg, compute_ms_max=max_)
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_ratio_just_below_critical_fires_warning(self):
        ratio = TH.skew.ratio_critical
        avg = 2000
        max_ = int(avg * ratio) - 1
        # まだ warning 閾値以上であること
        assert max_ / avg >= TH.skew.ratio_warning
        stage = _stage_for_skew(compute_ms_avg=avg, compute_ms_max=max_)
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING


class TestSkewGuards:
    def test_none_compute_ms_avg_no_finding(self):
        stage = _stage_for_skew(compute_ms_avg=None)
        job = make_job(stages=(stage,))
        assert list(compute_time(job, TH)) == []

    def test_none_compute_ms_max_no_finding(self):
        stage = _stage_for_skew(compute_ms_max=None)
        job = make_job(stages=(stage,))
        assert list(compute_time(job, TH)) == []

    def test_short_stage_duration_skips(self):
        # duration_ms < min_stage_duration_ms(1000) はガードでスキップ
        stage = _stage_for_skew(
            start_ms=0, end_ms=TH.global_.min_stage_duration_ms - 1,
            compute_ms_avg=100, compute_ms_max=1000,
        )
        job = make_job(stages=(stage,))
        assert list(compute_time(job, TH)) == []

    def test_duration_none_does_not_trigger_short_stage_guard(self):
        # duration_ms が None（start_ms か end_ms が None）の場合は
        # 短時間ガードの対象外（スキップしない = 判定継続）。
        stage = _stage_for_skew(start_ms=None, end_ms=None, compute_ms_avg=1000, compute_ms_max=8000)
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1

    def test_compute_ms_max_below_min_skips(self):
        stage = _stage_for_skew(
            compute_ms_avg=100,
            compute_ms_max=TH.skew.min_compute_ms_max - 1,
        )
        job = make_job(stages=(stage,))
        assert list(compute_time(job, TH)) == []

    def test_compute_ms_max_at_min_does_not_skip_by_this_guard(self):
        # min_compute_ms_max ちょうどはガードされない（>= min は許容）
        stage = _stage_for_skew(
            start_ms=0, end_ms=10000,
            compute_ms_avg=100,
            compute_ms_max=TH.skew.min_compute_ms_max,
        )
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1

    def test_compute_not_dominant_skips(self):
        # compute_ms_max / duration_ms < min_compute_share_of_stage(0.3)
        stage = _stage_for_skew(
            start_ms=0, end_ms=100000,  # duration=100000
            compute_ms_avg=100,
            compute_ms_max=5000,  # share = 0.05 < 0.3、だが ratio=50 (>critical)
        )
        job = make_job(stages=(stage,))
        assert list(compute_time(job, TH)) == []

    def test_compute_share_guard_skipped_when_duration_none(self):
        stage = _stage_for_skew(
            start_ms=None, end_ms=None, compute_ms_avg=100, compute_ms_max=8000
        )
        job = make_job(stages=(stage,))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1


class TestSkewEvidenceAndSummary:
    def test_evidence_contains_ratio_avg_max_with_stage_id(self):
        job = make_job(stages=(_stage_for_skew(compute_ms_avg=1000, compute_ms_max=8000, id=7),))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1
        f = findings[0]
        assert f.stage_ids == (7,)
        assert any(e.unit == "ratio" for e in f.evidence)
        assert any(e.unit == "ms" and e.value == 1000 for e in f.evidence)
        assert any(e.unit == "ms" and e.value == 8000 for e in f.evidence)
        for e in f.evidence:
            assert e.stage_id == 7

    def test_doc_url_and_quote(self):
        job = make_job(stages=(_stage_for_skew(),))
        findings = list(compute_time(job, TH))
        assert findings[0].doc_url == "https://cloud.google.com/bigquery/docs/query-plan-explanation"
        assert "compute maximum" in findings[0].doc_quote

    def test_summary_has_no_suggestion_words(self):
        job = make_job(stages=(_stage_for_skew(),))
        findings = list(compute_time(job, TH))
        for f in findings:
            assert_no_suggestion_words(f)

    def test_multiple_stages_each_evaluated(self):
        good = _stage_for_skew(id=1)
        bad = _stage_for_skew(id=2, compute_ms_avg=100, compute_ms_max=100)  # ratio=1, no finding
        job = make_job(stages=(good, bad))
        findings = list(compute_time(job, TH))
        assert len(findings) == 1
        assert findings[0].stage_ids == (1,)
