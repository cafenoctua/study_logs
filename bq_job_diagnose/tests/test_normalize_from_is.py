"""normalize/from_information_schema.py のテスト。

TDD: このテストを先に書き、失敗することを確認してから実装する。

このモジュールが検証する境界線:
- INFORMATION_SCHEMA の行（Mapping）を models.Job に変換する際、
  None（取得不能）と 0（取得できて値がゼロ）を絶対に混同しないこと。
- INFORMATION_SCHEMA の INT64 カラムが JSON 文字列として届く場合があること
  （_as_int / _as_float で吸収する）。
- input_stages キーがリーフステージでは丸ごと欠落しうること（KeyError にしない）。
- google.cloud を import しないこと（sql.py と同様の AST チェック）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bq_job_diagnose import models
from bq_job_diagnose.normalize import from_information_schema as fis

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "is_rows"


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# _as_int / _as_float ヘルパー
# ---------------------------------------------------------------------------


class TestAsInt:
    def test_string_digits_converted(self):
        assert fis._as_int("4212000") == 4212000

    def test_none_stays_none(self):
        assert fis._as_int(None) is None

    def test_zero_is_not_none(self):
        assert fis._as_int(0) == 0
        assert fis._as_int(0) is not None

    def test_int_passthrough(self):
        assert fis._as_int(42) == 42

    def test_string_zero(self):
        assert fis._as_int("0") == 0
        assert fis._as_int("0") is not None


class TestAsFloat:
    def test_string_converted(self):
        assert fis._as_float("1.5") == 1.5

    def test_none_stays_none(self):
        assert fis._as_float(None) is None

    def test_zero_is_not_none(self):
        assert fis._as_float(0) == 0.0
        assert fis._as_float(0) is not None

    def test_int_passthrough(self):
        assert fis._as_float(3) == 3.0


# ---------------------------------------------------------------------------
# fixture: skewed_join — スキュー比率 ≈ 20.0
# ---------------------------------------------------------------------------


class TestSkewedJoin:
    def test_normalizes_without_raising(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        assert isinstance(job, models.Job)

    def test_skew_ratio_is_20(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        join_stage = next(s for s in job.stages if s.id == 1)
        assert join_stage.compute_skew_ratio == pytest.approx(20.0)

    def test_join_substep_present(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        join_stage = next(s for s in job.stages if s.id == 1)
        join_step = next(s for s in join_stage.steps if s.kind == "JOIN")
        assert "JOIN EACH WITH EACH" in join_step.substeps

    def test_timeline_has_six_samples(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        assert len(job.timeline) == 6

    def test_total_slot_ms_string_converted(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        assert job.total_slot_ms == 4212000

    def test_plan_availability_available(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        assert job.plan_availability is models.PlanAvailability.AVAILABLE
        assert job.has_plan is True

    def test_labels_dict(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        assert job.labels == {"team": "data-platform", "env": "prod"}

    def test_referenced_tables(self):
        row = _load_fixture("skewed_join")
        job = fis.normalize_row(row, location="asia-northeast1")
        assert len(job.referenced_tables) == 2
        assert all(isinstance(t, models.TableRef) for t in job.referenced_tables)


# ---------------------------------------------------------------------------
# fixture: spill_heavy — spill > 0
# ---------------------------------------------------------------------------


class TestSpillHeavy:
    def test_normalizes_without_raising(self):
        row = _load_fixture("spill_heavy")
        job = fis.normalize_row(row, location="us")
        assert isinstance(job, models.Job)

    def test_spilled_bytes_positive(self):
        row = _load_fixture("spill_heavy")
        job = fis.normalize_row(row, location="us")
        stage = job.stages[0]
        assert stage.shuffle_output_bytes_spilled == 5368709120
        assert stage.shuffle_output_bytes_spilled > 0

    def test_zero_spill_stays_zero_not_none(self):
        # leaf_no_input_stages のステージは spilled=0 を持つ。0 のまま保持されること。
        row = _load_fixture("leaf_no_input_stages")
        job = fis.normalize_row(row, location="us")
        stage0 = next(s for s in job.stages if s.id == 0)
        assert stage0.shuffle_output_bytes_spilled == 0
        assert stage0.shuffle_output_bytes_spilled is not None


# ---------------------------------------------------------------------------
# fixture: cache_hit — CACHE_HIT
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_normalizes_without_raising(self):
        row = _load_fixture("cache_hit")
        job = fis.normalize_row(row, location="us")
        assert isinstance(job, models.Job)

    def test_plan_availability_cache_hit(self):
        row = _load_fixture("cache_hit")
        job = fis.normalize_row(row, location="us")
        assert job.plan_availability is models.PlanAvailability.CACHE_HIT
        assert job.has_plan is False

    def test_zero_bytes_billed_not_none(self):
        row = _load_fixture("cache_hit")
        job = fis.normalize_row(row, location="us")
        assert job.total_bytes_billed == 0
        assert job.total_bytes_billed is not None


# ---------------------------------------------------------------------------
# fixture: script_parent — is_script_parent True
# ---------------------------------------------------------------------------


class TestScriptParent:
    def test_normalizes_without_raising(self):
        row = _load_fixture("script_parent")
        job = fis.normalize_row(row, location="us")
        assert isinstance(job, models.Job)

    def test_is_script_parent_true(self):
        row = _load_fixture("script_parent")
        job = fis.normalize_row(row, location="us")
        assert job.is_script_parent is True

    def test_reservation_id_none(self):
        row = _load_fixture("script_parent")
        job = fis.normalize_row(row, location="us")
        assert job.reservation_id is None

    def test_total_bytes_processed_none_not_zero(self):
        row = _load_fixture("script_parent")
        job = fis.normalize_row(row, location="us")
        assert job.total_bytes_processed is None

    def test_not_restricted_even_though_shape_matches(self):
        """SCRIPT 親は RESTRICTED ではなく NOT_AVAILABLE。

        SCRIPT 親は job_stages が空でバイト数も null になり、行レベル
        アクセスポリシーで制限された行と列の形が完全に一致する。
        statement_type で切り分けないと、存在しない権限問題を
        ユーザーに調べさせることになる。
        """
        row = _load_fixture("script_parent")
        job = fis.normalize_row(row, location="us")
        assert job.plan_availability is models.PlanAvailability.NOT_AVAILABLE
        assert job.plan_availability is not models.PlanAvailability.RESTRICTED

    def test_rls_shape_without_script_is_restricted(self):
        """同じ列の形でも statement_type が SCRIPT でなければ RESTRICTED。"""
        row = _load_fixture("script_parent")
        row["statement_type"] = "SELECT"
        job = fis.normalize_row(row, location="us")
        assert job.plan_availability is models.PlanAvailability.RESTRICTED


# ---------------------------------------------------------------------------
# fixture: rls_masked — RESTRICTED
# ---------------------------------------------------------------------------


class TestRlsMasked:
    def test_normalizes_without_raising(self):
        row = _load_fixture("rls_masked")
        job = fis.normalize_row(row, location="us")
        assert isinstance(job, models.Job)

    def test_plan_availability_restricted(self):
        row = _load_fixture("rls_masked")
        job = fis.normalize_row(row, location="us")
        assert job.plan_availability is models.PlanAvailability.RESTRICTED

    def test_bytes_fields_none(self):
        row = _load_fixture("rls_masked")
        job = fis.normalize_row(row, location="us")
        assert job.total_bytes_billed is None
        assert job.total_bytes_processed is None


# ---------------------------------------------------------------------------
# fixture: leaf_no_input_stages — input_stages キー欠落 / 存在
# ---------------------------------------------------------------------------


class TestLeafNoInputStages:
    def test_normalizes_without_raising(self):
        row = _load_fixture("leaf_no_input_stages")
        job = fis.normalize_row(row, location="us")
        assert isinstance(job, models.Job)

    def test_leaf_stage_input_stage_ids_empty_tuple(self):
        row = _load_fixture("leaf_no_input_stages")
        job = fis.normalize_row(row, location="us")
        stage0 = next(s for s in job.stages if s.id == 0)
        assert stage0.input_stage_ids == ()

    def test_later_stage_input_stage_ids(self):
        row = _load_fixture("leaf_no_input_stages")
        job = fis.normalize_row(row, location="us")
        stage1 = next(s for s in job.stages if s.id == 1)
        assert stage1.input_stage_ids == (0,)

    def test_plan_availability_available(self):
        row = _load_fixture("leaf_no_input_stages")
        job = fis.normalize_row(row, location="us")
        assert job.plan_availability is models.PlanAvailability.AVAILABLE
        assert job.has_plan is True


# ---------------------------------------------------------------------------
# 欠落カラム・欠落キーへの耐性
# ---------------------------------------------------------------------------


class TestMissingColumns:
    def test_missing_optional_column_is_none_no_keyerror(self):
        row = _load_fixture("cache_hit")
        row = dict(row)
        del row["resource_warning"]
        job = fis.normalize_row(row, location="us")
        assert job.resource_warning is None

    def test_labels_absent_is_empty_mapping(self):
        row = _load_fixture("cache_hit")
        row = dict(row)
        del row["labels"]
        job = fis.normalize_row(row, location="us")
        assert job.labels == {}

    def test_referenced_tables_absent_is_empty_tuple(self):
        row = _load_fixture("cache_hit")
        row = dict(row)
        del row["referenced_tables"]
        job = fis.normalize_row(row, location="us")
        assert job.referenced_tables == ()

    def test_input_stages_key_missing_on_single_stage_row(self):
        row = _load_fixture("leaf_no_input_stages")
        row = dict(row)
        # job_stages 内、2番目のステージから input_stages キーを削除しても
        # KeyError にならないこと（既にリーフ側は欠落しているが、念のため
        # 明示的に .get() 経路を再確認する）。
        stages = [dict(s) for s in row["job_stages"]]
        stages[1].pop("input_stages", None)
        row["job_stages"] = stages
        job = fis.normalize_row(row, location="us")
        stage1 = next(s for s in job.stages if s.id == 1)
        assert stage1.input_stage_ids == ()


# ---------------------------------------------------------------------------
# has_plan の一般契約
# ---------------------------------------------------------------------------


class TestHasPlan:
    @pytest.mark.parametrize(
        "fixture_name,expected",
        [
            ("skewed_join", True),
            ("spill_heavy", True),
            ("cache_hit", False),
            ("script_parent", False),
            ("rls_masked", False),
            ("leaf_no_input_stages", True),
        ],
    )
    def test_has_plan(self, fixture_name, expected):
        row = _load_fixture(fixture_name)
        job = fis.normalize_row(row, location="us")
        assert job.has_plan is expected


# ---------------------------------------------------------------------------
# ネットワーク非依存の確認
# ---------------------------------------------------------------------------


class TestNoNetworkImports:
    def test_module_does_not_import_google_cloud(self):
        import ast
        import sys

        mod = sys.modules[fis.__name__]
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
        assert not hasattr(fis, "bigquery")
        assert "google" not in dir(fis)
