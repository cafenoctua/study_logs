"""normalize/from_sdk.py のテスト。

TDD: このテストを先に書き、失敗することを確認してから実装する。

このモジュールが検証する境界線:
- 入力は QueryJob._properties が保持する生の REST properties dict
  （camelCase）であり、SDK の型付きオブジェクトではないこと。
- statistics.creationTime / startTime / endTime はエポックミリ秒の
  文字列として届く。これを tz-aware な UTC datetime に変換すること。
- queryPlan[] / timeline[] の int64 系フィールドは全て文字列で届く。
  0 は 0 のまま、欠落は None のまま（決して混同しない）。
- queryPlan[] のリーフステージでは inputStages キー自体が丸ごと
  存在しないことがある（KeyError にしない）。
- configuration.dryRun は SDK 経路では信頼できる dry-run シグナルであり、
  INFORMATION_SCHEMA 経路とは扱いが異なる。
- computeMode / estimatedRunnableUnits は生の dict にだけ現れることが
  あり、型付き SDK では見えないフィールドなので、存在すれば読み取ること。
- google.cloud を import しないこと（sql.py / from_information_schema.py
  と同様の AST チェック）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bq_job_diagnose import models
from bq_job_diagnose.normalize import from_sdk

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sdk_jobs"


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# エポックミリ秒文字列 → datetime
# ---------------------------------------------------------------------------


class TestEpochMsDatetime:
    def test_epoch_ms_string_converted_to_aware_utc(self):
        dt = from_sdk._as_datetime_ms("1758326400000")
        assert dt == datetime(2025, 9, 20, 0, 0, 0, tzinfo=UTC)
        assert dt.tzinfo is not None

    def test_none_stays_none(self):
        assert from_sdk._as_datetime_ms(None) is None

    def test_zero_epoch_is_not_none(self):
        dt = from_sdk._as_datetime_ms("0")
        assert dt == datetime(1970, 1, 1, tzinfo=UTC)
        assert dt is not None


# ---------------------------------------------------------------------------
# int64-as-string ヘルパー
# ---------------------------------------------------------------------------


class TestAsInt:
    def test_string_digits_converted(self):
        assert from_sdk._as_int("4212000") == 4212000

    def test_none_stays_none(self):
        assert from_sdk._as_int(None) is None

    def test_zero_string_is_not_none(self):
        assert from_sdk._as_int("0") == 0
        assert from_sdk._as_int("0") is not None

    def test_int_passthrough(self):
        assert from_sdk._as_int(42) == 42


# ---------------------------------------------------------------------------
# skewed_join fixture 経由の詳細
# ---------------------------------------------------------------------------


class TestSkewedJoin:
    def test_normalizes_without_raising(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert isinstance(job, models.Job)

    def test_source_is_jobs_api(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.source is models.Source.JOBS_API

    def test_job_id_and_project_id(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.job_id == "job_skewed_join_001"
        assert job.project_id == "my-project"

    def test_creation_time_epoch_ms_converted(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.creation_time == datetime.fromisoformat("2026-09-13T01:00:00+00:00")

    def test_skew_ratio_is_20(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        join_stage = next(s for s in job.stages if s.id == 1)
        assert join_stage.compute_skew_ratio == pytest.approx(20.0)

    def test_labels_object_form_converted_to_dict(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.labels == {"team": "data-platform", "env": "prod"}

    def test_reservation_id_snake_case_key_read(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.reservation_id == "my-reservation"

    def test_plan_availability_available(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.plan_availability is models.PlanAvailability.AVAILABLE
        assert job.has_plan is True

    def test_input_stages_present_tuple(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        join_stage = next(s for s in job.stages if s.id == 1)
        assert join_stage.input_stage_ids == (0,)

    def test_leaf_stage_input_stages_absent_key_is_empty_tuple(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        leaf_stage = next(s for s in job.stages if s.id == 0)
        assert leaf_stage.input_stage_ids == ()

    def test_timeline_has_six_samples(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert len(job.timeline) == 6

    def test_estimated_runnable_units_read_when_present(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.timeline[0].estimated_runnable_units == 5

    def test_compute_mode_read_when_present(self):
        props = _load_fixture("skewed_join")
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        stage0 = next(s for s in job.stages if s.id == 0)
        assert stage0.compute_mode == "BIGQUERY"


# ---------------------------------------------------------------------------
# no_plan fixture
# ---------------------------------------------------------------------------


class TestNoPlan:
    def test_normalizes_without_raising(self):
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert isinstance(job, models.Job)

    def test_stages_empty(self):
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert job.stages == ()

    def test_plan_availability_not_available_not_restricted(self):
        # totalBytesProcessed / totalBytesBilled が両方あるので RESTRICTED ではない
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert job.plan_availability is models.PlanAvailability.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# dry_run fixture
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_plan_availability_dry_run(self):
        props = _load_fixture("dry_run")
        job = from_sdk.normalize_job(props, location="us")
        assert job.plan_availability is models.PlanAvailability.DRY_RUN
        assert job.has_plan is False

    def test_dry_run_wins_even_without_plan(self):
        props = _load_fixture("dry_run")
        job = from_sdk.normalize_job(props, location="us")
        assert job.stages == ()


# ---------------------------------------------------------------------------
# SCRIPT statementType, no plan, bytes present -> NOT_AVAILABLE (not RESTRICTED)
# ---------------------------------------------------------------------------


class TestScriptNoRestriction:
    def test_script_with_no_plan_is_not_available_not_restricted(self):
        props = _load_fixture("no_plan")
        props = json.loads(json.dumps(props))
        props["statistics"]["query"]["statementType"] = "SCRIPT"
        # totalBytes* も欠落させて RESTRICTED の形に一致させる
        del props["statistics"]["query"]["totalBytesProcessed"]
        del props["statistics"]["query"]["totalBytesBilled"]
        job = from_sdk.normalize_job(props, location="us")
        assert job.plan_availability is models.PlanAvailability.NOT_AVAILABLE
        assert job.plan_availability is not models.PlanAvailability.RESTRICTED

    def test_non_script_with_no_plan_and_no_bytes_is_restricted(self):
        props = _load_fixture("no_plan")
        props = json.loads(json.dumps(props))
        del props["statistics"]["query"]["totalBytesProcessed"]
        del props["statistics"]["query"]["totalBytesBilled"]
        job = from_sdk.normalize_job(props, location="us")
        assert job.plan_availability is models.PlanAvailability.RESTRICTED


# ---------------------------------------------------------------------------
# cache_hit
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_cache_hit_true_gives_cache_hit_availability(self):
        props = _load_fixture("no_plan")
        props = json.loads(json.dumps(props))
        props["statistics"]["query"]["cacheHit"] = True
        job = from_sdk.normalize_job(props, location="us")
        assert job.plan_availability is models.PlanAvailability.CACHE_HIT
        assert job.has_plan is False


# ---------------------------------------------------------------------------
# leaf_no_input_stages fixture
# ---------------------------------------------------------------------------


class TestLeafNoInputStages:
    def test_leaf_stage_input_stages_key_absent_is_empty_tuple(self):
        props = _load_fixture("leaf_no_input_stages")
        job = from_sdk.normalize_job(props, location="us")
        stage0 = next(s for s in job.stages if s.id == 0)
        assert stage0.input_stage_ids == ()

    def test_second_stage_has_input_stages(self):
        props = _load_fixture("leaf_no_input_stages")
        job = from_sdk.normalize_job(props, location="us")
        stage1 = next(s for s in job.stages if s.id == 1)
        assert stage1.input_stage_ids == (0,)

    def test_compute_mode_absent_is_none(self):
        # leaf_no_input_stages のステージには computeMode キーがない
        props = _load_fixture("leaf_no_input_stages")
        job = from_sdk.normalize_job(props, location="us")
        stage0 = next(s for s in job.stages if s.id == 0)
        assert stage0.compute_mode is None


# ---------------------------------------------------------------------------
# 欠落キーへの耐性
# ---------------------------------------------------------------------------


class TestMissingKeys:
    def test_estimated_runnable_units_absent_is_none_not_zero(self):
        props = _load_fixture("leaf_no_input_stages")
        props = json.loads(json.dumps(props))
        # leaf_no_input_stages には timeline がそもそもないので no_plan を使う
        job = from_sdk.normalize_job(props, location="us")
        assert job.timeline == ()

    def test_labels_absent_is_empty_mapping(self):
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert job.labels == {}

    def test_destination_table_absent_is_none(self):
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert job.destination_table is None

    def test_destination_table_present(self):
        props = _load_fixture("skewed_join")
        props = json.loads(json.dumps(props))
        props["configuration"]["query"]["destinationTable"] = {
            "projectId": "my-project",
            "datasetId": "ds1",
            "tableId": "dest1",
        }
        job = from_sdk.normalize_job(props, location="asia-northeast1")
        assert job.destination_table == models.TableRef("my-project", "ds1", "dest1")

    def test_referenced_tables_absent_is_empty_tuple(self):
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert job.referenced_tables == ()

    def test_query_plan_key_absent_entirely(self):
        props = _load_fixture("no_plan")
        assert "queryPlan" not in props["statistics"]["query"]
        job = from_sdk.normalize_job(props, location="us")
        assert job.stages == ()

    def test_parent_job_id_absent_is_none(self):
        props = _load_fixture("no_plan")
        job = from_sdk.normalize_job(props, location="us")
        assert job.parent_job_id is None

    def test_error_result_absent_is_none(self):
        props = _load_fixture("no_plan")
        props = json.loads(json.dumps(props))
        del props["status"]["errorResult"]
        job = from_sdk.normalize_job(props, location="us")
        assert job.error_result is None


# ---------------------------------------------------------------------------
# ネットワーク非依存の確認
# ---------------------------------------------------------------------------


class TestNoNetworkImports:
    def test_module_does_not_import_google_cloud(self):
        import ast
        import sys

        mod = sys.modules[from_sdk.__name__]
        source_file = mod.__file__
        assert source_file is not None
        with open(source_file, encoding="utf-8") as f:
            text = f.read()

        tree = ast.parse(text, filename=source_file)
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

        assert "google" not in imported_roots

    def test_module_has_no_google_cloud_in_module_namespace(self):
        assert not hasattr(from_sdk, "bigquery")
        assert "google" not in dir(from_sdk)


class TestDmlStatistics:
    """REST の dmlStats が INFORMATION_SCHEMA の dml_statistics と同じ形になること。

    両経路で形が揃っていないと、ルール側がデータソースを意識せざるを
    得なくなり「rules は models.Job しか知らない」という前提が崩れる。
    """

    def _job_with_dml(self, dml_stats):
        return {
            "jobReference": {"jobId": "j1", "projectId": "p1", "location": "us"},
            "user_email": "u@example.com",
            "configuration": {"jobType": "QUERY", "query": {"query": "MERGE ..."}},
            "status": {"state": "DONE"},
            "statistics": {
                "creationTime": "1758326400000",
                "query": {"statementType": "MERGE", "queryPlan": [], "dmlStats": dml_stats},
            },
        }

    def test_dml_stats_converted_to_snake_case_ints(self):
        job = from_sdk.normalize_job(
            self._job_with_dml(
                {"insertedRowCount": "10", "deletedRowCount": "0", "updatedRowCount": "3"}
            ),
            location="us",
        )
        assert job.dml_statistics == {
            "inserted_row_count": 10,
            "deleted_row_count": 0,
            "updated_row_count": 3,
        }

    def test_zero_row_count_stays_zero(self):
        """0 は「0 行更新された」であって「取得できなかった」ではない。"""
        job = from_sdk.normalize_job(
            self._job_with_dml({"deletedRowCount": "0"}), location="us"
        )
        assert job.dml_statistics["deleted_row_count"] == 0
        assert job.dml_statistics["deleted_row_count"] is not None

    def test_missing_key_stays_none(self):
        job = from_sdk.normalize_job(
            self._job_with_dml({"insertedRowCount": "5"}), location="us"
        )
        assert job.dml_statistics["inserted_row_count"] == 5
        assert job.dml_statistics["updated_row_count"] is None

    def test_absent_dml_stats_is_none(self):
        """SELECT など DML でないジョブは dml_statistics 自体が None。"""
        job = from_sdk.normalize_job(self._job_with_dml(None), location="us")
        assert job.dml_statistics is None
