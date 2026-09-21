"""`InformationSchemaCollector` — BigQuery INFORMATION_SCHEMA.JOBS_BY_PROJECT を
実際に叩く Collector 実装。

設計上の制約（重要）:
- このプロジェクトで `google.cloud` の import が許可される数少ないモジュール
  の1つ（もう1つは `jobs_api.py`）。`rules/` はこのモジュールを一切知らない。
- `bigquery.Client` はコンストラクタでの DI（依存性注入）で受け取る。
  このモジュール自身はクライアントを生成しない。テストでは fake client を
  渡せるようにするため。
- `collect/sql.py` の `ScalarParam` / `ArrayParam`（ローカル dataclass）を
  実 SDK の `bigquery.ScalarQueryParameter` / `bigquery.ArrayQueryParameter`
  に変換する。
- REVIEW_GUIDE.md 2.3 の方針により、`bigquery.Client` をモックして「呼ばれた
  こと」を検証するテストはこのプロジェクトでは書かない。そのためロジックの
  大半（時間窓拡大・エラー分類）を純粋関数へ切り出し、クライアント無しで
  直接テストできるようにしている。
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from google.api_core import exceptions as gcloud_exceptions
from google.cloud import bigquery

from bq_job_diagnose.collect.base import ScanRow
from bq_job_diagnose.collect.sql import (
    ArrayParam,
    RankBy,
    ScalarParam,
    build_job_sql,
    build_scan_sql,
)
from bq_job_diagnose.errors import (
    BqJobDiagnoseError,
    JobNotFound,
    PermissionFallbackNeeded,
    RetentionFallbackNeeded,
)
from bq_job_diagnose.models import Job
from bq_job_diagnose.normalize.from_information_schema import normalize_row
from scripts.anonymize_fixture import anonymize_row

# INFORMATION_SCHEMA.JOBS_BY_PROJECT の保持期間（日数）。これより古い
# creation_time は原理的に取得不能。
_RETENTION_DAYS = 180

# 時間窓の段階的拡大（created_on が指定されなかった場合に使う）。
_WIDEN_STEPS_DAYS = (7, 30, _RETENTION_DAYS)

# Forbidden のメッセージからパーミッション種別を判定するための正規表現。
# 大文字小文字を区別せず「bigquery.jobs.listAll」という文言を探す。
_JOBS_LIST_ALL_RE = re.compile(r"bigquery\.jobs\.listAll", re.IGNORECASE)


# ---------------------------------------------------------------------------
# パラメータ変換（純粋関数）
# ---------------------------------------------------------------------------


def _translate_param(param: ScalarParam | ArrayParam) -> Any:
    """`collect/sql.py` のローカル param dataclass を実 SDK オブジェクトに変換する。"""
    if isinstance(param, ScalarParam):
        return bigquery.ScalarQueryParameter(param.name, param.type_, param.value)
    if isinstance(param, ArrayParam):
        return bigquery.ArrayQueryParameter(param.name, param.element_type, list(param.values))
    raise TypeError(f"未知のパラメータ型です: {type(param)!r}")


def _translate_params(params: Sequence[ScalarParam | ArrayParam]) -> list[Any]:
    return [_translate_param(p) for p in params]


# ---------------------------------------------------------------------------
# 時間窓の拡大ロジック（純粋関数）
# ---------------------------------------------------------------------------


def _widen_windows(
    created_on: date | None, now: datetime
) -> list[tuple[datetime, datetime]]:
    """`fetch_job` が試行する時間窓の一覧を返す。

    - `created_on` が与えられた場合: その日 ±1日の単一ウィンドウのみ
      （ユーザーがジョブの実行日をおおよそ知っている場合、無駄に広い
      スキャンを避けられる）。
    - `created_on` が None の場合: 7日 -> 30日 -> 180日（INFORMATION_SCHEMA
      の保持期間上限）と段階的に広げていくウィンドウ列を返す。狭い窓から
      試すことで、直近のジョブに対するクエリコストを抑える。
    """
    if created_on is not None:
        base = datetime(created_on.year, created_on.month, created_on.day, tzinfo=now.tzinfo)
        lower = base - timedelta(days=1)
        upper = base + timedelta(days=1)
        return [(lower, upper)]

    return [(now - timedelta(days=days), now) for days in _WIDEN_STEPS_DAYS]


# ---------------------------------------------------------------------------
# エラー分類ロジック（純粋関数）
# ---------------------------------------------------------------------------


def _classify_forbidden(message: str) -> type[BqJobDiagnoseError] | None:
    """Forbidden 例外のメッセージから、既知のパーミッション不足パターンかを判定する。

    `bigquery.jobs.listAll` への言及があれば `PermissionFallbackNeeded` を返す。
    それ以外（テーブル単位の権限拒否等、INFORMATION_SCHEMA アクセスとは無関係な
    Forbidden）は None を返し、呼び出し側で元の例外をそのまま伝播させる。
    """
    if _JOBS_LIST_ALL_RE.search(message):
        return PermissionFallbackNeeded
    return None


# ---------------------------------------------------------------------------
# datetime -> ISO8601 のダンプ用シリアライザ
# ---------------------------------------------------------------------------


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"JSON化できない型です: {type(obj)!r}")


# ---------------------------------------------------------------------------
# Collector 本体
# ---------------------------------------------------------------------------


class InformationSchemaCollector:
    """INFORMATION_SCHEMA.JOBS_BY_PROJECT 経由でジョブ情報を取得する。

    `client` は呼び出し側が構築して渡す（DI）。このクラス自身は
    `bigquery.Client()` を生成しない。
    """

    def __init__(
        self,
        client: bigquery.Client,
        *,
        project_id: str,
        region: str,
        dump_raw_dir: Path | None = None,
        on_widen: Callable[[int], None] | None = None,
    ) -> None:
        self._client = client
        self._project_id = project_id
        self._region = region
        self._dump_raw_dir = dump_raw_dir
        # 時間窓を広げるたびに呼ばれるコールバック（引数は widen 後の日数）。
        # 未指定ならデフォルトで stderr にメッセージを出す。
        self._on_widen = on_widen or self._default_on_widen

    @staticmethod
    def _default_on_widen(days: int) -> None:
        import sys

        print(f"[bq-job-diagnose] 見つからないため検索期間を {days} 日に拡大します...", file=sys.stderr)

    # -- 内部ヘルパー ---------------------------------------------------

    def _run_query(self, sql: str, params: list) -> list[dict[str, Any]]:
        """SQL を実行し、行を `dict` のリストとして返す。

        Forbidden は `_classify_forbidden` で分類し、既知パターンなら
        型付きエラーへ変換して送出する。未知パターンはそのまま伝播させる。
        """
        job_config = bigquery.QueryJobConfig(query_parameters=_translate_params(params))
        try:
            result = self._client.query(sql, job_config=job_config).result()
        except gcloud_exceptions.Forbidden as exc:
            error_type = _classify_forbidden(str(exc))
            if error_type is not None:
                raise error_type(str(exc)) from exc
            raise
        rows = [dict(row.items()) for row in result]
        if self._dump_raw_dir is not None:
            self._dump_rows(rows)
        return rows

    def _dump_rows(self, rows: list[dict[str, Any]]) -> None:
        """取得した行を匿名化した上で JSON として `dump_raw_dir` に書き出す。

        `--dump-raw`（隠しオプション）用。フィクスチャ採取に使うため、
        書き出し時点で必ず匿名化する（生データを誤ってリポジトリに
        コミットしてしまう事故を防ぐ）。
        """
        self._dump_raw_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            anonymized = anonymize_row(row)
            job_id = row.get("job_id", "unknown")
            out_path = self._dump_raw_dir / f"{job_id}.json"
            out_path.write_text(
                json.dumps(anonymized, default=_json_default, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # -- Collector プロトコル実装 ----------------------------------------

    def fetch_job(self, job_id: str, *, created_on: date | None = None) -> Job | None:
        """単一ジョブを取得する。

        `created_on` があればその日 ±1日のみを試す。無ければ 7d -> 30d ->
        180d と段階的に窓を広げ、見つかるたびに `_on_widen` で通知する。
        180d まで見つからなければ None を返す（呼び出し側が `JobNotFound`
        として扱うかは呼び出し側の判断に委ねる。ここでは None を返す方が
        `Collector` Protocol のシグネチャと整合する）。
        """
        now = datetime.now(tz=self._client_utcnow_tz())
        windows = _widen_windows(created_on, now)

        for i, (lower, upper) in enumerate(windows):
            if i > 0:
                days = _WIDEN_STEPS_DAYS[i]
                self._on_widen(days)

            sql, params = build_job_sql(
                project_id=self._project_id,
                region=self._region,
                job_id=job_id,
                creation_time_lower=lower,
                creation_time_upper=upper,
            )
            rows = self._run_query(sql, params)
            if rows:
                return normalize_row(rows[0], location=self._region)

        # 180日まで探して見つからなかった。
        if created_on is not None:
            cutoff = now - timedelta(days=_RETENTION_DAYS)
            created_on_dt = datetime(
                created_on.year, created_on.month, created_on.day, tzinfo=now.tzinfo
            )
            if created_on_dt < cutoff:
                raise RetentionFallbackNeeded(
                    f"指定された creation_time（{created_on}）は "
                    f"INFORMATION_SCHEMA の保持期間（{_RETENTION_DAYS}日）より古いため取得できません"
                )
        raise JobNotFound(f"job_id={job_id!r} は保持期間内（{_RETENTION_DAYS}日）に見つかりませんでした")

    def _client_utcnow_tz(self):
        from datetime import UTC

        return UTC

    def scan(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        top_n: int,
        rank_by: RankBy,
        user_email: str | None = None,
        min_slot_ms: int | None = None,
    ) -> list[ScanRow]:
        """期間内のジョブを rank_by 基準で TopN 抽出し、軽量な `ScanRow` で返す。"""
        sql, params = build_scan_sql(
            project_id=self._project_id,
            region=self._region,
            start_time=start_time,
            end_time=end_time,
            top_n=top_n,
            rank_by=rank_by,
            user_email=user_email,
            min_slot_ms=min_slot_ms,
        )
        rows = self._run_query(sql, params)
        return [_row_to_scan_row(row) for row in rows]

    def fetch_jobs(
        self, job_ids: Sequence[str], *, start_time: datetime, end_time: datetime
    ) -> list[Job]:
        """job_id 群に対してフルの `Job` を一括取得する。"""
        from bq_job_diagnose.collect.sql import build_drill_sql

        sql, params = build_drill_sql(
            project_id=self._project_id,
            region=self._region,
            job_ids=list(job_ids),
            start_time=start_time,
            end_time=end_time,
        )
        rows = self._run_query(sql, params)
        return [normalize_row(row, location=self._region) for row in rows]


def _row_to_scan_row(row: dict[str, Any]) -> ScanRow:
    """`build_scan_sql` / `build_children_sql` の1行を `ScanRow` に変換する。

    INT64 列は BigQuery Python クライアント経由では既に int として届くが、
    念のため明示的に int() を通す（None は None のまま）。
    """

    def _int(v: Any) -> int | None:
        return None if v is None else int(v)

    def _bool(v: Any) -> bool | None:
        return None if v is None else bool(v)

    return ScanRow(
        job_id=row["job_id"],
        project_id=row["project_id"],
        parent_job_id=row.get("parent_job_id"),
        user_email=row.get("user_email"),
        creation_time=row["creation_time"],
        elapsed_ms=_int(row.get("elapsed_ms")),
        total_slot_ms=_int(row.get("total_slot_ms")),
        total_bytes_billed=_int(row.get("total_bytes_billed")),
        cache_hit=_bool(row.get("cache_hit")),
        statement_type=row.get("statement_type"),
        query_head=row.get("query_head"),
        has_error=bool(row.get("has_error")),
        edition=row.get("edition"),
        reservation_id=row.get("reservation_id"),
        resource_warning=row.get("resource_warning"),
        normalized_literals_hash=row.get("normalized_literals_hash"),
        referenced_table_count=_int(row.get("referenced_table_count")),
        state=row["state"],
        priority=row.get("priority"),
        job_type=row["job_type"],
    )
