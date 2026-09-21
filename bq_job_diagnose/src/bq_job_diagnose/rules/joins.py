"""JOIN パターン検出ルール（join.broadcast_large / join.shuffle_heavy / join.cardinality_explosion）。

`step.substeps` に含まれる文字列からクエリプランの JOIN 種別を判定する。
BigQuery のクエリプラン説明文言そのもの（"JOIN EACH WITH ALL" 等）に依存するため、
将来的に文言が変わった場合はこのモジュールの定数を更新すること。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Evidence, Finding, Job, Severity, Stage
from bq_job_diagnose.rules import rule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

_DOC_URL = "https://cloud.google.com/bigquery/docs/query-plan-explanation"

_BROADCAST_MARKER = "JOIN EACH WITH ALL"
_SHUFFLE_MARKER = "JOIN EACH WITH EACH"
_JOIN_MARKER = "JOIN"

_BROADCAST_DOC_QUOTE = (
    '"JOIN EACH WITH ALL" is a broadcast join and '
    '"JOIN EACH WITH EACH" is a hash join'
)
_SHUFFLE_DOC_QUOTE = _BROADCAST_DOC_QUOTE
_CARDINALITY_DOC_QUOTE = (
    "Joins that produce significantly more rows than the number of left and "
    "right input rows"
)


def _stage_has_truncated_step(stage: Stage) -> bool:
    return any(step.truncated for step in stage.steps)


def _confidence_for(stage: Stage) -> str:
    return "medium" if _stage_has_truncated_step(stage) else "high"


def _stage_has_marker(stage: Stage, marker: str) -> bool:
    return any(
        any(marker in substep for substep in step.substeps) for step in stage.steps
    )


@rule("join.broadcast_large", requires_plan=True)
def broadcast_large(job: Job, th: Thresholds) -> Iterable[Finding]:
    """ブロードキャスト結合（JOIN EACH WITH ALL）かつシャッフル出力が大きいステージを検出する。

    ガード:
    - substeps に "JOIN EACH WITH ALL" を含むステップを持たないステージは対象外。
    - shuffle_output_bytes が None なら対象外（取得不能を 0 として扱わない）。
    - substeps がプラン切り詰め（truncated=True）を含む場合、パターン一致が
      不完全な情報に基づく可能性があるため confidence を medium に下げる。
    """
    for stage in job.stages:
        if not _stage_has_marker(stage, _BROADCAST_MARKER):
            continue

        output_bytes = stage.shuffle_output_bytes
        if output_bytes is None:
            continue
        if output_bytes < th.join.broadcast_input_bytes_warning:
            continue

        summary = (
            f"ステージ {stage.name} はブロードキャスト結合（JOIN EACH WITH ALL）を含み、"
            f"シャッフル出力は {output_bytes:,} バイトです"
        )

        yield Finding(
            rule_id="join.broadcast_large",
            title="大規模なブロードキャスト結合",
            severity=Severity.WARNING,
            summary=summary,
            evidence=(
                Evidence(
                    label="shuffle_output_bytes",
                    value=output_bytes,
                    unit="bytes",
                    stage_id=stage.id,
                    threshold=th.join.broadcast_input_bytes_warning,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url=_DOC_URL,
            doc_quote=_BROADCAST_DOC_QUOTE,
            confidence=_confidence_for(stage),
        )


@rule("join.shuffle_heavy", requires_plan=True)
def shuffle_heavy(job: Job, th: Thresholds) -> Iterable[Finding]:
    """ハッシュ結合（JOIN EACH WITH EACH）でシャッフルスピルが発生しているステージを検出する。

    シャッフル結合自体は正常なプラン形状であり、スピルが発生している場合のみ
    問題の兆候とみなす。

    ガード:
    - substeps に "JOIN EACH WITH EACH" を含むステップを持たないステージは対象外。
    - shuffle_output_bytes_spilled が None または 0 以下なら対象外。
    - truncated=True を含む場合は confidence を medium に下げる。
    """
    for stage in job.stages:
        if not _stage_has_marker(stage, _SHUFFLE_MARKER):
            continue

        spilled = stage.shuffle_output_bytes_spilled
        if spilled is None or spilled <= 0:
            continue

        summary = (
            f"ステージ {stage.name} はハッシュ結合（JOIN EACH WITH EACH）を含み、"
            f"シャッフル出力 {spilled:,} バイトがディスクにスピルしました"
        )

        yield Finding(
            rule_id="join.shuffle_heavy",
            title="スピルを伴うシャッフル結合",
            severity=Severity.WARNING,
            summary=summary,
            evidence=(
                Evidence(
                    label="shuffle_output_bytes_spilled",
                    value=spilled,
                    unit="bytes",
                    stage_id=stage.id,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url=_DOC_URL,
            doc_quote=_SHUFFLE_DOC_QUOTE,
            confidence=_confidence_for(stage),
        )


@rule("join.cardinality_explosion", requires_plan=True)
def cardinality_explosion(job: Job, th: Thresholds) -> Iterable[Finding]:
    """JOIN ステップを含むステージで出力行数が入力行数に対し爆発的に増加している状態を検出する。

    ガード:
    - substeps に "JOIN" を含むステップを持たないステージは対象外。
    - records_read / records_written のいずれかが None なら対象外
      （取得不能を 0 として扱わない）。
    - records_written が min_output_records 未満なら実害が小さいとみなしスキップする。
    - records_read が 0 ならゼロ除算を避けるためスキップする。
    - truncated=True を含む場合は confidence を medium に下げる。
    """
    for stage in job.stages:
        if not _stage_has_marker(stage, _JOIN_MARKER):
            continue

        records_read = stage.records_read
        records_written = stage.records_written
        if records_read is None or records_written is None:
            continue
        if records_written < th.join.min_output_records:
            continue
        if records_read == 0:
            continue

        ratio = records_written / records_read
        if ratio < th.join.cardinality_explosion_ratio:
            continue

        summary = (
            f"ステージ {stage.name} は JOIN で {records_read:,} 行読み込み "
            f"{records_written:,} 行を出力（出力/入力比 {ratio:.2f} 倍）"
        )

        yield Finding(
            rule_id="join.cardinality_explosion",
            title="JOIN によるカーディナリティ爆発",
            severity=Severity.WARNING,
            summary=summary,
            evidence=(
                Evidence(
                    label="cardinality_ratio",
                    value=ratio,
                    unit="ratio",
                    stage_id=stage.id,
                    threshold=th.join.cardinality_explosion_ratio,
                ),
                Evidence(
                    label="records_read",
                    value=records_read,
                    unit="rows",
                    stage_id=stage.id,
                ),
                Evidence(
                    label="records_written",
                    value=records_written,
                    unit="rows",
                    stage_id=stage.id,
                ),
            ),
            stage_ids=(stage.id,),
            doc_url=_DOC_URL,
            doc_quote=_CARDINALITY_DOC_QUOTE,
            confidence=_confidence_for(stage),
        )
