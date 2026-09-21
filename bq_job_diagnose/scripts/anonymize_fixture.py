"""取得した生データ（INFORMATION_SCHEMA 行 / jobs.get properties）を匿名化する。

フィクスチャ採取（`--dump-raw`）から呼ばれる再利用可能な関数。学習リポジトリで
公開 PR を出す前提のため、実データが誤ってコミットされることを防ぐ目的で
`InformationSchemaCollector` / `JobsApiCollector` のダンプ経路から必ず通す。

匿名化する項目（REVIEW_GUIDE.md 2.4 に列挙されているものと同じ）:
- user_email -> "user@example.com"
- project_id -> "example-project"
- query -> "-- anonymized"
- referenced_tables の各エントリ -> ダミーのテーブル名
- labels -> {}

このモジュールは INFORMATION_SCHEMA 由来（snake_case）と jobs.get 由来
（camelCase, jobReference 等のネスト構造）の両方の形を受け付ける。
"""

from __future__ import annotations

import copy
from typing import Any

_ANON_USER_EMAIL = "user@example.com"
_ANON_PROJECT_ID = "example-project"
_ANON_QUERY = "-- anonymized"


def _anonymize_table_ref_is(ref: dict[str, Any], index: int) -> dict[str, Any]:
    """INFORMATION_SCHEMA 形式（project_id/dataset_id/table_id）のテーブル参照を匿名化する。"""
    return {
        "project_id": _ANON_PROJECT_ID,
        "dataset_id": f"dummy_dataset_{index}",
        "table_id": f"dummy_table_{index}",
    }


def _anonymize_table_ref_rest(ref: dict[str, Any], index: int) -> dict[str, Any]:
    """REST 形式（projectId/datasetId/tableId）のテーブル参照を匿名化する。"""
    return {
        "projectId": _ANON_PROJECT_ID,
        "datasetId": f"dummy_dataset_{index}",
        "tableId": f"dummy_table_{index}",
    }


def anonymize_row(row: dict[str, Any]) -> dict[str, Any]:
    """INFORMATION_SCHEMA の1行（Mapping）を匿名化したコピーとして返す。

    元の `row` は変更しない（deepcopy してから書き換える）。列にないフィールドは
    そのまま素通りする。
    """
    out = copy.deepcopy(row)

    if "user_email" in out and out["user_email"] is not None:
        out["user_email"] = _ANON_USER_EMAIL
    if "project_id" in out and out["project_id"] is not None:
        out["project_id"] = _ANON_PROJECT_ID
    if "query" in out and out["query"] is not None:
        out["query"] = _ANON_QUERY

    if out.get("referenced_tables"):
        out["referenced_tables"] = [
            _anonymize_table_ref_is(t, i) for i, t in enumerate(out["referenced_tables"])
        ]
    if out.get("destination_table") is not None:
        out["destination_table"] = _anonymize_table_ref_is(out["destination_table"], 0)

    if "labels" in out:
        out["labels"] = []

    return out


def anonymize_job_properties(job_properties: dict[str, Any]) -> dict[str, Any]:
    """jobs.get の生 properties dict（REST/camelCase・ネスト構造）を匿名化したコピーとして返す。"""
    out = copy.deepcopy(job_properties)

    job_reference = out.get("jobReference")
    if isinstance(job_reference, dict) and job_reference.get("projectId") is not None:
        job_reference["projectId"] = _ANON_PROJECT_ID

    if "user_email" in out and out["user_email"] is not None:
        out["user_email"] = _ANON_USER_EMAIL

    statistics = out.get("statistics")
    if isinstance(statistics, dict):
        if statistics.get("userEmail") is not None:
            statistics["userEmail"] = _ANON_USER_EMAIL
        query_stats = statistics.get("query")
        if isinstance(query_stats, dict) and query_stats.get("referencedTables"):
            query_stats["referencedTables"] = [
                _anonymize_table_ref_rest(t, i)
                for i, t in enumerate(query_stats["referencedTables"])
            ]

    configuration = out.get("configuration")
    if isinstance(configuration, dict):
        if "labels" in configuration:
            configuration["labels"] = {}
        query_config = configuration.get("query")
        if isinstance(query_config, dict) and query_config.get("query") is not None:
            query_config["query"] = _ANON_QUERY
        if isinstance(query_config, dict) and query_config.get("destinationTable") is not None:
            query_config["destinationTable"] = _anonymize_table_ref_rest(
                query_config["destinationTable"], 0
            )

    return out
