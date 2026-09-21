"""bq-job-diagnose の MCP サーバーエントリポイント。

このモジュールは「配線」のみを行う。診断ロジック（ルール実行・コスト試算・
レポート生成）はすべて既存モジュール（`rules/`, `cost.py`, `report/`）に
委譲し、ここには含めない（`cli.py` と同じ方針）。

Collector の構築は `COLLECTOR_FACTORY`（モジュールレベル変数）越しに行う。
テストは `FileCollector` を返すファクトリに差し替えることで、GCP アクセスや
`bigquery.Client` のモック無しにエンドツーエンドの検証ができる
（REVIEW_GUIDE.md 2.3 の方針。`cli.py` の `COLLECTOR_FACTORY` と同型）。

**重要**: このモジュールは stdout に `print()` してはならない。stdio
トランスポートは標準出力を JSON-RPC ストリームとして使うため、`print()` は
プロトコルを破壊する。ログは必ず標準エラー（`logging` の既定ハンドラ等）に
出す。
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from mcp.server.apps import Apps, ResourceCsp, client_supports_apps
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError

from bq_job_diagnose.collect.base import Collector
from bq_job_diagnose.config import config_digest, load_thresholds
from bq_job_diagnose.errors import (
    JobNotFound,
    PermissionFallbackNeeded,
    RetentionFallbackNeeded,
)
from bq_job_diagnose.models import Diagnosis, Job
from bq_job_diagnose.report.json_report import (
    append_starvation_skip_if_needed,
    build_json_report,
)

# ルールモジュールを import して登録を発火させる（`rules/__init__.py` は
# 個々のルールを import しない設計のため、専用モジュール経由で行う。
# cli.py と同じパターン）。
from bq_job_diagnose.rules import run_rules
from bq_job_diagnose.rules.all import ALL_RULE_MODULES  # noqa: F401

# stdout を汚さないよう、ロガーは標準エラーに出す。
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("bq_job_diagnose.mcp_server")

RankBy = Literal["slot_ms", "bytes_billed", "elapsed"]

_UI_RESOURCE_URI = "ui://bq-job-diagnose/report.html"

REPORT_HTML = (Path(__file__).parent / "report_ui.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Collector ファクトリ（DI ポイント。cli.py の COLLECTOR_FACTORY と同型）
# ---------------------------------------------------------------------------


def _default_collector_factory(
    *,
    project_id: str,
    region: str,
    dump_raw_dir: Path | None = None,
    use_jobs_api: bool = False,
) -> Collector:
    """本番用の Collector を構築する。

    `google.cloud.bigquery` の import はこの関数の中でのみ行う。テストで
    この関数が呼ばれない経路では GCP の依存が一切ロードされない。
    """
    from google.cloud import bigquery

    from bq_job_diagnose.collect.information_schema import InformationSchemaCollector
    from bq_job_diagnose.collect.jobs_api import JobsApiCollector

    client = bigquery.Client(project=project_id)
    if use_jobs_api:
        return JobsApiCollector(client, region=region, dump_raw_dir=dump_raw_dir)
    return InformationSchemaCollector(
        client, project_id=project_id, region=region, dump_raw_dir=dump_raw_dir
    )


# `Callable[..., Collector]` 相当。テストはこの変数を差し替える。
COLLECTOR_FACTORY = _default_collector_factory


def _make_collector(
    *,
    project_id: str,
    region: str,
    dump_raw_dir: Path | None = None,
    use_jobs_api: bool = False,
) -> Collector:
    return COLLECTOR_FACTORY(
        project_id=project_id,
        region=region,
        dump_raw_dir=dump_raw_dir,
        use_jobs_api=use_jobs_api,
    )


# ---------------------------------------------------------------------------
# 共通ヘルパー（cli.py の _build_diagnosis 等と同じロジックを再利用）
# ---------------------------------------------------------------------------


def _build_diagnosis(job: Job, thresholds) -> Diagnosis:
    findings, skipped = run_rules(job, thresholds)
    skipped = append_starvation_skip_if_needed(job, findings, skipped)
    return Diagnosis(
        job=job,
        findings=tuple(findings),
        skipped_rules=tuple(skipped),
        generated_at=datetime.now(tz=UTC),
        config_digest=config_digest(thresholds),
    )


def _since_days_to_range(since_days: int) -> tuple[datetime, datetime]:
    now = datetime.now(tz=UTC)
    return now - timedelta(days=since_days), now


def _scan_row_to_dict(row: Any) -> dict[str, Any]:
    from dataclasses import asdict

    d = asdict(row)
    if isinstance(d.get("creation_time"), datetime):
        d["creation_time"] = d["creation_time"].isoformat()
    return d


# ---------------------------------------------------------------------------
# 型付きエラー → ToolError マッピング
#
# CLI の終了コード（3=権限, 4=job not found）と同じ精神で、ユーザーが次に
# 何をすべきか分かるメッセージを ToolError に詰める。
# ---------------------------------------------------------------------------


def _job_not_found_error(job_id: str, exc: Exception) -> ToolError:
    return ToolError(
        f"ジョブが見つかりません（job_id={job_id!r}）: {exc}\n"
        "job_id・project・region の指定を確認してください。"
        " ジョブが180日以上前の場合は INFORMATION_SCHEMA の保持期間切れの可能性があります。"
    )


def _permission_fallback_error_for_scan(exc: Exception) -> ToolError:
    return ToolError(
        f"scan_jobs / drill_jobs には bigquery.jobs.listAll 権限が必要です（{exc}）。"
        " 個別ジョブの診断には diagnose_job を使用してください"
        "（jobs.get ベースのフォールバックが利用できます）。"
    )


# ---------------------------------------------------------------------------
# ツール実装
#
# それぞれ「収集 → ルール実行 → コスト試算 → レポート組み立て」という
# 既存パイプラインを呼ぶだけの配線。診断ロジック自体は一切持たない。
# ---------------------------------------------------------------------------


async def diagnose_job(
    job_id: str,
    project: str,
    region: str = "us",
    created_on: str | None = None,
) -> dict[str, Any]:
    """単一 BigQuery ジョブを深掘り診断する。

    クエリプランとタイムラインから性能問題（スキュー・フィルタ効率・
    スロット競合・スピル等）を決定論的に検出し、コスト試算（on-demand /
    Editions の両方）と合わせて JSON レポートを返す。

    INFORMATION_SCHEMA へのアクセス権限が無い場合や保持期間（180日）を
    過ぎている場合は、自動的に jobs.get ベースの経路にフォールバックする
    （`slot.starvation` ルールはこの経路では構造的に評価できず、
    `skipped_rules` にその旨が記録される）。
    """
    from datetime import date

    created_on_date: date | None = None
    if created_on is not None:
        try:
            created_on_date = date.fromisoformat(created_on)
        except ValueError as exc:
            raise ToolError(
                f"created_on は YYYY-MM-DD 形式で指定してください: {created_on!r}"
            ) from exc

    thresholds = load_thresholds()
    collector = _make_collector(project_id=project, region=region)

    try:
        job = collector.fetch_job(job_id, created_on=created_on_date)
    except JobNotFound as exc:
        raise _job_not_found_error(job_id, exc) from None
    except (PermissionFallbackNeeded, RetentionFallbackNeeded) as exc:
        logger.info(
            "INFORMATION_SCHEMA から取得できないため jobs.get にフォールバックします: %s",
            exc,
        )
        fallback_collector = _make_collector(project_id=project, region=region, use_jobs_api=True)
        try:
            job = fallback_collector.fetch_job(job_id, created_on=created_on_date)
        except JobNotFound as exc2:
            raise _job_not_found_error(job_id, exc2) from None

    if job is None:
        raise _job_not_found_error(job_id, JobNotFound(f"job_id={job_id!r}"))

    diag = _build_diagnosis(job, thresholds)
    return build_json_report(
        mode="job",
        diagnoses=[diag],
        generated_at=diag.generated_at,
        config_digest=diag.config_digest,
        thresholds=thresholds,
    )


async def scan_jobs(
    project: str,
    region: str = "us",
    since_days: int = 7,
    top_n: int = 20,
    rank_by: RankBy = "slot_ms",
) -> dict[str, Any]:
    """期間内の BigQuery ジョブを rank_by 基準で TopN 一覧する。

    `bigquery.jobs.listAll` 権限が必須（構造的に jobs.get へはフォールバック
    しない）。クエリプランを取得しないため、プラン前提のルールは評価対象外
    （TopN のジョブ一覧のみを返す）。
    """
    thresholds = load_thresholds()
    start_time, end_time = _since_days_to_range(since_days)
    collector = _make_collector(project_id=project, region=region)

    try:
        rows = collector.scan(
            start_time=start_time,
            end_time=end_time,
            top_n=top_n,
            rank_by=rank_by,
        )
    except PermissionFallbackNeeded as exc:
        raise _permission_fallback_error_for_scan(exc) from None

    scan_summary = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "top_n": top_n,
        "rank_by": rank_by,
        "row_count": len(rows),
        "rows": [_scan_row_to_dict(r) for r in rows],
    }

    return build_json_report(
        mode="scan",
        diagnoses=[],
        scan_summary=scan_summary,
        generated_at=datetime.now(tz=UTC),
        config_digest=config_digest(thresholds),
        thresholds=thresholds,
    )


async def drill_jobs(
    project: str,
    region: str = "us",
    since_days: int = 7,
    top_n: int = 5,
) -> dict[str, Any]:
    """期間スキャンで得た TopN のジョブそれぞれに対してフル診断を行う。

    `scan_jobs` と同様、`bigquery.jobs.listAll` 権限が必須。TopN のジョブ
    それぞれについて `diagnose_job` と同じ診断パイプラインを実行する。
    """
    thresholds = load_thresholds()
    start_time, end_time = _since_days_to_range(since_days)
    collector = _make_collector(project_id=project, region=region)

    try:
        rows = collector.scan(
            start_time=start_time,
            end_time=end_time,
            top_n=top_n,
            rank_by="slot_ms",
        )
    except PermissionFallbackNeeded as exc:
        raise _permission_fallback_error_for_scan(exc) from None

    job_ids = [r.job_id for r in rows]
    jobs = collector.fetch_jobs(job_ids, start_time=start_time, end_time=end_time) if job_ids else []

    diagnoses = [_build_diagnosis(job, thresholds) for job in jobs]
    return build_json_report(
        mode="drill",
        diagnoses=diagnoses,
        generated_at=datetime.now(tz=UTC),
        config_digest=config_digest(thresholds),
        thresholds=thresholds,
    )


# ---------------------------------------------------------------------------
# MCP Apps 対応ラッパー
#
# `client_supports_apps(ctx)` で判定し、対応していないホストにはテキスト/
# 構造化データのみを返す（UI 無しでも意味のある応答になるよう退化させる）。
# 対応しているホストには同じ dict を structured content として返せば、
# `_meta.ui.resourceUri` を見た host 側が UI へ流し込む。
# ---------------------------------------------------------------------------


def _client_supports_apps_safely(ctx: Context | None) -> bool:
    """`client_supports_apps` の安全なラッパー。

    実クライアントとのリクエスト中でない Context（テストからの直接呼び出しや、
    将来的なバッチ処理経路など）では `ctx.client_capabilities` へのアクセスが
    `ValueError` を送出する。この状況は「Apps 未対応」と同じ扱い（テキスト/
    構造化データのみ返す）にし、クラッシュさせない。
    """
    if ctx is None:
        return False
    try:
        return client_supports_apps(ctx)
    except ValueError:
        return False


def build_server() -> MCPServer:
    """MCPServer インスタンスを構築する（テスト・CLI 起動の両方から呼ばれる）。

    重要: `Apps` はツール/リソースの登録内容を `MCPServer.__init__` の中で
    （`extensions=[apps]` 経由で）読み取る。そのため `apps.tool(...)` /
    `apps.add_html_resource(...)` は **`MCPServer(...)` を構築するより前に**
    すべて呼び終えておく必要がある（後から追加しても反映されない）。
    """
    apps = Apps()

    apps.add_html_resource(
        _UI_RESOURCE_URI,
        REPORT_HTML,
        name="bq-job-diagnose レポート",
        title="bq-job-diagnose レポート",
        description="TopN 一覧とジョブ詳細（所見・コスト試算・ステージ）を表示する UI。",
        csp=ResourceCsp(),
    )

    @apps.tool(resource_uri=_UI_RESOURCE_URI, name="diagnose_job")
    async def _diagnose_job_tool(
        job_id: str,
        project: str,
        region: str = "us",
        created_on: str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """単一 BigQuery ジョブを深掘り診断する（クエリプラン・タイムラインから
        性能問題を決定論的に検出し、コスト試算と合わせて返す）。"""
        report = await diagnose_job(job_id=job_id, project=project, region=region, created_on=created_on)
        if not _client_supports_apps_safely(ctx):
            logger.info("client は MCP Apps 未対応のため、テキスト/構造化データのみ返します")
        return report

    @apps.tool(resource_uri=_UI_RESOURCE_URI, name="scan_jobs")
    async def _scan_jobs_tool(
        project: str,
        region: str = "us",
        since_days: int = 7,
        top_n: int = 20,
        rank_by: RankBy = "slot_ms",
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """期間内の BigQuery ジョブを rank_by 基準で TopN 一覧する。"""
        report = await scan_jobs(
            project=project, region=region, since_days=since_days, top_n=top_n, rank_by=rank_by
        )
        if not _client_supports_apps_safely(ctx):
            logger.info("client は MCP Apps 未対応のため、テキスト/構造化データのみ返します")
        return report

    @apps.tool(resource_uri=_UI_RESOURCE_URI, name="drill_jobs")
    async def _drill_jobs_tool(
        project: str,
        region: str = "us",
        since_days: int = 7,
        top_n: int = 5,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """期間スキャンで得た TopN のジョブそれぞれに対してフル診断を行う。"""
        report = await drill_jobs(project=project, region=region, since_days=since_days, top_n=top_n)
        if not _client_supports_apps_safely(ctx):
            logger.info("client は MCP Apps 未対応のため、テキスト/構造化データのみ返します")
        return report

    mcp = MCPServer(
        name="bq-job-diagnose",
        extensions=[apps],
    )
    return mcp


def main() -> None:
    """`bq-job-diagnose-mcp` エントリポイント。stdio トランスポートでサーバーを起動する。"""
    mcp = build_server()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
