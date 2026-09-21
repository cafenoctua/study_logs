"""Collector の共通インタフェース（Protocol）と scan モード専用の軽量行 `ScanRow`。

設計上の制約（重要）:
- このモジュールはネットワーク呼び出しを一切行わない。`google.cloud` を
  import してはならない（`Collector` はあくまで構造的な型で、実装は
  `information_schema.py` / `jobs_api.py` / `file_collector.py` が担う）。
- `scan()` は `models.Job` ではなく `ScanRow` を返す。scan は TopN 抽出が
  目的であり、`job_stages` / `timeline` のような重量級フィールドを含む
  フル `Job` を大量に取得するとスキャン自体が高コストになるため
  （`collect/sql.py` の `_SCAN_COLUMNS` と同じ理由）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol

from bq_job_diagnose.models import Job

RankBy = Literal["slot_ms", "bytes_billed", "elapsed"]


@dataclass(frozen=True, slots=True)
class ScanRow:
    """`build_scan_sql` / `build_children_sql` の軽量カラムに対応する1行分。

    `Job` と異なり `stages` / `timeline` / `query`（全文）を持たない。
    """

    job_id: str
    project_id: str
    parent_job_id: str | None
    user_email: str | None
    creation_time: datetime
    elapsed_ms: int | None
    total_slot_ms: int | None
    total_bytes_billed: int | None
    cache_hit: bool | None
    statement_type: str | None
    query_head: str | None
    has_error: bool
    edition: str | None
    reservation_id: str | None
    resource_warning: str | None
    normalized_literals_hash: str | None
    referenced_table_count: int | None
    state: str
    priority: str | None
    job_type: str


class Collector(Protocol):
    """ジョブ情報の取得元（INFORMATION_SCHEMA / jobs.get / ローカルファイル）を
    抽象化する共通インタフェース。

    `rules/` はこの Protocol を知らない（`Job` のみに依存する）。この
    Protocol を実装として使うのは `cli.py`（Phase 11 以降）の責務。
    """

    def fetch_job(self, job_id: str, *, created_on: date | None = None) -> Job | None:
        """単一ジョブを取得する。

        「見つからない」の表し方は実装によって意図的に異なる:

        - GCP を参照する実装（InformationSchemaCollector / JobsApiCollector）は
          `errors.JobNotFound` を送出する。CLI は「ジョブが無い」「権限が無い」
          「保持期限切れ」を別々の終了コードで扱う必要があり、None では理由が
          失われるため。
        - `FileCollector` はフィクスチャを読むだけなので、該当ファイルが無ければ
          単に None を返す（区別すべき理由が存在しない）。

        呼び出し側は両方を扱えるようにすること。
        """
        ...

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
        """期間内のジョブを rank_by 基準で TopN 抽出する。"""
        ...

    def fetch_jobs(
        self, job_ids: Sequence[str], *, start_time: datetime, end_time: datetime
    ) -> list[Job]:
        """job_id 群に対してフルの `Job` を一括取得する。"""
        ...
