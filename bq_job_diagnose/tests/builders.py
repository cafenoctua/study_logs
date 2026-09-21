"""テスト用の `Job` / `Stage` / `TimelineSample` ビルダー。

Phase 6 以降（ルールのテスト）で大量の Job バリエーションを組み立てる必要が
あるため、妥当なデフォルト値を持つファクトリ関数をここに用意する。
キーワード引数で個々のフィールドを上書きできる。

小さく素直に保つ方針: dataclass のフィールドをそのままキーワードで受け取り、
デフォルト値の辞書を dataclasses.replace ではなく単純な dict マージで構築する。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bq_job_diagnose.models import (
    Job,
    PlanAvailability,
    Source,
    Stage,
    Step,
    TimelineSample,
)

_DEFAULT_CREATION_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_DEFAULT_START_TIME = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
_DEFAULT_END_TIME = datetime(2026, 1, 1, 0, 0, 5, tzinfo=UTC)


def make_step(**overrides: Any) -> Step:
    """`Step` をデフォルト値付きで組み立てる。"""
    defaults: dict[str, Any] = {
        "kind": "READ",
        "substeps": (),
        "truncated": False,
    }
    defaults.update(overrides)
    return Step(**defaults)


def make_stage(**overrides: Any) -> Stage:
    """`Stage` をデフォルト値付きで組み立てる。

    デフォルトはスキュー等のシグナルが出ない「健全なステージ」を表す。
    """
    defaults: dict[str, Any] = {
        "id": 1,
        "name": "S00: Input",
        "status": "COMPLETE",
        "start_ms": 0,
        "end_ms": 1000,
        "input_stage_ids": (),
        "wait_ms_avg": 10,
        "wait_ms_max": 10,
        "read_ms_avg": 100,
        "read_ms_max": 100,
        "compute_ms_avg": 200,
        "compute_ms_max": 200,
        "write_ms_avg": 50,
        "write_ms_max": 50,
        "shuffle_output_bytes": 1000,
        "shuffle_output_bytes_spilled": 0,
        "records_read": 1000,
        "records_written": 1000,
        "parallel_inputs": 1,
        "completed_parallel_inputs": 1,
        "slot_ms": 1000,
        "compute_mode": "BIGQUERY",
        "steps": (),
    }
    defaults.update(overrides)
    return Stage(**defaults)


def make_timeline_sample(**overrides: Any) -> TimelineSample:
    """`TimelineSample` をデフォルト値付きで組み立てる。"""
    defaults: dict[str, Any] = {
        "elapsed_ms": 1000,
        "total_slot_ms": 1000,
        "pending_units": 0,
        "completed_units": 1,
        "active_units": 0,
        "estimated_runnable_units": 0,
    }
    defaults.update(overrides)
    return TimelineSample(**defaults)


def make_job(**overrides: Any) -> Job:
    """`Job` をデフォルト値付きで組み立てる。

    デフォルトはプラン利用可能・ステージ1件・タイムライン1件を持つ
    「素直に成功した」ジョブを表す。プランやタイムラインを持たないジョブを
    作りたい場合は `stages=()` や `plan_availability=PlanAvailability.CACHE_HIT`
    などを明示的に上書きする。
    """
    defaults: dict[str, Any] = {
        "source": Source.INFORMATION_SCHEMA,
        "job_id": "job_default",
        "project_id": "test-project",
        "location": "asia-northeast1",
        "parent_job_id": None,
        "user_email": "user@example.com",
        "creation_time": _DEFAULT_CREATION_TIME,
        "start_time": _DEFAULT_START_TIME,
        "end_time": _DEFAULT_END_TIME,
        "job_type": "QUERY",
        "statement_type": "SELECT",
        "priority": "INTERACTIVE",
        "state": "DONE",
        "error_result": None,
        "query": "SELECT 1",
        "cache_hit": False,
        "total_bytes_processed": 1000,
        "total_bytes_billed": 1000,
        "total_slot_ms": 1000,
        "referenced_tables": (),
        "destination_table": None,
        "plan_availability": PlanAvailability.AVAILABLE,
        "stages": (make_stage(),),
        "timeline": (make_timeline_sample(),),
    }
    defaults.update(overrides)
    return Job(**defaults)
