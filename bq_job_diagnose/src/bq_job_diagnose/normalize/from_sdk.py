"""BigQuery Jobs API（REST）の生 properties dict を models.Job へ変換する。

設計上の制約（重要）:
- このモジュールはネットワーク呼び出しを一切行わない。`google.cloud` を
  import してはならない。入力の `job_properties` は
  `google.cloud.bigquery.job.QueryJob._properties`（型付き SDK オブジェクトの
  内部に保持されている生の REST レスポンス dict）を想定するが、このモジュール
  自身はその dict を「ただの Mapping」として扱う（SDK のクラス型を一切
  前提にしない）。これにより GCP アクセスなしでテストできる。
- REST の JSON は camelCase であり、INFORMATION_SCHEMA（snake_case）とは
  キー名の形がまったく異なる。`statistics.reservation_id` だけは例外的に
  snake_case で届く（BigQuery REST API 自体の非対称性）。
- `None` は「取得できない／公開されていない」ことを表し、`0` は
  「取得できて値がゼロだった」ことを表す。この2つを絶対に混同しない。
- REST の INT64 フィールドは常に JSON 文字列として届く（JSON に 64bit
  整数の精度保証がないため）。そのため int への変換は必ず `_as_int` を通す。
- `statistics.creationTime` / `startTime` / `endTime` はエポックミリ秒の
  文字列として届く（INFORMATION_SCHEMA の ISO8601 文字列 / datetime とは
  異なる形）。`_as_datetime_ms` で tz-aware な UTC datetime に変換する。
- `queryPlan[].inputStages` はリーフステージ（他ステージへの入力を持たない
  最初のステージ）ではキー自体が丸ごと存在しないことがある。
  `entry["inputStages"]` ではなく `entry.get("inputStages")` を使い、
  欠落・空配列のどちらも空タプル `()` に正規化する。

`labels` に関する仮定:
- REST の `configuration.labels` は INFORMATION_SCHEMA の
  `[{key: ..., value: ...}, ...]` 形式とは異なり、素の `{key: value}`
  オブジェクトとして届く。そのままコピーすれば良い。

`Step.truncated` に関する仮定:
- REST の `queryPlan[].steps[]` にも切り詰めマーカーは現れないため、
  from_information_schema.py と同様に常に `truncated=False` とする。

PlanAvailability に関する仮定（from_information_schema.py との違い）:
- `configuration.dryRun` は SDK/REST 経路では信頼できる dry-run シグナル
  である（INFORMATION_SCHEMA には存在しない）。そのため最優先で判定する。
- それ以降の優先順位（cache_hit → SCRIPT → バイト数両方 None →
  それ以外）は from_information_schema.py の `_decide_plan_availability`
  と同じ考え方をミラーする。

型付き SDK には現れないが生 dict には現れうるフィールド:
- `queryPlan[].computeMode`
- `timeline[].estimatedRunnableUnits`
  どちらも「存在すれば読み取り、存在しなければ None」を徹底する。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from bq_job_diagnose import models

# ---------------------------------------------------------------------------
# 数値変換ヘルパー
# ---------------------------------------------------------------------------


def _as_int(v: Any) -> int | None:
    """REST の INT64 値（文字列で届く）を int に変換する。

    None は None のまま返す（「取得できない」と「値が0」を混同しないため）。
    """
    if v is None:
        return None
    return int(v)


def _as_bool(v: Any) -> bool | None:
    """BOOL 値を bool に変換する。None はそのまま None。"""
    if v is None:
        return None
    return bool(v)


def _as_datetime_ms(v: Any) -> datetime | None:
    """エポックミリ秒の文字列（または int）を tz-aware な UTC datetime に変換する。

    statistics.creationTime / startTime / endTime はこの形で届く。
    None は None のまま返す（"0" は 1970-01-01T00:00:00Z になり、None とは
    区別される）。
    """
    if v is None:
        return None
    millis = int(v)
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


# ---------------------------------------------------------------------------
# labels / referenced_tables / destination_table
# ---------------------------------------------------------------------------


def _normalize_labels(raw: Any) -> Mapping[str, str]:
    """`{key: value, ...}` というプレーンなオブジェクトをそのまま dict化する。

    INFORMATION_SCHEMA の repeated record 形式（[{key, value}, ...]）とは
    異なり、REST の configuration.labels は最初から plain object なので
    変換不要（コピーのみ）。欠落・None の場合は空 mapping。
    """
    if not raw:
        return {}
    return dict(raw)


def _normalize_table_ref(raw: Any) -> models.TableRef | None:
    """`{projectId, datasetId, tableId}` を TableRef に変換する。None は None のまま。"""
    if raw is None:
        return None
    return models.TableRef(
        project_id=raw["projectId"],
        dataset_id=raw["datasetId"],
        table_id=raw["tableId"],
    )


def _normalize_referenced_tables(raw: Any) -> tuple[models.TableRef, ...]:
    """referencedTables 配列を tuple[TableRef, ...] に変換する。欠落/None は空タプル。"""
    if not raw:
        return ()
    return tuple(_normalize_table_ref(t) for t in raw)


# ---------------------------------------------------------------------------
# Step / Stage / TimelineSample
# ---------------------------------------------------------------------------


def _normalize_step(raw: Mapping[str, Any]) -> models.Step:
    """queryPlan[].steps[] の1要素を Step に変換する。

    REST にも truncated マーカーは存在しないため常に False。
    """
    substeps_raw = raw.get("substeps") or ()
    return models.Step(
        kind=raw["kind"],
        substeps=tuple(substeps_raw),
        truncated=False,
    )


def _normalize_stage(raw: Mapping[str, Any]) -> models.Stage:
    """queryPlan[] の1要素を Stage に変換する。

    `inputStages` はリーフステージではキー自体が欠落しうるため、
    `raw["inputStages"]` ではなく `.get()` を使う。
    `computeMode` は型付き SDK には現れないが生 dict には現れることが
    あるため、存在すれば読み取り、存在しなければ None とする。
    """
    input_stages_raw = raw.get("inputStages") or ()
    steps_raw = raw.get("steps") or ()
    return models.Stage(
        id=_as_int(raw["id"]),
        # name は BigQuery が必ず返すフィールド。欠落は想定外のスキーマ変更
        # なので黙って None にせず KeyError で早期に落とす。
        name=raw["name"],
        status=raw.get("status"),
        start_ms=_as_int(raw.get("startMs")),
        end_ms=_as_int(raw.get("endMs")),
        input_stage_ids=tuple(_as_int(s) for s in input_stages_raw),
        wait_ms_avg=_as_int(raw.get("waitMsAvg")),
        wait_ms_max=_as_int(raw.get("waitMsMax")),
        read_ms_avg=_as_int(raw.get("readMsAvg")),
        read_ms_max=_as_int(raw.get("readMsMax")),
        compute_ms_avg=_as_int(raw.get("computeMsAvg")),
        compute_ms_max=_as_int(raw.get("computeMsMax")),
        write_ms_avg=_as_int(raw.get("writeMsAvg")),
        write_ms_max=_as_int(raw.get("writeMsMax")),
        shuffle_output_bytes=_as_int(raw.get("shuffleOutputBytes")),
        shuffle_output_bytes_spilled=_as_int(raw.get("shuffleOutputBytesSpilled")),
        records_read=_as_int(raw.get("recordsRead")),
        records_written=_as_int(raw.get("recordsWritten")),
        parallel_inputs=_as_int(raw.get("parallelInputs")),
        completed_parallel_inputs=_as_int(raw.get("completedParallelInputs")),
        slot_ms=_as_int(raw.get("slotMs")),
        compute_mode=raw.get("computeMode"),
        steps=tuple(_normalize_step(s) for s in steps_raw),
    )


def _normalize_timeline_sample(raw: Mapping[str, Any]) -> models.TimelineSample:
    """timeline[] の1要素を TimelineSample に変換する。

    `estimatedRunnableUnits` は型付き SDK には現れないが生 dict には
    現れることがあるため、存在すれば読み取り、存在しなければ None とする。
    """
    return models.TimelineSample(
        elapsed_ms=_as_int(raw["elapsedMs"]),
        total_slot_ms=_as_int(raw.get("totalSlotMs")),
        pending_units=_as_int(raw.get("pendingUnits")),
        completed_units=_as_int(raw.get("completedUnits")),
        active_units=_as_int(raw.get("activeUnits")),
        estimated_runnable_units=_as_int(raw.get("estimatedRunnableUnits")),
    )


# ---------------------------------------------------------------------------
# PlanAvailability 判定
# ---------------------------------------------------------------------------



def _normalize_dml_statistics(raw: Mapping[str, Any] | None) -> dict | None:
    """REST の dmlStats を INFORMATION_SCHEMA の dml_statistics と同じ形に揃える。

    REST: {"insertedRowCount": "10", "deletedRowCount": "0", "updatedRowCount": "3"}
    IS  : {"inserted_row_count": 10, "deleted_row_count": 0, "updated_row_count": 3}

    REST 側は int64 が文字列で届くため int に変換する。値が取得できなかった
    キーは None のままにし、0 と混同しない。
    """
    if not raw:
        return None
    return {
        "inserted_row_count": _as_int(raw.get("insertedRowCount")),
        "deleted_row_count": _as_int(raw.get("deletedRowCount")),
        "updated_row_count": _as_int(raw.get("updatedRowCount")),
    }

def _decide_plan_availability(
    *,
    dry_run: bool,
    cache_hit: bool | None,
    query_plan: tuple[Any, ...],
    statement_type: str | None,
    total_bytes_billed: int | None,
    total_bytes_processed: int | None,
) -> models.PlanAvailability:
    """statistics / configuration の内容から PlanAvailability を判定する。

    優先順位（from_information_schema.py の `_decide_plan_availability` と
    同じ考え方だが、SDK/REST 経路では dry-run が信頼できるシグナルなので
    最優先で判定する点が異なる）:
    1. configuration.dryRun が True → DRY_RUN。
    2. cache_hit が True → CACHE_HIT（キャッシュヒットは正常にプランを
       持たない。エラーではない）。
    3. queryPlan が空/欠落 かつ statement_type == 'SCRIPT' → NOT_AVAILABLE
       （SCRIPT 親は正常にプランを持たない。RESTRICTED と列の形が同じため
       statement_type で切り分ける）。
    4. queryPlan が空/欠落 かつ totalBytesBilled / totalBytesProcessed が
       ともに None → RESTRICTED。
    5. queryPlan が空/欠落（上記に該当しない）→ NOT_AVAILABLE。
    6. queryPlan が非空 → AVAILABLE。
    """
    if dry_run:
        return models.PlanAvailability.DRY_RUN

    if cache_hit is True:
        return models.PlanAvailability.CACHE_HIT

    if len(query_plan) == 0:
        if statement_type == "SCRIPT":
            return models.PlanAvailability.NOT_AVAILABLE
        if total_bytes_billed is None and total_bytes_processed is None:
            return models.PlanAvailability.RESTRICTED
        return models.PlanAvailability.NOT_AVAILABLE

    return models.PlanAvailability.AVAILABLE


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def normalize_job(job_properties: Mapping[str, Any], *, location: str) -> models.Job:
    """QueryJob._properties が保持する生の REST properties dict を models.Job に変換する。

    `job_properties` は
    `{"jobReference": {...}, "configuration": {...}, "statistics": {...}, "status": {...}}`
    という形を想定するが、この関数自体はそれを「プレーンな Mapping」として
    のみ扱う（google.cloud.bigquery のクラス型を一切前提にしない）。
    """
    job_reference = job_properties.get("jobReference") or {}
    configuration = job_properties.get("configuration") or {}
    statistics = job_properties.get("statistics") or {}
    status = job_properties.get("status") or {}

    query_config = configuration.get("query") or {}
    query_stats = statistics.get("query") or {}

    dry_run = bool(configuration.get("dryRun") or False)

    query_plan_raw = query_stats.get("queryPlan") or ()
    stages = tuple(_normalize_stage(s) for s in query_plan_raw)

    timeline_raw = query_stats.get("timeline") or ()
    timeline = tuple(_normalize_timeline_sample(t) for t in timeline_raw)

    cache_hit = _as_bool(query_stats.get("cacheHit"))
    statement_type = query_stats.get("statementType")
    total_bytes_billed = _as_int(query_stats.get("totalBytesBilled"))
    total_bytes_processed = _as_int(query_stats.get("totalBytesProcessed"))

    plan_availability = _decide_plan_availability(
        dry_run=dry_run,
        cache_hit=cache_hit,
        query_plan=query_plan_raw,
        statement_type=statement_type,
        total_bytes_billed=total_bytes_billed,
        total_bytes_processed=total_bytes_processed,
    )

    return models.Job(
        source=models.Source.JOBS_API,
        job_id=job_reference["jobId"],
        project_id=job_reference["projectId"],
        location=location,
        parent_job_id=statistics.get("parentJobId"),
        user_email=job_properties.get("user_email") or statistics.get("userEmail"),
        creation_time=_as_datetime_ms(statistics.get("creationTime")),
        start_time=_as_datetime_ms(statistics.get("startTime")),
        end_time=_as_datetime_ms(statistics.get("endTime")),
        job_type=configuration.get("jobType"),
        statement_type=statement_type,
        priority=query_config.get("priority"),
        state=status.get("state"),
        error_result=status.get("errorResult"),
        query=query_config.get("query"),
        cache_hit=cache_hit,
        total_bytes_processed=total_bytes_processed,
        total_bytes_billed=total_bytes_billed,
        total_slot_ms=_as_int(statistics.get("totalSlotMs")),
        referenced_tables=_normalize_referenced_tables(query_stats.get("referencedTables")),
        destination_table=_normalize_table_ref(query_config.get("destinationTable")),
        labels=_normalize_labels(configuration.get("labels")),
        # REST API では statistics.reservation_id のみ snake_case で届く
        # （BigQuery REST API 自体の非対称性。他は全て camelCase）。
        reservation_id=statistics.get("reservation_id"),
        edition=statistics.get("edition"),
        # REST では statistics.query.dmlStats に camelCase のキーで届く。
        # INFORMATION_SCHEMA の dml_statistics と意味を揃えるため snake_case に
        # 変換してから渡す（両経路で同じ形の dict になることをパリティテストで検証）。
        dml_statistics=_normalize_dml_statistics(query_stats.get("dmlStats")),
        plan_availability=plan_availability,
        stages=stages,
        timeline=timeline,
    )
