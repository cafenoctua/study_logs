"""bq-job-diagnose の CLI エントリポイント（Phase 11）。

このモジュールは「配線」のみを行う。診断ロジック（ルール実行・コスト試算・
レポート生成）はすべて既存モジュールに委譲し、ここには含めない。

Collector の構築は `COLLECTOR_FACTORY`（モジュールレベル変数）越しに行う。
テストは `FileCollector` を返すファクトリに差し替えることで、GCP アクセスや
`bigquery.Client` のモック無しにエンドツーエンドの検証ができる
（REVIEW_GUIDE.md 2.3 の方針）。
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

import typer

from bq_job_diagnose.collect.base import Collector, RankBy
from bq_job_diagnose.collect.sql import (
    build_job_sql,
    build_scan_sql,
)
from bq_job_diagnose.config import config_digest, load_thresholds
from bq_job_diagnose.errors import (
    JobNotFound,
    PermissionFallbackNeeded,
    RetentionFallbackNeeded,
)
from bq_job_diagnose.models import Diagnosis, Job, Severity
from bq_job_diagnose.report.json_report import (
    append_starvation_skip_if_needed,
    build_json_report,
)
from bq_job_diagnose.report.markdown_report import build_markdown_report

# ルールモジュールを import して登録を発火させる（`rules/__init__.py` は
# 個々のルールを import しない設計のため、専用モジュール経由で行う）。
from bq_job_diagnose.rules import run_rules
from bq_job_diagnose.rules.all import ALL_RULE_MODULES  # noqa: F401

app = typer.Typer(
    name="bq-job-diagnose",
    help="BigQuery ジョブのクエリプランとタイムラインから性能問題を決定論的に診断する CLI。",
    no_args_is_help=True,
)

_SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.WARNING: 1,
    Severity.ADVISORY: 2,
    Severity.INFO: 3,
}

_FAIL_ON_RANK = {
    "critical": _SEVERITY_RANK[Severity.CRITICAL],
    "warning": _SEVERITY_RANK[Severity.WARNING],
}

_EXIT_AUTH_PERMISSION = 3
_EXIT_JOB_NOT_FOUND = 4
_EXIT_FAIL_ON = 10


# ---------------------------------------------------------------------------
# Collector ファクトリ（DI ポイント）
# ---------------------------------------------------------------------------


def _default_collector_factory(
    *,
    project_id: str,
    region: str,
    dump_raw_dir: Path | None = None,
    use_jobs_api: bool = False,
) -> Collector:
    """本番用の Collector を構築する。

    `google.cloud.bigquery` の import はこの関数の中でのみ行う。
    `--dry-run-sql` やテストでこの関数が呼ばれない経路では GCP の依存が
    一切ロードされない。
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
# 共通ヘルパー
# ---------------------------------------------------------------------------


def _default_project_id() -> str:
    """ADC のデフォルトプロジェクトを解決する（`--project` 未指定時のみ呼ばれる）。"""
    import google.auth

    _, project = google.auth.default()
    if not project:
        raise typer.BadParameter(
            "--project が指定されておらず、ADC からデフォルトプロジェクトを解決できません"
        )
    return project


def _resolve_project_id(project: str | None) -> str:
    if project is not None:
        return project
    try:
        return _default_project_id()
    except Exception as exc:
        typer.echo(f"エラー: プロジェクトを解決できません: {exc}", err=True)
        raise typer.Exit(code=_EXIT_AUTH_PERMISSION) from exc


def _parse_enabled(rules: str | None) -> set[str] | None:
    """`--rules` から run_rules に渡す enabled パターン集合を作る。

    `--disable-rules` は「全ルール（`*`）から指定パターンを除外」という
    意味になるが、run_rules は肯定的な fnmatch パターン集合しか受け取れない
    ため、無効化は実行後に findings をフィルタする方式で実現する
    （`_filter_disabled` 参照）。
    """
    if rules is None:
        return None
    return {p.strip() for p in rules.split(",") if p.strip()}


def _disabled_patterns(disable_rules: str | None) -> set[str]:
    if disable_rules is None:
        return set()
    return {p.strip() for p in disable_rules.split(",") if p.strip()}


def _filter_disabled(
    findings: list[Any], skipped: list[Any], disabled: set[str]
) -> tuple[list[Any], list[Any]]:
    """`--disable-rules` にマッチする rule_id の Finding を除外する。

    REVIEW_GUIDE.md 1.6 の方針により、ユーザーが明示的に無効化したルールは
    `skipped_rules` に入れない（前提未達＝評価不能と、意図的な無効化を混同
    しないため）。
    """
    import fnmatch

    if not disabled:
        return findings, skipped

    def _is_disabled(rule_id: str) -> bool:
        return any(fnmatch.fnmatch(rule_id, pattern) for pattern in disabled)

    kept_findings = [f for f in findings if not _is_disabled(f.rule_id)]
    kept_skipped = [s for s in skipped if not _is_disabled(s.rule_id)]
    return kept_findings, kept_skipped


def _load_thresholds_or_exit(config: Path | None):
    if config is not None and not Path(config).exists():
        typer.echo(f"エラー: 設定ファイルが見つかりません: {config}", err=True)
        raise typer.Exit(code=2)
    try:
        return load_thresholds(config)
    except (ValueError, OSError) as exc:
        typer.echo(f"エラー: 設定ファイルが不正です: {exc}", err=True)
        raise typer.Exit(code=2) from None


def _max_severity_rank(findings: list[Any]) -> int | None:
    ranks = [_SEVERITY_RANK.get(f.severity, 99) for f in findings]
    return min(ranks) if ranks else None


def _emit_report(
    report: dict[str, Any],
    *,
    fmt: Literal["markdown", "json", "both"],
    output: Path | None,
) -> None:
    if fmt == "json":
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if output is None:
            typer.echo(text)
        else:
            output.write_text(text, encoding="utf-8")
        return

    if fmt == "markdown":
        text = build_markdown_report(report)
        if output is None:
            typer.echo(text)
        else:
            output.write_text(text, encoding="utf-8")
        return

    # both
    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    md_text = build_markdown_report(report)
    if output is None:
        typer.echo(json_text)
        typer.echo(md_text)
        return
    output.with_suffix(".json").write_text(json_text, encoding="utf-8")
    output.with_suffix(".md").write_text(md_text, encoding="utf-8")


def _build_diagnosis(job: Job, thresholds, *, enabled, disabled: set[str]) -> Diagnosis:
    findings, skipped = run_rules(job, thresholds, enabled=enabled)
    findings, skipped = _filter_disabled(findings, skipped, disabled)
    skipped = append_starvation_skip_if_needed(job, findings, skipped)
    return Diagnosis(
        job=job,
        findings=tuple(findings),
        skipped_rules=tuple(skipped),
        generated_at=datetime.now(tz=UTC),
        config_digest=config_digest(thresholds),
    )


def _since_to_range(since: str | None, from_: str | None, to: str | None) -> tuple[datetime, datetime]:
    """`--since` または `--from`/`--to` から (start_time, end_time) を組み立てる。"""
    now = datetime.now(tz=UTC)
    if since is not None:
        if not since.endswith("d"):
            raise typer.BadParameter(
                f"--since は '7d' のような日数指定のみサポートします: {since!r}"
            )
        try:
            days = int(since[:-1])
        except ValueError as exc:
            raise typer.BadParameter(f"--since の形式が不正です: {since!r}") from exc
        return now - timedelta(days=days), now

    if from_ is not None and to is not None:
        try:
            start = datetime.fromisoformat(from_)
            end = datetime.fromisoformat(to)
        except ValueError as exc:
            raise typer.BadParameter(f"--from/--to は ISO8601 形式である必要があります: {exc}") from exc
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        return start, end

    # デフォルト: 7日間。
    return now - timedelta(days=7), now


# ---------------------------------------------------------------------------
# job コマンド
# ---------------------------------------------------------------------------


@app.callback()
def main() -> None:
    """BigQuery ジョブのクエリプランとタイムラインから性能問題を決定論的に診断する CLI。"""


@app.command("job")
def job_cmd(
    job_id: Annotated[str, typer.Argument(help="診断対象の job_id。")],
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="GCP プロジェクトID（省略時は ADC のデフォルト）。")
    ] = None,
    region: Annotated[str, typer.Option("--region", "-r", help="BigQuery region（例: us, asia-northeast1）。")] = "us",
    config: Annotated[
        Path | None, typer.Option("--config", help="閾値設定 YAML へのパス。")
    ] = None,
    format_: Annotated[
        str, typer.Option("--format", help="出力形式（markdown/json/both）。")
    ] = "markdown",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="出力先（省略時は標準出力。both の場合は拡張子なしのベース名）。")
    ] = None,
    rules: Annotated[
        str | None, typer.Option("--rules", help="実行するルールの fnmatch パターン（カンマ区切り）。")
    ] = None,
    disable_rules: Annotated[
        str | None, typer.Option("--disable-rules", help="無効化するルールの fnmatch パターン（カンマ区切り）。")
    ] = None,
    no_fallback: Annotated[
        bool, typer.Option("--no-fallback", help="jobs.get へのフォールバックを行わない。")
    ] = False,
    dry_run_sql: Annotated[
        bool, typer.Option("--dry-run-sql", help="実行される SQL とパラメータを表示して終了する（GCP にアクセスしない）。")
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="詳細メッセージを標準エラーに出力する。")] = False,
    fail_on: Annotated[
        str | None, typer.Option("--fail-on", help="指定した重大度以上の所見があれば終了コード10で終了する（critical/warning）。")
    ] = None,
    dump_raw: Annotated[
        Path | None, typer.Option("--dump-raw", hidden=True, help="取得した生データの匿名化ダンプ先ディレクトリ。")
    ] = None,
    created_on: Annotated[
        str | None, typer.Option("--created-on", help="ジョブの実行日（YYYY-MM-DD）。分かっていれば検索を高速化できる。")
    ] = None,
    stage_limit: Annotated[
        int, typer.Option("--stage-limit", help="レポートに含めるステージ数の上限。")
    ] = 15,
) -> None:
    """単一ジョブを深掘り診断する。"""
    if fail_on is not None and fail_on not in _FAIL_ON_RANK:
        typer.echo(f"エラー: --fail-on は critical か warning のみ指定できます: {fail_on!r}", err=True)
        raise typer.Exit(code=2)

    created_on_date: date | None = None
    if created_on is not None:
        try:
            created_on_date = date.fromisoformat(created_on)
        except ValueError as exc:
            typer.echo(f"エラー: --created-on は YYYY-MM-DD 形式で指定してください: {exc}", err=True)
            raise typer.Exit(code=2) from None

    if dry_run_sql:
        project_id = project if project is not None else "PROJECT_ID_PLACEHOLDER"
        now = datetime.now(tz=UTC)
        if created_on_date is not None:
            base = datetime(created_on_date.year, created_on_date.month, created_on_date.day, tzinfo=UTC)
            lower, upper = base - timedelta(days=1), base + timedelta(days=1)
        else:
            lower, upper = now - timedelta(days=7), now
        sql, params = build_job_sql(
            project_id=project_id,
            region=region,
            job_id=job_id,
            creation_time_lower=lower,
            creation_time_upper=upper,
        )
        typer.echo(sql)
        typer.echo(f"-- params: {_format_params(params)}")
        raise typer.Exit(code=0)

    project_id = _resolve_project_id(project)
    thresholds = _load_thresholds_or_exit(config)
    enabled = _parse_enabled(rules)
    disabled = _disabled_patterns(disable_rules)

    collector = _make_collector(project_id=project_id, region=region, dump_raw_dir=dump_raw)

    try:
        job = collector.fetch_job(job_id, created_on=created_on_date)
    except JobNotFound as exc:
        typer.echo(f"エラー: ジョブが見つかりません: {exc}", err=True)
        raise typer.Exit(code=_EXIT_JOB_NOT_FOUND) from None
    except (PermissionFallbackNeeded, RetentionFallbackNeeded) as exc:
        if no_fallback:
            typer.echo(f"エラー: {exc}", err=True)
            raise typer.Exit(code=_EXIT_AUTH_PERMISSION) from None
        if verbose:
            typer.echo(
                "[bq-job-diagnose] INFORMATION_SCHEMA から取得できないため jobs.get にフォールバックします...",
                err=True,
            )
        fallback_collector = _make_collector(
            project_id=project_id, region=region, dump_raw_dir=dump_raw, use_jobs_api=True
        )
        try:
            job = fallback_collector.fetch_job(job_id, created_on=created_on_date)
        except JobNotFound as exc2:
            typer.echo(f"エラー: ジョブが見つかりません: {exc2}", err=True)
            raise typer.Exit(code=_EXIT_JOB_NOT_FOUND) from None

    if job is None:
        typer.echo(f"エラー: ジョブが見つかりません: job_id={job_id!r}", err=True)
        raise typer.Exit(code=_EXIT_JOB_NOT_FOUND)

    diag = _build_diagnosis(job, thresholds, enabled=enabled, disabled=disabled)
    report = build_json_report(
        mode="job",
        diagnoses=[diag],
        generated_at=diag.generated_at,
        config_digest=diag.config_digest,
        thresholds=thresholds,
    )

    _emit_report(report, fmt=_validate_format(format_), output=output)
    _exit_for_fail_on(diag.findings, fail_on)


def _format_params(params) -> str:
    parts = []
    for p in params:
        name = p.name
        value = getattr(p, "value", None)
        if value is None:
            value = getattr(p, "values", None)
        parts.append(f"{name}={value!r}")
    return ", ".join(parts)


def _validate_format(format_: str) -> Literal["markdown", "json", "both"]:
    if format_ not in ("markdown", "json", "both"):
        typer.echo(f"エラー: --format は markdown/json/both のいずれかです: {format_!r}", err=True)
        raise typer.Exit(code=2)
    return format_  # type: ignore[return-value]


def _exit_for_fail_on(findings, fail_on: str | None) -> None:
    if fail_on is None:
        return
    threshold_rank = _FAIL_ON_RANK[fail_on]
    max_rank = _max_severity_rank(list(findings))
    if max_rank is not None and max_rank <= threshold_rank:
        raise typer.Exit(code=_EXIT_FAIL_ON)


# ---------------------------------------------------------------------------
# scan コマンド
# ---------------------------------------------------------------------------


@app.command("scan")
def scan_cmd(
    project: Annotated[str | None, typer.Option("--project", "-p", help="GCP プロジェクトID（省略時は ADC のデフォルト）。")] = None,
    region: Annotated[str, typer.Option("--region", "-r", help="BigQuery region。")] = "us",
    config: Annotated[Path | None, typer.Option("--config", help="閾値設定 YAML へのパス。")] = None,
    format_: Annotated[str, typer.Option("--format", help="出力形式（markdown/json/both）。")] = "markdown",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="出力先。")] = None,
    rules: Annotated[str | None, typer.Option("--rules", help="実行するルールの fnmatch パターン（カンマ区切り）。")] = None,
    disable_rules: Annotated[str | None, typer.Option("--disable-rules", help="無効化するルールの fnmatch パターン。")] = None,
    no_fallback: Annotated[bool, typer.Option("--no-fallback", help="（scan では常にフォールバックしない）")] = False,
    dry_run_sql: Annotated[bool, typer.Option("--dry-run-sql", help="実行される SQL を表示して終了する。")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="詳細メッセージを標準エラーに出力する。")] = False,
    fail_on: Annotated[str | None, typer.Option("--fail-on", help="重大度しきい値（critical/warning）。")] = None,
    dump_raw: Annotated[Path | None, typer.Option("--dump-raw", hidden=True)] = None,
    since: Annotated[str | None, typer.Option("--since", help="相対期間（例: 7d）。")] = None,
    from_: Annotated[str | None, typer.Option("--from", help="開始日時（ISO8601）。")] = None,
    to: Annotated[str | None, typer.Option("--to", help="終了日時（ISO8601）。")] = None,
    top_n: Annotated[int | None, typer.Option("--top-n", help="上位N件（省略時は設定ファイルの既定値）。")] = None,
    rank_by: Annotated[str | None, typer.Option("--rank-by", help="ランキング基準（slot_ms/bytes_billed/elapsed）。")] = None,
    user: Annotated[str | None, typer.Option("--user", help="user_email で絞り込む。")] = None,
    min_slot_ms: Annotated[int | None, typer.Option("--min-slot-ms", help="total_slot_ms の下限で絞り込む。")] = None,
) -> None:
    """期間スキャンで TopN のジョブを一覧する（plan が必要なルールは評価対象外）。"""
    thresholds_for_dry_run = None
    if dry_run_sql:
        project_id = project if project is not None else "PROJECT_ID_PLACEHOLDER"
        start_time, end_time = _since_to_range(since, from_, to)
        thresholds_for_dry_run = _load_thresholds_or_exit(config)
        resolved_top_n = top_n if top_n is not None else thresholds_for_dry_run.scan.default_top_n
        resolved_rank_by: RankBy = (rank_by or thresholds_for_dry_run.scan.default_rank_by)  # type: ignore[assignment]
        sql, params = build_scan_sql(
            project_id=project_id,
            region=region,
            start_time=start_time,
            end_time=end_time,
            top_n=resolved_top_n,
            rank_by=resolved_rank_by,
            user_email=user,
            min_slot_ms=min_slot_ms,
        )
        typer.echo(sql)
        typer.echo(f"-- params: {_format_params(params)}")
        raise typer.Exit(code=0)

    project_id = _resolve_project_id(project)
    thresholds = _load_thresholds_or_exit(config)
    # scan は ScanRow（plan なし）しか返さないため findings は発生せず、
    # --rules / --disable-rules は scan には意味を持たない
    # （job / drill と引数の形を揃えるためだけに受け取っている）。

    start_time, end_time = _since_to_range(since, from_, to)
    resolved_top_n = top_n if top_n is not None else thresholds.scan.default_top_n
    resolved_rank_by: RankBy = (rank_by or thresholds.scan.default_rank_by)  # type: ignore[assignment]

    collector = _make_collector(project_id=project_id, region=region, dump_raw_dir=dump_raw)

    try:
        rows = collector.scan(
            start_time=start_time,
            end_time=end_time,
            top_n=resolved_top_n,
            rank_by=resolved_rank_by,
            user_email=user,
            min_slot_ms=min_slot_ms,
        )
    except PermissionFallbackNeeded as exc:
        typer.echo(
            "エラー: scan には bigquery.jobs.listAll 権限が必要です。"
            f"（{exc}）"
            " 個別ジョブの診断には `job <ID>` を使用してください。",
            err=True,
        )
        raise typer.Exit(code=_EXIT_AUTH_PERMISSION) from None

    # scan は ScanRow（plan なし）しか返さないため、diagnoses は生成しない。
    # plan を要求するルールはすべて構造的に評価不能であり、JSON レポートは
    # scan_summary として TopN 一覧を出力する。
    scan_summary = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "top_n": resolved_top_n,
        "rank_by": resolved_rank_by,
        "row_count": len(rows),
        "rows": [_scan_row_to_dict(r) for r in rows],
    }

    report = build_json_report(
        mode="scan",
        diagnoses=[],
        scan_summary=scan_summary,
        generated_at=datetime.now(tz=UTC),
        config_digest=config_digest(thresholds),
        thresholds=thresholds,
    )
    _emit_report(report, fmt=_validate_format(format_), output=output)
    # scan には findings が存在しない（plan 前提のルールが全て評価不能）ため
    # --fail-on は常に該当なし（exit 0）。


def _scan_row_to_dict(row) -> dict[str, Any]:
    from dataclasses import asdict

    d = asdict(row)
    if isinstance(d.get("creation_time"), datetime):
        d["creation_time"] = d["creation_time"].isoformat()
    return d


# ---------------------------------------------------------------------------
# drill コマンド
# ---------------------------------------------------------------------------

_DRILL_TOP_N_CAP = 50


@app.command("drill")
def drill_cmd(
    project: Annotated[str | None, typer.Option("--project", "-p", help="GCP プロジェクトID（省略時は ADC のデフォルト）。")] = None,
    region: Annotated[str, typer.Option("--region", "-r", help="BigQuery region。")] = "us",
    config: Annotated[Path | None, typer.Option("--config", help="閾値設定 YAML へのパス。")] = None,
    format_: Annotated[str, typer.Option("--format", help="出力形式（markdown/json/both）。")] = "markdown",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="出力先。")] = None,
    rules: Annotated[str | None, typer.Option("--rules", help="実行するルールの fnmatch パターン（カンマ区切り）。")] = None,
    disable_rules: Annotated[str | None, typer.Option("--disable-rules", help="無効化するルールの fnmatch パターン。")] = None,
    no_fallback: Annotated[bool, typer.Option("--no-fallback", help="jobs.get へのフォールバックを行わない。")] = False,
    dry_run_sql: Annotated[bool, typer.Option("--dry-run-sql", help="実行される SQL を表示して終了する。")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="詳細メッセージを標準エラーに出力する。")] = False,
    fail_on: Annotated[str | None, typer.Option("--fail-on", help="重大度しきい値（critical/warning）。")] = None,
    dump_raw: Annotated[Path | None, typer.Option("--dump-raw", hidden=True)] = None,
    since: Annotated[str | None, typer.Option("--since", help="相対期間（例: 7d）。")] = None,
    from_: Annotated[str | None, typer.Option("--from", help="開始日時（ISO8601）。")] = None,
    to: Annotated[str | None, typer.Option("--to", help="終了日時（ISO8601）。")] = None,
    top_n: Annotated[int | None, typer.Option("--top-n", help="上位N件（上限50、省略時は設定ファイルの既定値）。")] = None,
    rank_by: Annotated[str | None, typer.Option("--rank-by", help="ランキング基準。")] = None,
    user: Annotated[str | None, typer.Option("--user", help="user_email で絞り込む。")] = None,
    min_slot_ms: Annotated[int | None, typer.Option("--min-slot-ms", help="total_slot_ms の下限で絞り込む。")] = None,
    from_scan: Annotated[
        Path | None, typer.Option("--from-scan", help="保存済み scan JSON から GCP にアクセスせず再診断する。")
    ] = None,
) -> None:
    """TopN のジョブそれぞれに対してフル診断を行う。"""
    if fail_on is not None and fail_on not in _FAIL_ON_RANK:
        typer.echo(f"エラー: --fail-on は critical か warning のみ指定できます: {fail_on!r}", err=True)
        raise typer.Exit(code=2)

    if dry_run_sql:
        project_id = project if project is not None else "PROJECT_ID_PLACEHOLDER"
        start_time, end_time = _since_to_range(since, from_, to)
        # drill は scan → fetch_jobs（build_drill_sql）の2段構え。
        # dry-run では scan の SQL を代表として表示する（実行時と同じ最初の
        # クエリ）。job_ids が未確定な段階では drill SQL は組み立てられない。
        thresholds_for_dry_run = _load_thresholds_or_exit(config)
        resolved_top_n = min(
            top_n if top_n is not None else thresholds_for_dry_run.scan.default_top_n,
            _DRILL_TOP_N_CAP,
        )
        resolved_rank_by: RankBy = (rank_by or thresholds_for_dry_run.scan.default_rank_by)  # type: ignore[assignment]
        sql, params = build_scan_sql(
            project_id=project_id,
            region=region,
            start_time=start_time,
            end_time=end_time,
            top_n=resolved_top_n,
            rank_by=resolved_rank_by,
            user_email=user,
            min_slot_ms=min_slot_ms,
        )
        typer.echo(sql)
        typer.echo(f"-- params: {_format_params(params)}")
        typer.echo(
            "-- drill は上記 scan で得た job_id 群に対して build_drill_sql を"
            " さらに実行します（job_id が未確定のためここでは表示できません）。"
        )
        raise typer.Exit(code=0)

    thresholds = _load_thresholds_or_exit(config)
    enabled = _parse_enabled(rules)
    disabled = _disabled_patterns(disable_rules)

    if from_scan is not None:
        jobs = _jobs_from_scan_file(from_scan, region=region)
    else:
        project_id = _resolve_project_id(project)
        start_time, end_time = _since_to_range(since, from_, to)
        resolved_top_n = min(
            top_n if top_n is not None else thresholds.scan.default_top_n,
            _DRILL_TOP_N_CAP,
        )
        resolved_rank_by: RankBy = (rank_by or thresholds.scan.default_rank_by)  # type: ignore[assignment]

        collector = _make_collector(project_id=project_id, region=region, dump_raw_dir=dump_raw)
        try:
            rows = collector.scan(
                start_time=start_time,
                end_time=end_time,
                top_n=resolved_top_n,
                rank_by=resolved_rank_by,
                user_email=user,
                min_slot_ms=min_slot_ms,
            )
        except PermissionFallbackNeeded as exc:
            typer.echo(
                f"エラー: scan には bigquery.jobs.listAll 権限が必要です（{exc}）。"
                " 個別ジョブの診断には `job <ID>` を使用してください。",
                err=True,
            )
            raise typer.Exit(code=_EXIT_AUTH_PERMISSION) from None

        job_ids = [r.job_id for r in rows]
        if not job_ids:
            jobs = []
        else:
            jobs = collector.fetch_jobs(job_ids, start_time=start_time, end_time=end_time)

    diagnoses = [
        _build_diagnosis(job, thresholds, enabled=enabled, disabled=disabled) for job in jobs
    ]
    report = build_json_report(
        mode="drill",
        diagnoses=diagnoses,
        generated_at=datetime.now(tz=UTC),
        config_digest=config_digest(thresholds),
        thresholds=thresholds,
    )
    _emit_report(report, fmt=_validate_format(format_), output=output)

    all_findings = [f for diag in diagnoses for f in diag.findings]
    _exit_for_fail_on(all_findings, fail_on)


def _jobs_from_scan_file(path: Path, *, region: str) -> list[Job]:
    """`--from-scan` 用: 保存済み scan JSON レポートの job_id 一覧を使い、
    `COLLECTOR_FACTORY` から作った Collector の `fetch_jobs` でフル診断分の
    `Job` を再取得する（scan 自体は再実行しない＝GCP の scan API には触れない）。

    `project_id` は scan 結果に含まれないため、Collector 構築のためだけの
    ダミー値を渡す（`fetch_jobs` は job_id 群のみで一意に引けるため実害はない）。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    scan_summary = data.get("scan_summary")
    if scan_summary is None:
        raise typer.BadParameter(f"{path} は scan_summary を含む JSON レポートである必要があります")

    job_ids = [r["job_id"] for r in scan_summary.get("rows", [])]
    if not job_ids:
        return []

    start_time = datetime.fromisoformat(scan_summary["start_time"])
    end_time = datetime.fromisoformat(scan_summary["end_time"])

    collector = _make_collector(project_id="from-scan", region=region)
    return collector.fetch_jobs(job_ids, start_time=start_time, end_time=end_time)


if __name__ == "__main__":
    app()
