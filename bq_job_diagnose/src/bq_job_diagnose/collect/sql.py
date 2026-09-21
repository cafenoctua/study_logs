"""BigQuery INFORMATION_SCHEMA.JOBS_BY_PROJECT 向けの SQL を組み立てる純粋関数群。

設計上の制約（重要）:
- このモジュールはネットワーク呼び出しを一切行わない。`google.cloud` を
  import してはならない（実際の BigQuery API 呼び出しは Phase 10 で追加する
  別モジュールの責務）。
- クエリパラメータ（`@name`）で束縛できるのは「値」のみで「識別子」は
  束縛できない。region と project_id はテーブルパス内の識別子であるため
  f-string で埋め込む必要があり、これがこのモジュール唯一の危険地帯になる。
  そのため `validate_region` / `validate_project_id` で厳格な正規表現
  バリデーションを行ってから埋め込む。それ以外のユーザー入力はすべて
  クエリパラメータ経由で渡す。
- `creation_time` によるパーティションプルーニングは BigQuery 側で強制
  されない（省略すると `JOBS_BY_PROJECT` の全期間＝最大180日をフルスキャン
  してしまう）。そのため全ビルダーが `creation_time >= @start_time`
  （job系は `creation_time_lower` / `creation_time_upper`）を必ず含む。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# ---------------------------------------------------------------------------
# パラメータ表現（google.cloud.bigquery.ScalarQueryParameter 等の代わりに
# このモジュール内で完結する軽量な dataclass を使う。Phase 10 で実 SDK の
# オブジェクトへ変換する）。
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScalarParam:
    """単一値のクエリパラメータ。"""

    name: str
    type_: str  # "STRING" / "TIMESTAMP" / "INT64" など
    value: object


@dataclass(frozen=True, slots=True)
class ArrayParam:
    """配列値のクエリパラメータ（UNNEST と組み合わせて使う）。"""

    name: str
    element_type: str
    values: tuple


# ---------------------------------------------------------------------------
# バリデーション（識別子はパラメータ化できないため、埋め込み前に厳格化する）
# ---------------------------------------------------------------------------

_REGION_RE = re.compile(r"^[a-z0-9-]+$")
_PROJECT_ID_STRICT_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
# google.com: のようなドメインスコープ付きプロジェクトIDを許容するための
# 緩いフォールバック。コロンを含みうる点が唯一 STRICT と異なる。
# ドット・コロン・ハイフンのみを追加許容し、空白・バッククォート・引用符・
# セミコロン等は依然として拒否される。
_PROJECT_ID_DOMAIN_SCOPED_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*:[a-z][a-z0-9-]{4,28}[a-z0-9]$")


def validate_region(region: str) -> str:
    """region 文字列を検証し、`region-` プレフィックスを外して正規化する。

    - 受理するのは `^[a-z0-9-]+$`（小文字・数字・ハイフンのみ）。
    - 先頭の `region-` は剥がす（`us` でも `region-us` でも同じ結果になる
      ようにする。剥がした後は正規表現の再検証は行わないが、剥がす前の
      文字列全体が既に許可文字集合であることを確認済みなので安全）。
    - 大文字は正規化せず拒否する（`US` は ValueError）。BigQuery の region
      名は実運用上すべて小文字であり、大文字を安易に小文字化すると
      呼び出し元の入力ミスを隠してしまうため、明示的に拒否する方針とする。
    - バッククォート・引用符・セミコロン・空白・SQL キーワードのような
      危険な入力は、許可文字集合の外にあるため正規表現で自動的に弾かれる。
    """
    if not region:
        raise ValueError("region が空文字です")
    if not _REGION_RE.match(region):
        raise ValueError(
            f"region の形式が不正です（小文字・数字・ハイフンのみ許可）: {region!r}"
        )
    region = region.removeprefix("region-")
    if not region:
        raise ValueError("region が空文字です（'region-' のみが指定されました）")
    return region


def validate_project_id(project_id: str) -> str:
    """BigQuery project_id を検証する。

    通常の project_id は `^[a-z][a-z0-9-]{4,28}[a-z0-9]$`（6〜30文字、
    先頭は英字、末尾は英数字）。加えて `google.com:my-project` のような
    ドメインスコープ付きプロジェクト（主に旧式の Google Apps 管理プロジェクト）
    にも対応するため、コロンを含む緩いフォールバックパターンも許可する。
    いずれのパターンも小文字・数字・ハイフン・ドット・コロンの範囲でしか
    マッチしないため、バッククォート・引用符・セミコロン・空白は必ず拒否される。
    """
    if not project_id:
        raise ValueError("project_id が空文字です")
    if _PROJECT_ID_STRICT_RE.match(project_id):
        return project_id
    if _PROJECT_ID_DOMAIN_SCOPED_RE.match(project_id):
        return project_id
    raise ValueError(
        "project_id の形式が不正です"
        "（例: 'my-project' または 'google.com:my-project'）: "
        f"{project_id!r}"
    )


# ---------------------------------------------------------------------------
# rank_by -> ORDER BY 式の固定マッピング（ユーザー入力を生の SQL として
# 解釈させないため、既知の安全な式のみに限定する）
# ---------------------------------------------------------------------------

RankBy = Literal["slot_ms", "bytes_billed", "elapsed"]

_RANK_BY_EXPR: dict[str, str] = {
    "slot_ms": "total_slot_ms",
    "bytes_billed": "total_bytes_billed",
    "elapsed": "TIMESTAMP_DIFF(end_time, start_time, MILLISECOND)",
}


def _rank_by_expr(rank_by: str) -> str:
    try:
        return _RANK_BY_EXPR[rank_by]
    except KeyError:
        valid = ", ".join(sorted(_RANK_BY_EXPR))
        raise ValueError(f"未知の rank_by です: {rank_by!r}（有効な値: {valid}）") from None


def _table_path(project_id: str, region: str) -> str:
    """`` `project`.`region-xx`.INFORMATION_SCHEMA.JOBS_BY_PROJECT `` を組み立てる。"""
    safe_project = validate_project_id(project_id)
    safe_region = validate_region(region)
    return f"`{safe_project}`.`region-{safe_region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT"


# ---------------------------------------------------------------------------
# カラムリスト（SELECT * は使わない）
# ---------------------------------------------------------------------------

_SCAN_COLUMNS = """\
  job_id,
  parent_job_id,
  project_id,
  user_email,
  creation_time,
  start_time,
  end_time,
  job_type,
  statement_type,
  priority,
  state,
  error_result IS NOT NULL AS has_error,
  cache_hit,
  total_bytes_processed,
  total_bytes_billed,
  total_slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS elapsed_ms,
  reservation_id,
  edition,
  query_info.resource_warning AS resource_warning,
  query_info.query_hashes.normalized_literals AS normalized_literals_hash,
  ARRAY_LENGTH(referenced_tables) AS referenced_table_count,
  SUBSTR(query, 1, 4096) AS query_head"""

# build_job_sql / build_drill_sql 向けのフルカラムセット。
# scan の軽量カラムに加え、job_stages / timeline / query 本文等の重量級
# フィールドを含む（TopN で使うと高コストになるため scan では使わない）。
_FULL_COLUMNS = """\
  job_id,
  parent_job_id,
  project_id,
  user_email,
  creation_time,
  start_time,
  end_time,
  job_type,
  statement_type,
  priority,
  state,
  error_result,
  error_result IS NOT NULL AS has_error,
  cache_hit,
  total_bytes_processed,
  total_bytes_billed,
  total_slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS elapsed_ms,
  reservation_id,
  edition,
  query_info.resource_warning AS resource_warning,
  query_info.query_hashes.normalized_literals AS normalized_literals_hash,
  query_info.performance_insights AS performance_insights,
  ARRAY_LENGTH(referenced_tables) AS referenced_table_count,
  query,
  referenced_tables,
  destination_table,
  labels,
  dml_statistics,
  job_stages,
  timeline"""


# ---------------------------------------------------------------------------
# 1. build_scan_sql — 期間スキャン・TopN
# ---------------------------------------------------------------------------


def build_scan_sql(
    *,
    project_id: str,
    region: str,
    start_time: datetime,
    end_time: datetime,
    top_n: int,
    rank_by: RankBy,
    user_email: str | None = None,
    min_slot_ms: int | None = None,
) -> tuple[str, list]:
    """期間内のジョブを rank_by 基準で TopN 抽出する SQL を組み立てる。

    軽量カラムのみを選択する（job_stages / timeline は含めない）。
    TopN × フルプランを取得すると数十MB規模になり、スキャン自体が高コストな
    クエリになってしまうため。
    """
    order_expr = _rank_by_expr(rank_by)
    table = _table_path(project_id, region)

    params: list = [
        ScalarParam("start_time", "TIMESTAMP", start_time),
        ScalarParam("end_time", "TIMESTAMP", end_time),
        ScalarParam("top_n", "INT64", top_n),
    ]

    where_clauses = [
        "creation_time >= @start_time",
        "creation_time <= @end_time",
        "job_type = 'QUERY'",
        "state = 'DONE'",
        "statement_type != 'SCRIPT'",
    ]

    if user_email is not None:
        where_clauses.append("user_email = @user_email")
        params.append(ScalarParam("user_email", "STRING", user_email))

    if min_slot_ms is not None:
        where_clauses.append("total_slot_ms >= @min_slot_ms")
        params.append(ScalarParam("min_slot_ms", "INT64", min_slot_ms))

    where_sql = "\n  AND ".join(where_clauses)

    text = f"""\
SELECT
{_SCAN_COLUMNS}
FROM {table}
WHERE {where_sql}
ORDER BY {order_expr} DESC
LIMIT @top_n"""

    return text, params


# ---------------------------------------------------------------------------
# 2. build_job_sql — 単一ジョブの詳細取得
# ---------------------------------------------------------------------------


def build_job_sql(
    *,
    project_id: str,
    region: str,
    job_id: str,
    creation_time_lower: datetime,
    creation_time_upper: datetime,
) -> tuple[str, list]:
    """単一ジョブの詳細（job_stages / timeline 含むフルカラム）を取得する SQL。

    job_id で一意に絞り込む場合でも creation_time の範囲指定は必須
    （パーティションプルーニングは BigQuery 側で自動には効かない）。
    ユーザーが明示的に SCRIPT の親ジョブを指定した場合はそれをそのまま
    返す必要があるため、statement_type による除外は行わない。
    """
    table = _table_path(project_id, region)

    params: list = [
        ScalarParam("creation_time_lower", "TIMESTAMP", creation_time_lower),
        ScalarParam("creation_time_upper", "TIMESTAMP", creation_time_upper),
        ScalarParam("job_id", "STRING", job_id),
    ]

    text = f"""\
SELECT
{_FULL_COLUMNS}
FROM {table}
WHERE creation_time >= @creation_time_lower
  AND creation_time <= @creation_time_upper
  AND job_id = @job_id"""

    return text, params


# ---------------------------------------------------------------------------
# 3. build_children_sql — SCRIPT 親ジョブの子ジョブ一覧
# ---------------------------------------------------------------------------


def build_children_sql(
    *,
    project_id: str,
    region: str,
    parent_job_id: str,
    creation_time_lower: datetime,
    creation_time_upper: datetime,
) -> tuple[str, list]:
    """SCRIPT 親ジョブの子ジョブを軽量カラムで列挙する SQL。

    「この SCRIPT には N 個の子ジョブがある」ことを報告するためのもので、
    合算処理は行わない（子ジョブの total_slot_ms を安易に合計すると
    親ジョブの値と二重計上になるため、集計は呼び出し側の責務とする）。
    """
    table = _table_path(project_id, region)

    params: list = [
        ScalarParam("creation_time_lower", "TIMESTAMP", creation_time_lower),
        ScalarParam("creation_time_upper", "TIMESTAMP", creation_time_upper),
        ScalarParam("parent_job_id", "STRING", parent_job_id),
    ]

    text = f"""\
SELECT
{_SCAN_COLUMNS}
FROM {table}
WHERE creation_time >= @creation_time_lower
  AND creation_time <= @creation_time_upper
  AND parent_job_id = @parent_job_id"""

    return text, params


# ---------------------------------------------------------------------------
# 4. build_drill_sql — job_id 群での一括取得
# ---------------------------------------------------------------------------

_DRILL_JOB_IDS_MAX = 50


def build_drill_sql(
    *,
    project_id: str,
    region: str,
    job_ids: list[str] | tuple[str, ...],
    start_time: datetime,
    end_time: datetime,
) -> tuple[str, list]:
    """job_id 群に対してフルカラム（job_stages / timeline 含む）を一括取得する SQL。

    プラン全体のボリュームが実用上の限界を超えないよう、job_ids の件数に
    上限（50件）を設ける。
    """
    if len(job_ids) > _DRILL_JOB_IDS_MAX:
        raise ValueError(
            f"job_ids は最大 {_DRILL_JOB_IDS_MAX} 件までです（{len(job_ids)} 件指定されました）"
        )
    if len(job_ids) == 0:
        raise ValueError("job_ids が空です")

    table = _table_path(project_id, region)

    params: list = [
        ScalarParam("start_time", "TIMESTAMP", start_time),
        ScalarParam("end_time", "TIMESTAMP", end_time),
        ArrayParam("job_ids", "STRING", tuple(job_ids)),
    ]

    text = f"""\
SELECT
{_FULL_COLUMNS}
FROM {table}
WHERE creation_time >= @start_time
  AND creation_time <= @end_time
  AND job_id IN UNNEST(@job_ids)"""

    return text, params


# ---------------------------------------------------------------------------
# 5. build_repeated_query_sql — 繰り返しクエリの集計
# ---------------------------------------------------------------------------


def build_repeated_query_sql(
    *,
    project_id: str,
    region: str,
    start_time: datetime,
    end_time: datetime,
    min_count: int,
    min_bytes: int,
) -> tuple[str, list]:
    """正規化済みクエリハッシュ単位で実行回数・コストを集計する SQL。

    cache_hit のジョブは実コストがゼロに近く「繰り返し実行のコスト」という
    観点では意味を持たないため除外する。SCRIPT も個別クエリの集計対象では
    ないため除外する。
    """
    table = _table_path(project_id, region)

    params: list = [
        ScalarParam("start_time", "TIMESTAMP", start_time),
        ScalarParam("end_time", "TIMESTAMP", end_time),
        ScalarParam("min_count", "INT64", min_count),
        ScalarParam("min_bytes", "INT64", min_bytes),
    ]

    text = f"""\
SELECT
  query_info.query_hashes.normalized_literals AS normalized_literals_hash,
  COUNT(*) AS execution_count,
  SUM(total_bytes_billed) AS total_bytes_billed,
  SUM(total_slot_ms) AS total_slot_ms,
  ANY_VALUE(job_id) AS sample_job_id
FROM {table}
WHERE creation_time >= @start_time
  AND creation_time <= @end_time
  AND job_type = 'QUERY'
  AND state = 'DONE'
  AND statement_type != 'SCRIPT'
  AND cache_hit = FALSE
  AND query_info.query_hashes.normalized_literals IS NOT NULL
GROUP BY 1
HAVING execution_count >= @min_count AND total_bytes_billed >= @min_bytes
ORDER BY total_bytes_billed DESC
LIMIT 50"""

    return text, params
