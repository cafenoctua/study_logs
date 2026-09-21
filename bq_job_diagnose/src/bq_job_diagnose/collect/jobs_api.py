"""`JobsApiCollector` — `jobs.get`（BigQuery Jobs API / REST）経由でジョブ情報を
取得する Collector 実装。

設計上の制約（重要）:
- このプロジェクトで `google.cloud` の import が許可される数少ないモジュールの
  1つ（もう1つは `information_schema.py`）。
- `client.get_job(job_id, location=...)` は単一ジョブしか取得できない。
  scan（TopN 抽出）や fetch_jobs（複数ジョブ一括取得）は
  INFORMATION_SCHEMA + `bigquery.jobs.listAll` 権限が必須の機能であり、
  jobs.get ベースの経路では原理的に実現できないため、明確なエラーを送出する。
- `client` はコンストラクタで DI する。このクラス自身はクライアントを
  生成しない。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from bq_job_diagnose.collect.base import ScanRow
from bq_job_diagnose.collect.sql import RankBy
from bq_job_diagnose.errors import ScanNotSupported
from bq_job_diagnose.models import Job
from bq_job_diagnose.normalize.from_sdk import normalize_job


class JobsApiCollector:
    """`jobs.get` 経由でジョブ情報を取得する。scan / fetch_jobs はサポートしない。"""

    def __init__(
        self,
        client: bigquery.Client,
        *,
        region: str,
        dump_raw_dir: Path | None = None,
    ) -> None:
        self._client = client
        self._region = region
        self._dump_raw_dir = dump_raw_dir

    def fetch_job(self, job_id: str, *, created_on: date | None = None) -> Job | None:
        """`client.get_job` でジョブを取得し `models.Job` に正規化する。

        `created_on` は jobs.get 経路では使わない（jobs.get は job_id のみで
        一意に取得できるため、時間窓の絞り込みが不要）。Protocol の
        シグネチャに合わせるため引数としては受け取るが無視する。
        """
        job = self._client.get_job(job_id, location=self._region)
        properties = job._properties
        if self._dump_raw_dir is not None:
            self._dump_properties(properties)
        return normalize_job(properties, location=self._region)

    def _dump_properties(self, properties: dict[str, Any]) -> None:
        """取得した job._properties を匿名化した上で JSON として書き出す。"""
        import json

        from bq_job_diagnose.anonymize import anonymize_job_properties

        self._dump_raw_dir.mkdir(parents=True, exist_ok=True)
        anonymized = anonymize_job_properties(properties)
        job_id = properties.get("jobReference", {}).get("jobId", "unknown")
        out_path = self._dump_raw_dir / f"{job_id}.json"
        out_path.write_text(
            json.dumps(anonymized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
        raise ScanNotSupported(
            "JobsApiCollector は scan をサポートしません。"
            "scan には INFORMATION_SCHEMA と bigquery.jobs.listAll 権限が必要です。"
            "InformationSchemaCollector を使用してください。"
        )

    def fetch_jobs(
        self, job_ids: Sequence[str], *, start_time: datetime, end_time: datetime
    ) -> list[Job]:
        raise ScanNotSupported(
            "JobsApiCollector は fetch_jobs（一括取得）をサポートしません。"
            "一括取得には INFORMATION_SCHEMA と bigquery.jobs.listAll 権限が必要です。"
            "InformationSchemaCollector を使用してください。"
        )
