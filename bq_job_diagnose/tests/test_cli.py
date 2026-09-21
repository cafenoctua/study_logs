"""cli.py（Phase 11）のテスト。

TDD: このテストを先に書き、失敗することを確認してから cli.py を実装する。

制約（重要）:
- GCP アクセス・ネットワークアクセスを一切行わない。
- `google.cloud.bigquery.Client` をモックしない（REVIEW_GUIDE.md 2.3）。
  `FileCollector` + フィクスチャで実データ形状を通す。
- `--dry-run-sql` は認証情報が無くても動作すること。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bq_job_diagnose import cli
from bq_job_diagnose.collect.file_collector import FileCollector

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "is_rows"


@pytest.fixture(autouse=True)
def _reset_collector_factory():
    """各テストの前後で COLLECTOR_FACTORY を既定値に戻す。"""
    original = cli.COLLECTOR_FACTORY
    yield
    cli.COLLECTOR_FACTORY = original


@pytest.fixture(autouse=True)
def _no_adc_credentials(monkeypatch):
    """ADC 認証情報が全く無い環境を模す（--dry-run-sql が動くことの検証用）。"""
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)


def _use_file_collector(directory: Path = FIXTURES_DIR):
    def factory(*, project_id, region, dump_raw_dir=None, **_kwargs):
        return FileCollector(directory, region=region)

    cli.COLLECTOR_FACTORY = factory


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_app_help(self):
        result = runner.invoke(cli.app, ["--help"])
        assert result.exit_code == 0

    def test_job_help(self):
        result = runner.invoke(cli.app, ["job", "--help"])
        assert result.exit_code == 0

    def test_scan_help(self):
        result = runner.invoke(cli.app, ["scan", "--help"])
        assert result.exit_code == 0

    def test_drill_help(self):
        result = runner.invoke(cli.app, ["drill", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# --dry-run-sql（認証情報なしで動くこと）
# ---------------------------------------------------------------------------


class TestDryRunSql:
    def test_job_dry_run_sql_no_credentials_needed(self):
        result = runner.invoke(
            cli.app,
            ["job", "job_abc", "-p", "my-project", "-r", "us", "--dry-run-sql"],
        )
        assert result.exit_code == 0
        assert "creation_time >=" in result.stdout

    def test_scan_dry_run_sql(self):
        result = runner.invoke(
            cli.app,
            ["scan", "-p", "my-project", "-r", "us", "--dry-run-sql"],
        )
        assert result.exit_code == 0
        assert "creation_time >=" in result.stdout

    def test_drill_dry_run_sql(self):
        result = runner.invoke(
            cli.app,
            ["drill", "-p", "my-project", "-r", "us", "--dry-run-sql"],
        )
        assert result.exit_code == 0
        assert "creation_time >=" in result.stdout


# ---------------------------------------------------------------------------
# --format json / both
# ---------------------------------------------------------------------------


class TestFormatOutput:
    def test_format_json_parses_and_has_schema_version(self):
        _use_file_collector()
        result = runner.invoke(
            cli.app,
            [
                "job",
                "skewed_join",
                "-p",
                "my-project",
                "-r",
                "us",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.stdout
        report = json.loads(result.stdout)
        assert "schema_version" in report

    def test_format_both_writes_json_and_md(self, tmp_path):
        _use_file_collector()
        out_base = tmp_path / "report"
        result = runner.invoke(
            cli.app,
            [
                "job",
                "skewed_join",
                "-p",
                "my-project",
                "-r",
                "us",
                "--format",
                "both",
                "-o",
                str(out_base),
            ],
        )
        assert result.exit_code == 0, result.stdout
        json_path = out_base.with_suffix(".json")
        md_path = out_base.with_suffix(".md")
        assert json_path.exists()
        assert md_path.exists()
        report = json.loads(json_path.read_text(encoding="utf-8"))
        assert "schema_version" in report
        assert "skewed_join" in md_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# FileCollector 経由の end-to-end（GCP・モック無し）
# ---------------------------------------------------------------------------


class TestFileCollectorEndToEnd:
    def test_skewed_join_produces_finding_in_markdown(self):
        _use_file_collector()
        result = runner.invoke(
            cli.app,
            ["job", "skewed_join", "-p", "my-project", "-r", "us"],
        )
        assert result.exit_code == 0, result.stdout
        assert "skew" in result.stdout.lower() or "スキュー" in result.stdout


# ---------------------------------------------------------------------------
# --fail-on
# ---------------------------------------------------------------------------


class TestFailOn:
    def test_fail_on_critical_exits_10_when_critical_finding(self, tmp_path):
        # error_result を持つジョブを用意して job.error (critical) を発生させる。
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        data = json.loads((FIXTURES_DIR / "skewed_join.json").read_text(encoding="utf-8"))
        data["error_result"] = {"reason": "invalidQuery", "message": "boom"}
        data["has_error"] = True
        (fixture_dir / "job_with_error.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        _use_file_collector(fixture_dir)

        result_no_flag = runner.invoke(
            cli.app,
            ["job", "job_with_error", "-p", "my-project", "-r", "us"],
        )
        assert result_no_flag.exit_code == 0, result_no_flag.stdout

        result_fail_on = runner.invoke(
            cli.app,
            [
                "job",
                "job_with_error",
                "-p",
                "my-project",
                "-r",
                "us",
                "--fail-on",
                "critical",
            ],
        )
        assert result_fail_on.exit_code == 10, result_fail_on.stdout


# ---------------------------------------------------------------------------
# --config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_nonexistent_config_path_exits_2(self):
        _use_file_collector()
        result = runner.invoke(
            cli.app,
            [
                "job",
                "skewed_join",
                "-p",
                "my-project",
                "-r",
                "us",
                "--config",
                "/nonexistent/path/to/config.yaml",
            ],
        )
        assert result.exit_code == 2

    def test_unknown_threshold_key_shows_clear_error(self, tmp_path):
        _use_file_collector()
        bad_config = tmp_path / "bad_config.yaml"
        bad_config.write_text("version: 1\nskew:\n  totally_unknown_key: 1\n", encoding="utf-8")
        result = runner.invoke(
            cli.app,
            [
                "job",
                "skewed_join",
                "-p",
                "my-project",
                "-r",
                "us",
                "--config",
                str(bad_config),
            ],
        )
        assert result.exit_code != 0
        assert "totally_unknown_key" in result.output or "totally_unknown_key" in str(
            result.exception
        )


# ---------------------------------------------------------------------------
# --disable-rules
# ---------------------------------------------------------------------------


class TestDisableRules:
    def test_disable_rules_suppresses_skew_findings(self):
        _use_file_collector()
        result_enabled = runner.invoke(
            cli.app,
            ["job", "skewed_join", "-p", "my-project", "-r", "us", "--format", "json"],
        )
        assert result_enabled.exit_code == 0, result_enabled.stdout
        report_enabled = json.loads(result_enabled.stdout)
        rule_ids_enabled = {
            f["rule_id"] for f in report_enabled["jobs"][0]["findings"]
        }
        assert any(rid.startswith("skew.") for rid in rule_ids_enabled)

        result_disabled = runner.invoke(
            cli.app,
            [
                "job",
                "skewed_join",
                "-p",
                "my-project",
                "-r",
                "us",
                "--format",
                "json",
                "--disable-rules",
                "skew.*",
            ],
        )
        assert result_disabled.exit_code == 0, result_disabled.stdout
        report_disabled = json.loads(result_disabled.stdout)
        rule_ids_disabled = {
            f["rule_id"] for f in report_disabled["jobs"][0]["findings"]
        }
        assert not any(rid.startswith("skew.") for rid in rule_ids_disabled)


# ---------------------------------------------------------------------------
# job: JobNotFound / PermissionFallbackNeeded
# ---------------------------------------------------------------------------


class TestJobErrors:
    def test_job_not_found_exits_4(self):
        _use_file_collector()
        result = runner.invoke(
            cli.app,
            ["job", "does_not_exist_anywhere", "-p", "my-project", "-r", "us"],
        )
        assert result.exit_code == 4

    def test_permission_fallback_needed_with_no_fallback_exits_3(self):
        from bq_job_diagnose.errors import PermissionFallbackNeeded

        class _RaisingCollector:
            def fetch_job(self, job_id, *, created_on=None):
                raise PermissionFallbackNeeded("no listAll permission")

            def scan(self, **kwargs):
                raise PermissionFallbackNeeded("no listAll permission")

            def fetch_jobs(self, job_ids, *, start_time, end_time):
                raise PermissionFallbackNeeded("no listAll permission")

        def factory(*, project_id, region, dump_raw_dir=None, **_kwargs):
            return _RaisingCollector()

        cli.COLLECTOR_FACTORY = factory

        result = runner.invoke(
            cli.app,
            [
                "job",
                "job_abc",
                "-p",
                "my-project",
                "-r",
                "us",
                "--no-fallback",
            ],
        )
        assert result.exit_code == 3
