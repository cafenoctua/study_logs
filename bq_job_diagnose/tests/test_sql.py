"""collect/sql.py のテスト。

TDD: このテストを先に書き、失敗することを確認してから collect/sql.py を実装する。

このモジュールが検証する境界線:
- collect/sql.py はネットワーク呼び出しを一切行わない純粋関数の集合であること
  （google.cloud を import しないこと）。
- region / project_id はクエリパラメータで束縛できない「識別子」なので、
  f-string 埋め込み前に厳格な正規表現でバリデーションされていること
  （SQL インジェクション対策の要）。
- 各ビルダーが creation_time によるパーティションプルーニング条件を
  必ず含んでいること（省略すると180日分フルスキャンになる）。
- 返り値の SQL 文字列に現れる `@param` と、返り値のパラメータリストが
  一対一で対応していること。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from bq_job_diagnose.collect import sql

# ---------------------------------------------------------------------------
# 共通フィクスチャ・ヘルパー
# ---------------------------------------------------------------------------

START = datetime(2026, 9, 13, 0, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 20, 0, 0, 0, tzinfo=UTC)


def _param_names_in_sql(text: str) -> set[str]:
    """SQL 文字列中に現れる @param 名の集合を返す。"""
    return set(re.findall(r"@(\w+)", text))


def _param_names_in_params(params: list) -> set[str]:
    """返り値の params リストに含まれる name の集合を返す。"""
    return {p.name for p in params}


def _assert_params_consistent(text: str, params: list) -> None:
    """SQL 中の @param と params リストが完全に一致することを確認する。"""
    in_sql = _param_names_in_sql(text)
    in_params = _param_names_in_params(params)
    assert in_sql == in_params, (
        f"SQL とパラメータが不一致: SQL のみ={in_sql - in_params}, "
        f"params のみ={in_params - in_sql}"
    )


# ---------------------------------------------------------------------------
# validate_region
# ---------------------------------------------------------------------------


class TestValidateRegion:
    def test_plain_region_passes_through(self):
        assert sql.validate_region("us") == "us"

    def test_region_prefix_stripped(self):
        assert sql.validate_region("region-us") == "us"

    def test_asia_northeast1(self):
        assert sql.validate_region("asia-northeast1") == "asia-northeast1"

    def test_region_prefix_not_doubled(self):
        # "region-us" -> "us" のみで、"region-region-us" にはならない
        result = sql.validate_region("region-us")
        assert result == "us"
        assert not result.startswith("region-")

    def test_uppercase_raises(self):
        # 大文字は正規化せず拒否する方針（実装で明示的にドキュメント化する）
        with pytest.raises(ValueError):
            sql.validate_region("US")

    @pytest.mark.parametrize(
        "malicious",
        [
            "us`; DROP TABLE x--",
            "us' OR '1'='1",
            "../../etc",
            "",
            "us; SELECT 1",
            "us OR 1=1",
            "us\nSELECT",
            "us US",
            "`us`",
        ],
    )
    def test_injection_attempts_raise(self, malicious):
        with pytest.raises(ValueError):
            sql.validate_region(malicious)


# ---------------------------------------------------------------------------
# validate_project_id
# ---------------------------------------------------------------------------


class TestValidateProjectId:
    def test_valid_project_id_passes(self):
        assert sql.validate_project_id("my-project") == "my-project"

    def test_valid_project_id_with_digits(self):
        assert sql.validate_project_id("my-project-123") == "my-project-123"

    def test_domain_scoped_project_id(self):
        assert sql.validate_project_id("google.com:my-project") == "google.com:my-project"

    @pytest.mark.parametrize(
        "malicious",
        [
            "my-project`; DROP TABLE x--",
            "my-project' OR '1'='1",
            "../../etc",
            "",
            "my project",
            "my-project; SELECT 1",
            "`my-project`",
        ],
    )
    def test_injection_attempts_raise(self, malicious):
        with pytest.raises(ValueError):
            sql.validate_project_id(malicious)


# ---------------------------------------------------------------------------
# 全ビルダー共通の契約テスト
# ---------------------------------------------------------------------------


def _build_all_for_contract_tests():
    """全ビルダーの (name, sql, params) タプルのリストを返す。"""
    results = []

    text, params = sql.build_scan_sql(
        project_id="my-project",
        region="asia-northeast1",
        start_time=START,
        end_time=END,
        top_n=20,
        rank_by="slot_ms",
        user_email=None,
        min_slot_ms=None,
    )
    results.append(("build_scan_sql", text, params))

    text, params = sql.build_job_sql(
        project_id="my-project",
        region="asia-northeast1",
        job_id="job123",
        creation_time_lower=START,
        creation_time_upper=END,
    )
    results.append(("build_job_sql", text, params))

    text, params = sql.build_children_sql(
        project_id="my-project",
        region="asia-northeast1",
        parent_job_id="parent123",
        creation_time_lower=START,
        creation_time_upper=END,
    )
    results.append(("build_children_sql", text, params))

    text, params = sql.build_drill_sql(
        project_id="my-project",
        region="asia-northeast1",
        job_ids=["job1", "job2"],
        start_time=START,
        end_time=END,
    )
    results.append(("build_drill_sql", text, params))

    text, params = sql.build_repeated_query_sql(
        project_id="my-project",
        region="asia-northeast1",
        start_time=START,
        end_time=END,
        min_count=20,
        min_bytes=100,
    )
    results.append(("build_repeated_query_sql", text, params))

    return results


ALL_BUILDERS = _build_all_for_contract_tests()


class TestPartitionPruningContract:
    @pytest.mark.parametrize("name,text,params", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
    def test_has_creation_time_lower_bound(self, name, text, params):
        assert "creation_time >=" in text, f"{name}: creation_time >= 条件がありません"

    @pytest.mark.parametrize("name,text,params", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
    def test_has_start_time_param_reference(self, name, text, params):
        # start_time または creation_time_lower のいずれかの param 名を使う
        param_names = _param_names_in_params(params)
        lower_bound_names = {"start_time", "creation_time_lower"}
        assert param_names & lower_bound_names, (
            f"{name}: creation_time の下限パラメータが見当たりません（{param_names}）"
        )


class TestParamSqlConsistency:
    @pytest.mark.parametrize("name,text,params", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
    def test_params_consistent(self, name, text, params):
        _assert_params_consistent(text, params)


class TestNoSelectStar:
    @pytest.mark.parametrize("name,text,params", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
    def test_no_select_star(self, name, text, params):
        assert "SELECT *" not in text.upper().replace("\n", " ")
        assert re.search(r"SELECT\s+\*", text, re.IGNORECASE) is None


# ---------------------------------------------------------------------------
# SCRIPT 除外の契約
# ---------------------------------------------------------------------------


class TestScriptExclusion:
    def test_scan_excludes_script(self):
        text, _ = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "statement_type != 'SCRIPT'" in text

    def test_repeated_query_excludes_script(self):
        text, _ = sql.build_repeated_query_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            min_count=20,
            min_bytes=100,
        )
        assert "statement_type != 'SCRIPT'" in text

    def test_job_sql_does_not_exclude_script(self):
        text, _ = sql.build_job_sql(
            project_id="my-project",
            region="us",
            job_id="job123",
            creation_time_lower=START,
            creation_time_upper=END,
        )
        assert "statement_type != 'SCRIPT'" not in text


# ---------------------------------------------------------------------------
# build_scan_sql の詳細
# ---------------------------------------------------------------------------


class TestBuildScanSql:
    def test_region_interpolated_into_table_path(self):
        text, _ = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "`region-us`" in text
        assert "`my-project`" in text

    def test_region_prefix_not_doubled_in_sql(self):
        text, _ = sql.build_scan_sql(
            project_id="my-project",
            region="region-us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "`region-us`" in text
        assert "region-region-us" not in text

    def test_does_not_select_job_stages_or_timeline(self):
        text, _ = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "job_stages" not in text
        assert "timeline" not in text

    @pytest.mark.parametrize(
        "rank_by,expected_expr",
        [
            ("slot_ms", "total_slot_ms"),
            ("bytes_billed", "total_bytes_billed"),
            ("elapsed", "TIMESTAMP_DIFF(end_time, start_time, MILLISECOND)"),
        ],
    )
    def test_rank_by_maps_to_expected_order_by(self, rank_by, expected_expr):
        text, _ = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by=rank_by,
            user_email=None,
            min_slot_ms=None,
        )
        order_by_clause = text[text.upper().index("ORDER BY"):]
        assert expected_expr in order_by_clause

    def test_unknown_rank_by_raises(self):
        with pytest.raises(ValueError):
            sql.build_scan_sql(
                project_id="my-project",
                region="us",
                start_time=START,
                end_time=END,
                top_n=20,
                rank_by="totally_bogus",  # type: ignore[arg-type]
                user_email=None,
                min_slot_ms=None,
            )

    def test_top_n_bound_via_param(self):
        text, params = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "@top_n" in text
        assert any(p.name == "top_n" and p.value == 20 for p in params)

    def test_user_email_filter_included_when_given(self):
        text, params = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email="alice@example.com",
            min_slot_ms=None,
        )
        assert "@user_email" in text
        assert any(p.name == "user_email" and p.value == "alice@example.com" for p in params)

    def test_user_email_filter_absent_when_none(self):
        text, _params = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "@user_email" not in text

    def test_min_slot_ms_filter_included_when_given(self):
        text, params = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=1000,
        )
        assert "@min_slot_ms" in text
        assert any(p.name == "min_slot_ms" and p.value == 1000 for p in params)

    def test_min_slot_ms_filter_absent_when_none(self):
        text, _params = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "@min_slot_ms" not in text

    def test_where_filters_query_job_type_done_state(self):
        text, _ = sql.build_scan_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            top_n=20,
            rank_by="slot_ms",
            user_email=None,
            min_slot_ms=None,
        )
        assert "job_type = 'QUERY'" in text
        assert "state = 'DONE'" in text


# ---------------------------------------------------------------------------
# build_job_sql の詳細
# ---------------------------------------------------------------------------


class TestBuildJobSql:
    def test_selects_job_stages_and_timeline(self):
        text, _ = sql.build_job_sql(
            project_id="my-project",
            region="us",
            job_id="job123",
            creation_time_lower=START,
            creation_time_upper=END,
        )
        assert "job_stages" in text
        assert "timeline" in text

    def test_job_id_bound_via_param(self):
        text, params = sql.build_job_sql(
            project_id="my-project",
            region="us",
            job_id="job123",
            creation_time_lower=START,
            creation_time_upper=END,
        )
        assert "@job_id" in text
        assert any(p.name == "job_id" and p.value == "job123" for p in params)

    def test_still_has_creation_time_upper_bound(self):
        text, _params = sql.build_job_sql(
            project_id="my-project",
            region="us",
            job_id="job123",
            creation_time_lower=START,
            creation_time_upper=END,
        )
        assert "creation_time <=" in text or "creation_time <" in text


# ---------------------------------------------------------------------------
# build_children_sql の詳細
# ---------------------------------------------------------------------------


class TestBuildChildrenSql:
    def test_filters_by_parent_job_id(self):
        text, params = sql.build_children_sql(
            project_id="my-project",
            region="us",
            parent_job_id="parent123",
            creation_time_lower=START,
            creation_time_upper=END,
        )
        assert "parent_job_id = @parent_job_id" in text
        assert any(p.name == "parent_job_id" and p.value == "parent123" for p in params)

    def test_uses_lightweight_columns_only(self):
        text, _ = sql.build_children_sql(
            project_id="my-project",
            region="us",
            parent_job_id="parent123",
            creation_time_lower=START,
            creation_time_upper=END,
        )
        assert "job_stages" not in text
        assert "timeline" not in text


# ---------------------------------------------------------------------------
# build_drill_sql の詳細
# ---------------------------------------------------------------------------


class TestBuildDrillSql:
    def test_job_ids_bound_via_array_param(self):
        text, params = sql.build_drill_sql(
            project_id="my-project",
            region="us",
            job_ids=["job1", "job2", "job3"],
            start_time=START,
            end_time=END,
        )
        assert "UNNEST(@job_ids)" in text
        matching = [p for p in params if p.name == "job_ids"]
        assert len(matching) == 1
        assert tuple(matching[0].values) == ("job1", "job2", "job3")

    def test_full_columns_included(self):
        text, _ = sql.build_drill_sql(
            project_id="my-project",
            region="us",
            job_ids=["job1"],
            start_time=START,
            end_time=END,
        )
        assert "job_stages" in text
        assert "timeline" in text

    def test_cap_at_50_ok(self):
        job_ids = [f"job{i}" for i in range(50)]
        text, _params = sql.build_drill_sql(
            project_id="my-project",
            region="us",
            job_ids=job_ids,
            start_time=START,
            end_time=END,
        )
        assert text  # 例外が出ないこと

    def test_cap_over_50_raises(self):
        job_ids = [f"job{i}" for i in range(51)]
        with pytest.raises(ValueError):
            sql.build_drill_sql(
                project_id="my-project",
                region="us",
                job_ids=job_ids,
                start_time=START,
                end_time=END,
            )


# ---------------------------------------------------------------------------
# build_repeated_query_sql の詳細
# ---------------------------------------------------------------------------


class TestBuildRepeatedQuerySql:
    def test_group_by_and_having(self):
        text, _params = sql.build_repeated_query_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            min_count=20,
            min_bytes=100,
        )
        assert "GROUP BY" in text
        assert "HAVING" in text
        assert "@min_count" in text
        assert "@min_bytes" in text

    def test_cache_hit_false_filter(self):
        text, _ = sql.build_repeated_query_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            min_count=20,
            min_bytes=100,
        )
        assert "cache_hit = FALSE" in text

    def test_orders_by_total_bytes_billed_desc_limit_50(self):
        text, _ = sql.build_repeated_query_sql(
            project_id="my-project",
            region="us",
            start_time=START,
            end_time=END,
            min_count=20,
            min_bytes=100,
        )
        assert "ORDER BY total_bytes_billed DESC" in text
        assert "LIMIT 50" in text


# ---------------------------------------------------------------------------
# ネットワーク非依存の確認（constraint 1）
# ---------------------------------------------------------------------------


class TestNoNetworkImports:
    def test_module_does_not_import_google_cloud(self):
        import ast
        import sys

        mod = sys.modules[sql.__name__]
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
        assert not hasattr(sql, "bigquery")
        assert "google" not in dir(sql)
