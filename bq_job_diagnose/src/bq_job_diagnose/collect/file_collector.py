"""`FileCollector` — GCP にアクセスせず、ローカルのフィクスチャ/ダンプ済み
JSON ファイルからジョブ情報を読む Collector 実装。

設計上の制約（重要）:
- このモジュールは `google.cloud` を import してはならない。統合テストや
  `--from-scan`（過去にダンプした scan 結果からのオフライン再診断）で使う。
- 1ファイル = 1ジョブ。ファイル名（拡張子抜き）を job_id 的なキーとして
  `fetch_job` に渡す（実際の `job_id` フィールド値とは別。ディレクトリ内で
  ファイルを探すためのキーであり、フィクスチャ命名（例: `skewed_join.json`）
  と一致させて使う）。
- JSON の形（`jobReference` キーの有無）で INFORMATION_SCHEMA 行か
  REST jobs.get properties かを判定し、対応する normalize 関数へルーティング
  する。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bq_job_diagnose.collect.base import ScanRow
from bq_job_diagnose.collect.sql import RankBy
from bq_job_diagnose.models import Job
from bq_job_diagnose.normalize.from_information_schema import normalize_row
from bq_job_diagnose.normalize.from_sdk import normalize_job


def _is_sdk_job_properties(data: dict[str, Any]) -> bool:
    """`jobReference` キーの有無で REST jobs.get properties かどうかを判定する。

    INFORMATION_SCHEMA 行には `jobReference` という入れ子構造は存在しない
    （`job_id` がトップレベルの snake_case フィールドとして直接ある）ため、
    この判定は両形式を確実に区別できる。
    """
    return "jobReference" in data


class FileCollector:
    """ディレクトリ内の JSON ファイルからジョブ情報を読む。scan/fetch_jobs は未サポート。"""

    def __init__(self, directory: Path, *, region: str) -> None:
        self._directory = Path(directory)
        self._region = region

    def fetch_job(self, job_id: str, *, created_on: date | None = None) -> Job | None:
        """`{directory}/{job_id}.json` を読み、形式を判定して正規化する。

        ファイルが存在しなければ None を返す（`Collector` Protocol と同じ契約）。
        `created_on` は使わない（ローカルファイルには時間窓の概念がない）。
        """
        path = self._directory / f"{job_id}.json"
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        if _is_sdk_job_properties(data):
            return normalize_job(data, location=self._region)
        return normalize_row(data, location=self._region)

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
        raise NotImplementedError(
            "FileCollector は scan をサポートしません "
            "（ローカルファイルには期間スキャン・TopN ランキングの概念がありません）"
        )

    def fetch_jobs(
        self, job_ids: Sequence[str], *, start_time: datetime, end_time: datetime
    ) -> list[Job]:
        """job_id 群それぞれに対して `fetch_job` を呼び、見つかったものだけ返す。"""
        jobs: list[Job] = []
        for job_id in job_ids:
            job = self.fetch_job(job_id)
            if job is not None:
                jobs.append(job)
        return jobs
