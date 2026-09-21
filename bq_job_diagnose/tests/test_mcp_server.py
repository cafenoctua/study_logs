"""mcp_server（Phase: MCP Apps 対応）のテスト。

TDD: このテストを先に書き、失敗することを確認してから mcp_server を実装する。

制約（重要）:
- GCP アクセス・ネットワークアクセスを一切行わない。
- `google.cloud.bigquery.Client` をモックしない（REVIEW_GUIDE.md 2.3）。
  `FileCollector` + フィクスチャで実データ形状を通す。
- ツールは async 関数として実装されるため、`asyncio.run` で直接呼び出すか
  `MCPServer.call_tool` 経由で呼び出す。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from bq_job_diagnose.collect.base import ScanRow
from bq_job_diagnose.collect.file_collector import FileCollector
from bq_job_diagnose.errors import JobNotFound, PermissionFallbackNeeded

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "is_rows"


# ---------------------------------------------------------------------------
# テスト用 Collector
# ---------------------------------------------------------------------------


class _ScanCapableFileCollector:
    """`FileCollector` をラップし、テスト用に `scan()` を実装したもの。

    `FileCollector` は「ローカルファイルには期間スキャンの概念がない」ため
    `scan()` が `NotImplementedError` を送出する設計（本体は変更しない）。
    scan_jobs / drill_jobs ツールのテストのためだけに、フィクスチャ
    ディレクトリ内の全ジョブを ScanRow 化して返す薄いラッパーをここで用意する。
    """

    def __init__(self, directory: Path, *, region: str) -> None:
        self._inner = FileCollector(directory, region=region)
        self._directory = Path(directory)
        self._region = region

    def fetch_job(self, job_id: str, *, created_on=None):
        return self._inner.fetch_job(job_id, created_on=created_on)

    def fetch_jobs(self, job_ids, *, start_time, end_time):
        return self._inner.fetch_jobs(job_ids, start_time=start_time, end_time=end_time)

    def scan(
        self,
        *,
        start_time,
        end_time,
        top_n,
        rank_by,
        user_email=None,
        min_slot_ms=None,
    ) -> list[ScanRow]:
        rows: list[ScanRow] = []
        for path in sorted(self._directory.glob("*.json")):
            job = self._inner.fetch_job(path.stem)
            if job is None:
                continue
            rows.append(
                ScanRow(
                    job_id=job.job_id,
                    project_id=job.project_id,
                    parent_job_id=job.parent_job_id,
                    user_email=job.user_email,
                    creation_time=job.creation_time,
                    elapsed_ms=job.elapsed_ms,
                    total_slot_ms=job.total_slot_ms,
                    total_bytes_billed=job.total_bytes_billed,
                    cache_hit=job.cache_hit,
                    statement_type=job.statement_type,
                    query_head=(job.query or "")[:80] if job.query else None,
                    has_error=job.error_result is not None,
                    edition=job.edition,
                    reservation_id=job.reservation_id,
                    resource_warning=job.resource_warning,
                    normalized_literals_hash=job.normalized_literals_hash,
                    referenced_table_count=job.referenced_table_count
                    if hasattr(job, "referenced_table_count")
                    else len(job.referenced_tables),
                    state=job.state,
                    priority=job.priority,
                    job_type=job.job_type,
                )
            )
        return rows[:top_n]


class _RaisingCollector:
    """常に指定の例外を送出する Collector（エラーマッピングのテスト用）。"""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def fetch_job(self, job_id, *, created_on=None):
        raise self._exc

    def scan(self, **kwargs):
        raise self._exc

    def fetch_jobs(self, job_ids, *, start_time, end_time):
        raise self._exc


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _reset_collector_factory():
    from bq_job_diagnose.mcp_server import server as mcp_server_module

    original = mcp_server_module.COLLECTOR_FACTORY
    yield
    mcp_server_module.COLLECTOR_FACTORY = original


def _use_file_collector(directory: Path = FIXTURES_DIR):
    from bq_job_diagnose.mcp_server import server as mcp_server_module

    def factory(*, project_id, region, **_kwargs):
        return FileCollector(directory, region=region)

    mcp_server_module.COLLECTOR_FACTORY = factory


def _use_scan_capable_collector(directory: Path = FIXTURES_DIR):
    from bq_job_diagnose.mcp_server import server as mcp_server_module

    def factory(*, project_id, region, **_kwargs):
        return _ScanCapableFileCollector(directory, region=region)

    mcp_server_module.COLLECTOR_FACTORY = factory


def _use_raising_collector(exc: Exception):
    from bq_job_diagnose.mcp_server import server as mcp_server_module

    def factory(*, project_id, region, **_kwargs):
        return _RaisingCollector(exc)

    mcp_server_module.COLLECTOR_FACTORY = factory


# ---------------------------------------------------------------------------
# diagnose_job
# ---------------------------------------------------------------------------


class TestDiagnoseJob:
    def test_returns_dict_with_schema_version_first(self):
        _use_file_collector()
        from bq_job_diagnose.mcp_server.server import diagnose_job

        result = _run(diagnose_job(job_id="skewed_join", project="my-project", region="us"))

        assert isinstance(result, dict)
        assert next(iter(result.keys())) == "schema_version"
        # json.dumps できること
        json.dumps(result, ensure_ascii=False)

    def test_skewed_join_yields_skew_finding(self):
        _use_file_collector()
        from bq_job_diagnose.mcp_server.server import diagnose_job

        result = _run(diagnose_job(job_id="skewed_join", project="my-project", region="us"))

        rule_ids = {f["rule_id"] for job in result["jobs"] for f in job["findings"]}
        assert "skew.compute_time" in rule_ids

    def test_job_not_found_raises_tool_error_mentioning_not_found(self):
        _use_raising_collector(JobNotFound("job_id=does_not_exist"))
        from mcp.server.mcpserver.exceptions import ToolError

        from bq_job_diagnose.mcp_server.server import diagnose_job

        with pytest.raises(ToolError) as excinfo:
            _run(diagnose_job(job_id="does_not_exist", project="my-project", region="us"))
        message = str(excinfo.value)
        assert "見つかりません" in message or "not found" in message.lower()


# ---------------------------------------------------------------------------
# scan_jobs
# ---------------------------------------------------------------------------


class TestScanJobs:
    def test_returns_dict_with_schema_version_first(self):
        _use_scan_capable_collector()
        from bq_job_diagnose.mcp_server.server import scan_jobs

        result = _run(
            scan_jobs(project="my-project", region="us", since_days=7, top_n=20, rank_by="slot_ms")
        )

        assert isinstance(result, dict)
        assert next(iter(result.keys())) == "schema_version"
        json.dumps(result, ensure_ascii=False)
        assert result["mode"] == "scan"
        assert result["scan_summary"] is not None

    def test_permission_fallback_needed_tells_user_to_use_diagnose_job(self):
        _use_raising_collector(PermissionFallbackNeeded("no listAll"))
        from mcp.server.mcpserver.exceptions import ToolError

        from bq_job_diagnose.mcp_server.server import scan_jobs

        with pytest.raises(ToolError) as excinfo:
            _run(scan_jobs(project="my-project", region="us"))
        message = str(excinfo.value)
        assert "diagnose_job" in message


# ---------------------------------------------------------------------------
# drill_jobs
# ---------------------------------------------------------------------------


class TestDrillJobs:
    def test_returns_dict_with_schema_version_first(self):
        _use_scan_capable_collector()
        from bq_job_diagnose.mcp_server.server import drill_jobs

        result = _run(drill_jobs(project="my-project", region="us", since_days=7, top_n=5))

        assert isinstance(result, dict)
        assert next(iter(result.keys())) == "schema_version"
        json.dumps(result, ensure_ascii=False)
        assert result["mode"] == "drill"

    def test_permission_fallback_needed_tells_user_to_use_diagnose_job(self):
        _use_raising_collector(PermissionFallbackNeeded("no listAll"))
        from mcp.server.mcpserver.exceptions import ToolError

        from bq_job_diagnose.mcp_server.server import drill_jobs

        with pytest.raises(ToolError) as excinfo:
            _run(drill_jobs(project="my-project", region="us"))
        message = str(excinfo.value)
        assert "diagnose_job" in message


# ---------------------------------------------------------------------------
# MCP サーバー構成: ツール登録 / UI リソース
# ---------------------------------------------------------------------------


class TestServerRegistration:
    def _server(self):
        from bq_job_diagnose.mcp_server.server import build_server

        return build_server()

    def test_tools_registered_with_expected_names(self):
        mcp = self._server()
        tools = _run(mcp.list_tools())
        names = {t.name for t in tools}
        assert {"diagnose_job", "scan_jobs", "drill_jobs"} <= names

    def test_tools_have_ui_resource_uri_meta(self):
        mcp = self._server()
        tools = _run(mcp.list_tools())
        by_name = {t.name: t for t in tools}
        for name in ("diagnose_job", "scan_jobs", "drill_jobs"):
            tool = by_name[name]
            meta = tool.meta or {}
            assert meta.get("ui", {}).get("resourceUri") == "ui://bq-job-diagnose/report.html"

    def test_ui_resource_registered_with_expected_mime_type(self):
        mcp = self._server()
        resources = _run(mcp.list_resources())
        by_uri = {str(r.uri): r for r in resources}
        assert "ui://bq-job-diagnose/report.html" in by_uri
        resource = by_uri["ui://bq-job-diagnose/report.html"]
        assert resource.mime_type == "text/html;profile=mcp-app"

    def test_ui_html_references_no_external_resources(self):
        from bq_job_diagnose.mcp_server.server import REPORT_HTML

        assert "http://" not in REPORT_HTML
        assert "https://" not in REPORT_HTML
        assert "fetch(" not in REPORT_HTML

    def test_call_tool_diagnose_job_end_to_end(self):
        _use_file_collector()
        mcp = self._server()
        result = _run(
            mcp.call_tool(
                "diagnose_job",
                {"job_id": "skewed_join", "project": "my-project", "region": "us"},
            )
        )
        assert result is not None
