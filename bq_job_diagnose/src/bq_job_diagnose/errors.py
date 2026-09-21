"""bq-job-diagnose 独自の型付きエラー。

`collect/` 層が GCP API とのやり取りで直面する「利用者が次に何をすべきか
判断できる」エラーだけをここに定義する。BigQuery / google-api-core の
生の例外をそのまま伝播させず、意味のある型に変換することで、CLI 側が
`except PermissionFallbackNeeded:` のように分岐できるようにする。
"""

from __future__ import annotations


class BqJobDiagnoseError(Exception):
    """このプロジェクト固有のエラーの基底クラス。"""


class JobNotFound(BqJobDiagnoseError):
    """指定された job_id が保持期間内（180日）の INFORMATION_SCHEMA に見つからなかった。"""


class PermissionFallbackNeeded(BqJobDiagnoseError):
    """`bigquery.jobs.listAll` 権限が無く INFORMATION_SCHEMA にアクセスできない。

    呼び出し側は `JobsApiCollector`（`jobs.get` ベース、権限要件が緩い）への
    フォールバックを検討すべきというシグナル。
    """


class RetentionFallbackNeeded(BqJobDiagnoseError):
    """指定された creation_time が INFORMATION_SCHEMA の保持期間（180日）より古い。

    INFORMATION_SCHEMA では原理的に取得不可能なため、`JobsApiCollector`
    （jobs.get、保持期間の制約が異なる）へのフォールバックが必要というシグナル。
    """


class ScanNotSupported(BqJobDiagnoseError):
    """`JobsApiCollector` は scan / fetch_jobs をサポートしないことを示す。

    scan には INFORMATION_SCHEMA と `bigquery.jobs.listAll` 権限が必須であり、
    jobs.get ベースの経路では原理的に実現できない。
    """
