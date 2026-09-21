"""rules/job_status.py のテスト（job.error / job.resource_warning）。

TDD: このテストを先に書き、失敗することを確認してから job_status.py を実装する。

両ルールとも job レベルのフィールドのみを見るため requires_plan=False。
"""

from __future__ import annotations

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import Severity
from bq_job_diagnose.rules.job_status import error, resource_warning
from tests.assertions import assert_no_suggestion_words
from tests.builders import make_job

TH = load_thresholds()


class TestJobError:
    def test_error_result_none_no_finding(self):
        job = make_job(error_result=None)
        assert list(error(job, TH)) == []

    def test_error_result_present_critical(self):
        job = make_job(
            error_result={"reason": "invalidQuery", "message": "Syntax error near X"}
        )
        findings = list(error(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL
        assert "invalidQuery" in findings[0].summary
        assert "Syntax error near X" in findings[0].summary
        assert_no_suggestion_words(findings[0])

    def test_error_result_missing_message_key_no_crash(self):
        job = make_job(error_result={"reason": "invalidQuery"})
        findings = list(error(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL
        assert "invalidQuery" in findings[0].summary
        assert_no_suggestion_words(findings[0])

    def test_error_result_missing_reason_key_no_crash(self):
        job = make_job(error_result={"message": "Syntax error near X"})
        findings = list(error(job, TH))
        assert len(findings) == 1
        assert "Syntax error near X" in findings[0].summary
        assert_no_suggestion_words(findings[0])

    def test_error_result_empty_dict_no_crash(self):
        job = make_job(error_result={})
        findings = list(error(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL
        assert_no_suggestion_words(findings[0])


class TestJobResourceWarning:
    def test_resource_warning_none_no_finding(self):
        job = make_job(resource_warning=None)
        assert list(resource_warning(job, TH)) == []

    def test_resource_warning_empty_string_no_finding(self):
        job = make_job(resource_warning="")
        assert list(resource_warning(job, TH)) == []

    def test_resource_warning_present_warns(self):
        job = make_job(resource_warning="Not enough resources for query planning")
        findings = list(resource_warning(job, TH))
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "Not enough resources for query planning" in findings[0].summary
        assert_no_suggestion_words(findings[0])

    def test_resource_warning_evidence(self):
        job = make_job(resource_warning="Not enough resources")
        finding = next(iter(resource_warning(job, TH)))
        assert any(e.label == "resource_warning" for e in finding.evidence)
