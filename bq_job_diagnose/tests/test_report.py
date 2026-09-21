"""report/ 層（JSON / Markdown）のテスト。

TDD: このテストを先に書き、失敗することを確認してから
report/json_report.py, report/markdown_report.py を実装する。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from bq_job_diagnose.config import load_thresholds
from bq_job_diagnose.models import (
    Diagnosis,
    Evidence,
    Finding,
    PlanAvailability,
    Severity,
    SkippedRule,
    Source,
)
from bq_job_diagnose.report.json_report import (
    append_starvation_skip_if_needed,
    build_json_report,
)
from bq_job_diagnose.report.markdown_report import build_markdown_report
from bq_job_diagnose.rules import run_rules
from tests.builders import make_job, make_timeline_sample

TH = load_thresholds()

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"

_GENERATED_AT = datetime(2026, 9, 21, 0, 0, 0, tzinfo=UTC)
_CONFIG_DIGEST = "deadbeefcafe"


def _diagnosis_for_job(job) -> Diagnosis:
    findings, skipped = run_rules(job, TH)
    return Diagnosis(
        job=job,
        findings=tuple(findings),
        skipped_rules=tuple(skipped),
        generated_at=_GENERATED_AT,
        config_digest=_CONFIG_DIGEST,
    )


def _load_skewed_join_job():
    """tests/fixtures/is_rows/skewed_join.json から Job を組み立てる。"""
    from bq_job_diagnose.normalize.from_information_schema import normalize_row

    fixture_path = (
        Path(__file__).parent / "fixtures" / "is_rows" / "skewed_join.json"
    )
    row = json.loads(fixture_path.read_text(encoding="utf-8"))
    return normalize_row(row, location="asia-northeast1")


# ---------------------------------------------------------------------------
# Part A: JSON レポート
# ---------------------------------------------------------------------------


class TestBuildJsonReportSchema:
    def test_schema_version_is_first_key(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        keys = list(report.keys())
        assert keys[0] == "schema_version"

    def test_top_level_keys(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        assert set(report.keys()) == {
            "schema_version",
            "generated_at",
            "config_digest",
            "mode",
            "jobs",
            "scan_summary",
        }
        assert report["mode"] == "job"
        assert report["scan_summary"] is None

    def test_cost_always_present_even_when_amounts_none(self):
        job = make_job(cache_hit=False, total_bytes_billed=None, total_slot_ms=None)
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        cost = report["jobs"][0]["cost"]
        assert cost is not None
        assert cost["on_demand"]["amount"] is None
        assert cost["editions"]["amount"] is None
        assert "cheaper_model" in cost
        assert "savings_ratio" in cost

    def test_skipped_rules_always_present_even_when_empty(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        # 全前提条件を満たす健全なジョブなら skipped_rules は空かもしれないが、
        # キー自体は必ず存在しなければならない。
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        assert "skipped_rules" in report["jobs"][0]
        assert isinstance(report["jobs"][0]["skipped_rules"], list)

    def test_json_dumps_succeeds_without_custom_encoder(self):
        job = _load_skewed_join_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        # カスタムエンコーダなしで確実に文字列化できること。
        dumped = json.dumps(report)
        assert isinstance(dumped, str)
        # ラウンドトリップも確認する。
        reloaded = json.loads(dumped)
        assert reloaded["schema_version"] == "1"

    def test_datetimes_are_iso8601_strings(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        job_dict = report["jobs"][0]["job"]
        assert isinstance(job_dict["creation_time"], str)
        # ISO8601 としてパースできること。
        datetime.fromisoformat(job_dict["creation_time"])
        assert isinstance(report["generated_at"], str)

    def test_enums_are_values(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        job_dict = report["jobs"][0]["job"]
        assert job_dict["source"] == Source.INFORMATION_SCHEMA.value
        assert job_dict["plan_availability"] == PlanAvailability.AVAILABLE.value

    def test_findings_sorted_by_severity_then_rule_id(self):
        job = make_job()
        findings = (
            Finding(
                rule_id="z.rule",
                title="t",
                severity=Severity.INFO,
                summary="s",
                evidence=(),
            ),
            Finding(
                rule_id="a.rule",
                title="t",
                severity=Severity.CRITICAL,
                summary="s",
                evidence=(),
            ),
            Finding(
                rule_id="b.rule",
                title="t",
                severity=Severity.CRITICAL,
                summary="s",
                evidence=(),
            ),
            Finding(
                rule_id="m.rule",
                title="t",
                severity=Severity.WARNING,
                summary="s",
                evidence=(),
            ),
            Finding(
                rule_id="c.rule",
                title="t",
                severity=Severity.ADVISORY,
                summary="s",
                evidence=(),
            ),
        )
        diag = Diagnosis(
            job=job,
            findings=findings,
            skipped_rules=(),
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        rule_ids = [f["rule_id"] for f in report["jobs"][0]["findings"]]
        assert rule_ids == ["a.rule", "b.rule", "m.rule", "c.rule", "z.rule"]

    def test_finding_evidence_and_fields_serialized(self):
        job = make_job()
        finding = Finding(
            rule_id="test.rule",
            title="テストタイトル",
            severity=Severity.WARNING,
            summary="テストサマリ",
            evidence=(
                Evidence(label="foo", value=1.5, unit="ms", stage_id=1, threshold=2.0),
            ),
            stage_ids=(1, 2),
            doc_url="https://example.com",
            doc_quote="quote",
            confidence="medium",
        )
        diag = Diagnosis(
            job=job,
            findings=(finding,),
            skipped_rules=(),
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        f = report["jobs"][0]["findings"][0]
        assert f["rule_id"] == "test.rule"
        assert f["severity"] == "warning"
        assert f["evidence"][0] == {
            "label": "foo",
            "value": 1.5,
            "unit": "ms",
            "stage_id": 1,
            "threshold": 2.0,
        }
        assert f["stage_ids"] == [1, 2]
        assert f["confidence"] == "medium"

    def test_golden_json_skewed_join(self):
        job = _load_skewed_join_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        golden_path = GOLDEN_DIR / "skewed_join_report.json"
        expected = json.loads(golden_path.read_text(encoding="utf-8"))
        assert report == expected


class TestStarvationSkipPostProcessing:
    def test_jobs_api_source_no_finding_appends_skip(self):
        job = make_job(
            source=Source.JOBS_API,
            timeline=(make_timeline_sample(estimated_runnable_units=None),),
        )
        findings: list[Finding] = []
        skipped: list[SkippedRule] = []
        result = append_starvation_skip_if_needed(job, findings, skipped)
        rule_ids = [s.rule_id for s in result]
        assert "slot.starvation" in rule_ids
        skip = next(s for s in result if s.rule_id == "slot.starvation")
        assert skip.reason

    def test_all_none_estimated_runnable_units_appends_skip(self):
        job = make_job(
            source=Source.INFORMATION_SCHEMA,
            timeline=(
                make_timeline_sample(estimated_runnable_units=None),
                make_timeline_sample(estimated_runnable_units=None),
            ),
        )
        result = append_starvation_skip_if_needed(job, [], [])
        rule_ids = [s.rule_id for s in result]
        assert "slot.starvation" in rule_ids

    def test_information_schema_with_real_values_no_finding_no_skip(self):
        job = make_job(
            source=Source.INFORMATION_SCHEMA,
            timeline=(
                make_timeline_sample(estimated_runnable_units=0),
                make_timeline_sample(estimated_runnable_units=0),
            ),
        )
        # starvation の Finding が無い（健全）場合、SkippedRule は追加されない。
        result = append_starvation_skip_if_needed(job, [], [])
        rule_ids = [s.rule_id for s in result]
        assert "slot.starvation" not in rule_ids

    def test_finding_already_present_no_duplicate_skip(self):
        job = make_job(
            source=Source.JOBS_API,
            timeline=(make_timeline_sample(estimated_runnable_units=None),),
        )
        starvation_finding = Finding(
            rule_id="slot.starvation",
            title="t",
            severity=Severity.WARNING,
            summary="s",
            evidence=(),
        )
        result = append_starvation_skip_if_needed(job, [starvation_finding], [])
        rule_ids = [s.rule_id for s in result]
        assert "slot.starvation" not in rule_ids

    def test_existing_skipped_rules_preserved(self):
        job = make_job(
            source=Source.JOBS_API,
            timeline=(make_timeline_sample(estimated_runnable_units=None),),
        )
        existing = SkippedRule(rule_id="other.rule", reason="他の理由")
        result = append_starvation_skip_if_needed(job, [], [existing])
        assert existing in result

    def test_integration_via_build_json_report_jobs_api(self):
        job = make_job(
            source=Source.JOBS_API,
            timeline=(make_timeline_sample(estimated_runnable_units=None),),
        )
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        skipped_ids = [s["rule_id"] for s in report["jobs"][0]["skipped_rules"]]
        assert "slot.starvation" in skipped_ids


# ---------------------------------------------------------------------------
# Part B: Markdown レポート
# ---------------------------------------------------------------------------


class TestBuildMarkdownReport:
    def test_renders_job_with_findings(self):
        job = _load_skewed_join_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert isinstance(md, str)
        assert job.job_id in md
        assert "所見" in md
        assert "評価できなかった項目" in md

    def test_renders_job_with_no_findings(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert "評価できなかった項目" in md

    def test_renders_cache_hit_job_no_plan(self):
        job = make_job(
            cache_hit=True,
            plan_availability=PlanAvailability.CACHE_HIT,
            stages=(),
        )
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert isinstance(md, str)
        assert "評価できなかった項目" in md

    def test_renders_job_with_cost_amounts_none(self):
        job = make_job(cache_hit=False, total_bytes_billed=None, total_slot_ms=None)
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert isinstance(md, str)
        # None の場合は unavailable_reason が出ていること（空白やゼロではない）。
        assert "取得できません" in md

    def test_markdown_contains_both_cost_models_when_available(self):
        job = make_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert "on_demand" in report["jobs"][0]["cost"]
        assert "editions" in report["jobs"][0]["cost"]
        # 両モデルの単価参照が両方とも本文に出ていること。
        cost = report["jobs"][0]["cost"]
        assert cost["on_demand"]["price_ref"] in md
        assert cost["editions"]["price_ref"] in md

    def test_empty_skipped_rules_shows_none_marker(self):
        job = make_job()
        diag = Diagnosis(
            job=job,
            findings=(),
            skipped_rules=(),
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        assert report["jobs"][0]["skipped_rules"] == []
        md = build_markdown_report(report)
        assert "評価できなかった項目" in md
        assert "なし" in md

    def test_elapsed_ms_rendered_from_start_end_time(self):
        job = _load_skewed_join_job()
        diag = _diagnosis_for_job(job)
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert f"{job.elapsed_ms:,} ms" in md or f"{job.elapsed_ms} ms" in md

    def test_low_confidence_finding_shows_confidence(self):
        job = make_job()
        finding = Finding(
            rule_id="test.rule",
            title="テストタイトル",
            severity=Severity.ADVISORY,
            summary="テストサマリ",
            evidence=(),
            confidence="low",
        )
        diag = Diagnosis(
            job=job,
            findings=(finding,),
            skipped_rules=(),
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        report = build_json_report(
            mode="job",
            diagnoses=[diag],
            generated_at=_GENERATED_AT,
            config_digest=_CONFIG_DIGEST,
        )
        md = build_markdown_report(report)
        assert "low" in md
