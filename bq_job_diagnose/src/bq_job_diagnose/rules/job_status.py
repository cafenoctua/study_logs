"""ジョブステータス関連ルール（job.error / job.resource_warning）。

両ルールとも `Job` のトップレベルフィールドのみを参照し、クエリプラン
（`Stage` / `Step`）を必要としないため `requires_plan=False` とする。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds


@rule("job.error", requires_plan=False)
def error(job: Job, th: Thresholds) -> Iterable[Finding]:
    """ジョブがエラーで終了した場合を検出する。

    `error_result` は BigQuery API が返す素の dict であり、キーの存在は
    保証されないため `.get()` で安全に参照する。
    """
    if job.error_result is None:
        return

    reason = job.error_result.get("reason")
    message = job.error_result.get("message")

    detail_parts = [part for part in (reason, message) if part]
    detail = ": ".join(detail_parts) if detail_parts else "詳細情報なし"
    summary = f"ジョブはエラーで終了しました（{detail}）"

    yield Finding(
        rule_id="job.error",
        title="ジョブエラー",
        severity=Severity.CRITICAL,
        summary=summary,
        evidence=(
            Evidence(
                label="error_reason",
                value=reason if reason is not None else "unknown",
            ),
        ),
    )


@rule("job.resource_warning", requires_plan=False)
def resource_warning(job: Job, th: Thresholds) -> Iterable[Finding]:
    """ジョブにリソース警告（resource_warning）が付与されている場合を検出する。

    `resource_warning` が None、または空文字列なら Finding を生成しない。
    """
    warning_text = job.resource_warning
    if not warning_text:
        return

    summary = f"ジョブにリソース警告が付与されています: {warning_text!r}"

    yield Finding(
        rule_id="job.resource_warning",
        title="ジョブのリソース警告",
        severity=Severity.WARNING,
        summary=summary,
        evidence=(
            Evidence(
                label="resource_warning",
                value=warning_text,
            ),
        ),
    )
