"""`InformationSchemaCollector` の純粋関数部分のテスト。

方針（REVIEW_GUIDE.md 2.3 に従う）:
- `bigquery.Client` をモックして「呼ばれたこと」を検証するテストは書かない。
- 時間窓の拡大ロジック・エラー分類ロジックはどちらも純粋関数へ切り出し、
  クライアント無しで直接テストする。
- クエリパラメータ変換（ScalarParam/ArrayParam -> 実 SDK オブジェクト）は
  実際に `google.cloud.bigquery` の型を import して属性を比較する
  （これはモックではなく、宣言済み依存の実オブジェクトを使う統合的検証）。
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from google.cloud import bigquery

from bq_job_diagnose.collect.information_schema import (
    _classify_forbidden,
    _translate_param,
    _widen_windows,
)
from bq_job_diagnose.collect.sql import ArrayParam, ScalarParam
from bq_job_diagnose.errors import PermissionFallbackNeeded

# ---------------------------------------------------------------------------
# 1. パラメータ変換
# ---------------------------------------------------------------------------


class TestTranslateParam:
    def test_scalar_param_translates_to_scalar_query_parameter(self):
        p = ScalarParam("top_n", "INT64", 20)
        result = _translate_param(p)
        assert isinstance(result, bigquery.ScalarQueryParameter)
        assert result.name == "top_n"
        assert result.type_ == "INT64"
        assert result.value == 20

    def test_scalar_param_with_timestamp_type(self):
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        p = ScalarParam("start_time", "TIMESTAMP", ts)
        result = _translate_param(p)
        assert isinstance(result, bigquery.ScalarQueryParameter)
        assert result.type_ == "TIMESTAMP"
        assert result.value == ts

    def test_array_param_translates_to_array_query_parameter(self):
        p = ArrayParam("job_ids", "STRING", ("a", "b", "c"))
        result = _translate_param(p)
        assert isinstance(result, bigquery.ArrayQueryParameter)
        assert result.name == "job_ids"
        assert result.array_type == "STRING"
        assert list(result.values) == ["a", "b", "c"]

    def test_unknown_param_type_raises(self):
        with pytest.raises(TypeError):
            _translate_param(object())


# ---------------------------------------------------------------------------
# 2. 時間窓の拡大ロジック（純粋関数）
# ---------------------------------------------------------------------------


class TestWidenWindows:
    def test_widen_windows_with_created_on_given(self):
        created_on = date(2026, 6, 15)
        now = datetime(2026, 9, 21, tzinfo=UTC)
        windows = _widen_windows(created_on, now)

        # created_on 指定時は「その日 ± 1日」の単一ウィンドウのみ。
        assert len(windows) == 1
        lower, upper = windows[0]
        assert lower == datetime(2026, 6, 14, tzinfo=UTC)
        assert upper == datetime(2026, 6, 16, tzinfo=UTC)

    def test_widen_windows_without_created_on_progressively_widens(self):
        now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=UTC)
        windows = _widen_windows(None, now)

        assert len(windows) == 3
        expected_days = [7, 30, 180]
        for (lower, upper), days in zip(windows, expected_days, strict=True):
            assert upper == now
            assert lower == now - timedelta(days=days)

    def test_widen_windows_order_is_narrow_to_wide(self):
        now = datetime(2026, 9, 21, tzinfo=UTC)
        windows = _widen_windows(None, now)
        spans = [(upper - lower) for lower, upper in windows]
        assert spans == sorted(spans), "狭い順（7d -> 30d -> 180d）に並んでいること"


# ---------------------------------------------------------------------------
# 3. エラー分類ロジック（純粋関数）
# ---------------------------------------------------------------------------


class TestClassifyForbidden:
    def test_message_mentioning_jobs_list_all_classified_as_permission_fallback(self):
        msg = (
            "403 Access Denied: User does not have bigquery.jobs.listAll "
            "permission in project my-project"
        )
        result = _classify_forbidden(msg)
        assert result is PermissionFallbackNeeded

    def test_unrelated_forbidden_message_returns_none(self):
        msg = "403 Access Denied: BigQuery BigQuery: Permission denied on table."
        result = _classify_forbidden(msg)
        assert result is None

    def test_case_insensitive_or_partial_match_still_detects_jobs_list_all(self):
        msg = "Forbidden: missing permission bigquery.jobs.listAll on the project"
        result = _classify_forbidden(msg)
        assert result is PermissionFallbackNeeded
