"""`FileCollector` のテスト。

GCP アクセスなし・ネットワークなしで完走する（`tests/fixtures/` のフィクスチャを
そのまま読む）。既存の全フィクスチャ（`is_rows/` と `sdk_jobs/`）が正しく
`models.Job` へラウンドトリップすることを検証する。これは CLI 未満だが、
正規化層まで含めた実質的な統合テストになる。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bq_job_diagnose.collect.file_collector import FileCollector
from bq_job_diagnose.models import Job, Source

FIXTURES_DIR = Path(__file__).parent / "fixtures"
IS_ROWS_DIR = FIXTURES_DIR / "is_rows"
SDK_JOBS_DIR = FIXTURES_DIR / "sdk_jobs"


def _all_fixture_files() -> list[Path]:
    return sorted(IS_ROWS_DIR.glob("*.json")) + sorted(SDK_JOBS_DIR.glob("*.json"))


class TestFileCollectorRoundTripsAllFixtures:
    @pytest.mark.parametrize("fixture_path", _all_fixture_files(), ids=lambda p: p.stem)
    def test_fetch_job_normalizes_every_fixture(self, fixture_path: Path):
        # フィクスチャのファイル名（拡張子抜き）を job_id として渡せるように、
        # 各フィクスチャディレクトリを単独で束ねた FileCollector を使う。
        collector = FileCollector(fixture_path.parent, region="asia-northeast1")
        job = collector.fetch_job(fixture_path.stem)
        assert isinstance(job, Job)

    def test_is_rows_fixtures_normalize_with_information_schema_source(self):
        collector = FileCollector(IS_ROWS_DIR, region="asia-northeast1")
        job = collector.fetch_job("skewed_join")
        assert job is not None
        assert job.source is Source.INFORMATION_SCHEMA
        assert job.job_id == "job_skewed_join_001"

    def test_sdk_jobs_fixtures_normalize_with_jobs_api_source(self):
        collector = FileCollector(SDK_JOBS_DIR, region="asia-northeast1")
        job = collector.fetch_job("skewed_join")
        assert job is not None
        assert job.source is Source.JOBS_API
        assert job.job_id == "job_skewed_join_001"


class TestFileCollectorDetectsFormatByShape:
    def test_is_row_json_without_job_reference_key_detected_as_information_schema(self, tmp_path):
        (tmp_path / "sample.json").write_text(
            (IS_ROWS_DIR / "cache_hit.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        collector = FileCollector(tmp_path, region="asia-northeast1")
        job = collector.fetch_job("sample")
        assert job.source is Source.INFORMATION_SCHEMA

    def test_sdk_job_json_with_job_reference_key_detected_as_jobs_api(self, tmp_path):
        (tmp_path / "sample.json").write_text(
            (SDK_JOBS_DIR / "no_plan.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        collector = FileCollector(tmp_path, region="asia-northeast1")
        job = collector.fetch_job("sample")
        assert job.source is Source.JOBS_API


class TestFileCollectorMissingJob:
    def test_fetch_job_returns_none_when_file_does_not_exist(self, tmp_path):
        collector = FileCollector(tmp_path, region="asia-northeast1")
        assert collector.fetch_job("does_not_exist") is None


class TestFileCollectorUnsupportedOperations:
    def test_scan_raises_not_implemented_style_error(self):
        from datetime import UTC, datetime

        collector = FileCollector(IS_ROWS_DIR, region="asia-northeast1")
        with pytest.raises(Exception):  # noqa: B017 — 具体的な型は実装依存とし、送出のみ確認
            collector.scan(
                start_time=datetime(2026, 1, 1, tzinfo=UTC),
                end_time=datetime(2026, 1, 2, tzinfo=UTC),
                top_n=10,
                rank_by="slot_ms",
            )


class TestFileCollectorNoGoogleImport:
    """file_collector.py が google をトップレベルで import していないことを AST で検証する。"""

    def test_no_google_import_in_file_collector_module(self):
        import ast

        path = (
            Path(__file__).parent.parent
            / "src"
            / "bq_job_diagnose"
            / "collect"
            / "file_collector.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
                imported.add(node.module.split(".")[0])
        assert "google" not in imported
