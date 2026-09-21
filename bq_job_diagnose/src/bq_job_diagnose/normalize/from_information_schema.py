"""INFORMATION_SCHEMA.JOBS_BY_PROJECT の行を models.Job へ変換する。

設計上の制約（重要）:
- このモジュールはネットワーク呼び出しを一切行わない。`google.cloud` を
  import してはならない。入力の `row` は `collect/sql.py` の
  `build_job_sql` / `build_drill_sql` が返す SQL を実行して得られる行を
  想定するが、このモジュール自身はその行を「ただの Mapping」として扱う
  （BigQuery クライアントの RowIterator 等の型を一切前提にしない）。
- `None` は「取得できない／公開されていない」ことを表し、`0` は
  「取得できて値がゼロだった」ことを表す。この2つを絶対に混同しない
  （行レベルアクセスポリシーでマスクされたジョブが「0バイトスキャンした
  ジョブ」に見えてしまうと誤診断の原因になる）。
- INFORMATION_SCHEMA の INT64 / FLOAT64 カラムは、BigQuery REST 層経由だと
  JSON 文字列として届くことがある（JSON に 64bit 整数の精度保証がないため）。
  そのため int/float への変換は必ず `_as_int` / `_as_float` を通す。
- `input_stages` はリーフステージ（他ステージへの入力を持たない最初の
  ステージ）ではキー自体が丸ごと存在しないことがある。`row["input_stages"]`
  ではなく `row.get("input_stages")` を使い、欠落・空配列のどちらも
  空タプル `()` に正規化する。

タイムスタンプに関する仮定:
- BigQuery Python クライアントが実際に返す行では `creation_time` 等は
  tz-aware な `datetime` オブジェクトとして届く。一方このモジュールは
  google.cloud を import できないためテスト等では JSON 経由で ISO8601
  文字列として渡されることがある。両方を受け付け、文字列の場合は
  `datetime.fromisoformat` でパースする。

`labels` に関する仮定:
- INFORMATION_SCHEMA の `labels` カラムは `[{key: ..., value: ...}, ...]`
  という repeated record として届く。これを `{key: value}` の
  プレーンな dict に変換する。欠落・None の場合は空 mapping。

`Step.truncated` に関する仮定:
- INFORMATION_SCHEMA の `job_stages[].steps[]` には切り詰めを示す
  マーカーが存在しない（Jobs API 側は `MAX_TRUNCATED_...` 等の情報を
  返すことがあるが、INFORMATION_SCHEMA では観測できない）。そのため
  このモジュールでは常に `truncated=False` を設定する。SDK 経由の
  normalize（Phase 10 以降で別モジュールとして実装予定）では異なりうる。

PlanAvailability に関する仮定:
- INFORMATION_SCHEMA には dry-run 実行だったかどうかを示す信頼できる
  シグナルが存在しない（dry-run のジョブは JOBS_BY_PROJECT に記録
  されないか、記録されても通常実行と区別する専用カラムがない）。
  そのためこのモジュールは `PlanAvailability.DRY_RUN` を一切生成しない。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from bq_job_diagnose import models

# ---------------------------------------------------------------------------
# 数値変換ヘルパー
# ---------------------------------------------------------------------------


def _as_int(v: Any) -> int | None:
    """INFORMATION_SCHEMA の INT64 値（文字列で届く場合を含む）を int に変換する。

    None は None のまま返す（「取得できない」と「値が0」を混同しないため）。
    """
    if v is None:
        return None
    return int(v)


def _as_float(v: Any) -> float | None:
    """INFORMATION_SCHEMA の FLOAT64 値（文字列で届く場合を含む）を float に変換する。

    None は None のまま返す。
    """
    if v is None:
        return None
    return float(v)


def _as_bool(v: Any) -> bool | None:
    """BOOL 値を bool に変換する。None はそのまま None。"""
    if v is None:
        return None
    return bool(v)


def _as_datetime(v: Any) -> datetime | None:
    """datetime か ISO8601 文字列のどちらでも受け付ける。

    BigQuery クライアントは tz-aware な datetime を返すが、このモジュールは
    google.cloud を import できないためテスト等では文字列で渡されることも
    許容する。
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        return datetime.fromisoformat(v)
    raise TypeError(f"datetime または ISO8601 文字列を期待しましたが、{type(v)!r} を受け取りました")


# ---------------------------------------------------------------------------
# labels / referenced_tables / destination_table
# ---------------------------------------------------------------------------


def _normalize_labels(raw: Any) -> Mapping[str, str]:
    """`[{key: ..., value: ...}, ...]` 形式の repeated record を dict に変換する。

    キーが存在しない・None の場合は空 mapping を返す。
    """
    if not raw:
        return {}
    return {entry["key"]: entry["value"] for entry in raw}


def _normalize_table_ref(raw: Any) -> models.TableRef | None:
    """`{project_id, dataset_id, table_id}` を TableRef に変換する。None は None のまま。"""
    if raw is None:
        return None
    return models.TableRef(
        project_id=raw["project_id"],
        dataset_id=raw["dataset_id"],
        table_id=raw["table_id"],
    )


def _normalize_referenced_tables(raw: Any) -> tuple[models.TableRef, ...]:
    """referenced_tables 配列を tuple[TableRef, ...] に変換する。欠落/None は空タプル。"""
    if not raw:
        return ()
    return tuple(_normalize_table_ref(t) for t in raw)


# ---------------------------------------------------------------------------
# Step / Stage / TimelineSample
# ---------------------------------------------------------------------------


def _normalize_step(raw: Mapping[str, Any]) -> models.Step:
    """job_stages[].steps[] の1要素を Step に変換する。

    INFORMATION_SCHEMA には truncated マーカーが存在しないため常に False。
    """
    substeps_raw = raw.get("substeps") or ()
    return models.Step(
        kind=raw["kind"],
        substeps=tuple(substeps_raw),
        truncated=False,
    )


def _normalize_stage(raw: Mapping[str, Any]) -> models.Stage:
    """job_stages[] の1要素を Stage に変換する。

    `input_stages` はリーフステージではキー自体が欠落しうるため、
    `row["input_stages"]` ではなく `.get()` を使う。
    """
    input_stages_raw = raw.get("input_stages") or ()
    steps_raw = raw.get("steps") or ()
    return models.Stage(
        id=_as_int(raw["id"]),
        # name は BigQuery が必ず返す列。欠落は想定外のスキーマ変更なので
        # 黙って None にせず KeyError で早期に落とす（models.Stage.name は str）。
        name=raw["name"],
        status=raw.get("status"),
        start_ms=_as_int(raw.get("start_ms")),
        end_ms=_as_int(raw.get("end_ms")),
        input_stage_ids=tuple(_as_int(s) for s in input_stages_raw),
        wait_ms_avg=_as_int(raw.get("wait_ms_avg")),
        wait_ms_max=_as_int(raw.get("wait_ms_max")),
        read_ms_avg=_as_int(raw.get("read_ms_avg")),
        read_ms_max=_as_int(raw.get("read_ms_max")),
        compute_ms_avg=_as_int(raw.get("compute_ms_avg")),
        compute_ms_max=_as_int(raw.get("compute_ms_max")),
        write_ms_avg=_as_int(raw.get("write_ms_avg")),
        write_ms_max=_as_int(raw.get("write_ms_max")),
        shuffle_output_bytes=_as_int(raw.get("shuffle_output_bytes")),
        shuffle_output_bytes_spilled=_as_int(raw.get("shuffle_output_bytes_spilled")),
        records_read=_as_int(raw.get("records_read")),
        records_written=_as_int(raw.get("records_written")),
        parallel_inputs=_as_int(raw.get("parallel_inputs")),
        completed_parallel_inputs=_as_int(raw.get("completed_parallel_inputs")),
        slot_ms=_as_int(raw.get("slot_ms")),
        compute_mode=raw.get("compute_mode"),
        steps=tuple(_normalize_step(s) for s in steps_raw),
    )


def _normalize_timeline_sample(raw: Mapping[str, Any]) -> models.TimelineSample:
    """timeline[] の1要素を TimelineSample に変換する。"""
    return models.TimelineSample(
        elapsed_ms=_as_int(raw["elapsed_ms"]),
        total_slot_ms=_as_int(raw.get("total_slot_ms")),
        pending_units=_as_int(raw.get("pending_units")),
        completed_units=_as_int(raw.get("completed_units")),
        active_units=_as_int(raw.get("active_units")),
        estimated_runnable_units=_as_int(raw.get("estimated_runnable_units")),
    )


# ---------------------------------------------------------------------------
# PlanAvailability 判定
# ---------------------------------------------------------------------------


def _decide_plan_availability(row: Mapping[str, Any]) -> models.PlanAvailability:
    """行の内容から PlanAvailability を判定する。

    優先順位:
    1. cache_hit が True → CACHE_HIT（キャッシュヒットは正常にプランを
       持たない。エラーではない）。
    2. job_stages が空/欠落 かつ statement_type == 'SCRIPT' → NOT_AVAILABLE
       （SCRIPT 親は正常にプランを持たない。RESTRICTED と列の形が同じため
       statement_type で切り分ける）。
    3. job_stages が空/欠落 かつ total_bytes_billed / total_bytes_processed
       がともに None → RESTRICTED（行レベルアクセスポリシーがこの3項目を
       まとめてブランクにする既知の挙動）。
    4. job_stages が空/欠落（上記に該当しない）→ NOT_AVAILABLE。
    5. job_stages が非空 → AVAILABLE。

    注意: INFORMATION_SCHEMA には dry-run を示す信頼できるシグナルが
    存在しないため、DRY_RUN はこの関数からは絶対に返らない。
    """
    if row.get("cache_hit") is True:
        return models.PlanAvailability.CACHE_HIT

    job_stages = row.get("job_stages") or ()
    if len(job_stages) == 0:
        # SCRIPT 親は子ジョブが実際の実行を担うため、自身はプランを持たない。
        # このときバイト数も null になり RESTRICTED と列の形が区別できないので、
        # statement_type という別の証拠を先に見て切り分ける。
        # （ここを誤ると、存在しない権限問題をユーザーに調べさせることになる）
        if row.get("statement_type") == "SCRIPT":
            return models.PlanAvailability.NOT_AVAILABLE
        if row.get("total_bytes_billed") is None and row.get("total_bytes_processed") is None:
            return models.PlanAvailability.RESTRICTED
        return models.PlanAvailability.NOT_AVAILABLE

    return models.PlanAvailability.AVAILABLE


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def normalize_row(row: Mapping[str, Any], *, location: str) -> models.Job:
    """INFORMATION_SCHEMA の1行（Mapping）を models.Job に変換する。

    `row` は `collect/sql.py` の `build_job_sql` / `build_drill_sql` が
    返す SQL の実行結果1行を想定するが、この関数自体はそれを「プレーンな
    Mapping」としてのみ扱う（BigQuery クライアントの行オブジェクト型を
    一切前提にしない）。
    """
    job_stages_raw = row.get("job_stages") or ()
    stages = tuple(_normalize_stage(s) for s in job_stages_raw)

    timeline_raw = row.get("timeline") or ()
    timeline = tuple(_normalize_timeline_sample(t) for t in timeline_raw)

    plan_availability = _decide_plan_availability(row)

    return models.Job(
        source=models.Source.INFORMATION_SCHEMA,
        job_id=row["job_id"],
        project_id=row["project_id"],
        location=location,
        parent_job_id=row.get("parent_job_id"),
        user_email=row.get("user_email"),
        creation_time=_as_datetime(row["creation_time"]),
        start_time=_as_datetime(row.get("start_time")),
        end_time=_as_datetime(row.get("end_time")),
        job_type=row["job_type"],
        statement_type=row.get("statement_type"),
        priority=row.get("priority"),
        state=row["state"],
        error_result=row.get("error_result"),
        query=row.get("query"),
        cache_hit=_as_bool(row.get("cache_hit")),
        total_bytes_processed=_as_int(row.get("total_bytes_processed")),
        total_bytes_billed=_as_int(row.get("total_bytes_billed")),
        total_slot_ms=_as_int(row.get("total_slot_ms")),
        referenced_tables=_normalize_referenced_tables(row.get("referenced_tables")),
        destination_table=_normalize_table_ref(row.get("destination_table")),
        labels=_normalize_labels(row.get("labels")),
        reservation_id=row.get("reservation_id"),
        edition=row.get("edition"),
        resource_warning=row.get("resource_warning"),
        normalized_literals_hash=row.get("normalized_literals_hash"),
        performance_insights=row.get("performance_insights"),
        dml_statistics=row.get("dml_statistics"),
        plan_availability=plan_availability,
        stages=stages,
        timeline=timeline,
    )
