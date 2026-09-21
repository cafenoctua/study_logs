"""BigQuery ジョブ診断のためのドメインモデル。

設計上の制約（重要）:
- このモジュールは stdlib のみに依存する。外部ライブラリを import しない。
  `rules/` は `models.Job` のみを知っていればよく、`collect/`（BigQuery API 呼び出し）
  を import してはならない。この分離を守るため、models 自体も薄く保つ。
- `Stage` には比率フィールド（compute_ratio_avg 等）を持たせない。
  BigQuery の INFORMATION_SCHEMA / Jobs API が返す比率は「クエリ全体で最も遅かった
  ワーカーの時間」を分母に正規化されており、ステージ内の比較には使えない
  （誤ってスキュー検出に使うと必ず誤診断になる）。スキュー検出は
  `wait_ms_*` / `compute_ms_*` などのミリ秒フィールドから計算した比率
  （例: `Stage.compute_skew_ratio`）を使うこと。
- `None` は「このデータソースでは取得できない／公開されていない」ことを表す。
  `0` は「取得できたが値がゼロだった」ことを表す。この2つを混同しない。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Literal

# labels のデフォルト値として使う空の read-only mapping。
# frozen + slots な dataclass では mutable なデフォルト値を持てないため、
# モジュールレベルの定数として共有する。
_EMPTY_MAPPING: Mapping[str, str] = MappingProxyType({})


class Source(StrEnum):
    """ジョブ情報の取得元。"""

    INFORMATION_SCHEMA = "information_schema"
    JOBS_API = "jobs_api"


class PlanAvailability(StrEnum):
    """クエリプラン（ステージ情報）が利用可能かどうかの状態。"""

    AVAILABLE = "available"
    CACHE_HIT = "cache_hit"  # cache_hit=true → プランなし（正常、エラーではない）
    DRY_RUN = "dry_run"
    RESTRICTED = "restricted"  # 行レベルアクセスポリシーで job_stages が空
    NOT_AVAILABLE = "not_available"


class Severity(StrEnum):
    """診断結果（Finding）の重要度。"""

    CRITICAL = "critical"
    WARNING = "warning"
    ADVISORY = "advisory"  # spill のような非決定的シグナル専用
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Step:
    """クエリプランのステージ内に現れる実行ステップ。"""

    kind: str
    substeps: tuple[str, ...]
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class Stage:
    """クエリプランの1ステージ。

    注意: 比率フィールド（compute_ratio_avg 等）は意図的に持たせていない。
    BigQuery が返す比率はクエリ全体で最も遅いワーカーの時間を分母に正規化されており、
    ステージ単体でのスキュー検出には使えない。スキューは `compute_skew_ratio` など
    ミリ秒フィールドから算出したプロパティで判定すること。
    """

    id: int
    name: str
    status: str | None
    start_ms: int | None
    end_ms: int | None
    input_stage_ids: tuple[int, ...]
    wait_ms_avg: int | None
    wait_ms_max: int | None
    read_ms_avg: int | None
    read_ms_max: int | None
    compute_ms_avg: int | None
    compute_ms_max: int | None
    write_ms_avg: int | None
    write_ms_max: int | None
    shuffle_output_bytes: int | None
    shuffle_output_bytes_spilled: int | None
    records_read: int | None
    records_written: int | None
    parallel_inputs: int | None
    completed_parallel_inputs: int | None
    slot_ms: int | None
    compute_mode: str | None
    steps: tuple[Step, ...]

    @property
    def duration_ms(self) -> int | None:
        """ステージの所要時間（ミリ秒）。start_ms / end_ms のいずれかが None なら None。"""
        if self.start_ms is None or self.end_ms is None:
            return None
        return self.end_ms - self.start_ms

    @property
    def compute_skew_ratio(self) -> float | None:
        """compute_ms_max / compute_ms_avg。

        ステージ内のワーカー間スキューを検出するための比率。
        avg が None、max が None、または avg が 0 以下（正規化不能）の場合は None。
        """
        if self.compute_ms_avg is None or self.compute_ms_max is None:
            return None
        if self.compute_ms_avg <= 0:
            return None
        return self.compute_ms_max / self.compute_ms_avg


@dataclass(frozen=True, slots=True)
class TimelineSample:
    """ジョブのタイムライン（進捗）サンプル1点分。"""

    elapsed_ms: int
    total_slot_ms: int | None
    pending_units: int | None
    completed_units: int | None
    active_units: int | None
    estimated_runnable_units: int | None


@dataclass(frozen=True, slots=True)
class TableRef:
    """テーブルの完全修飾参照。"""

    project_id: str
    dataset_id: str
    table_id: str

    def __str__(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"


@dataclass(frozen=True, slots=True)
class Job:
    """BigQuery ジョブ1件分の情報（診断対象のルート）。

    `rules/` はこの `Job`（および `Stage` / `TimelineSample` 等の下位モデル）のみに
    依存する。`collect/`（実際の BigQuery API 呼び出し）を import してはならない。
    """

    source: Source
    job_id: str
    project_id: str
    location: str
    parent_job_id: str | None
    user_email: str | None
    creation_time: datetime
    start_time: datetime | None
    end_time: datetime | None
    job_type: str
    statement_type: str | None
    priority: str | None
    state: str
    error_result: dict | None
    query: str | None
    cache_hit: bool | None
    total_bytes_processed: int | None
    total_bytes_billed: int | None
    total_slot_ms: int | None
    referenced_tables: tuple[TableRef, ...]
    destination_table: TableRef | None
    labels: Mapping[str, str] = field(default_factory=lambda: _EMPTY_MAPPING)
    reservation_id: str | None = None
    edition: str | None = None
    resource_warning: str | None = None
    normalized_literals_hash: str | None = None
    performance_insights: dict | None = None
    dml_statistics: dict | None = None
    plan_availability: PlanAvailability = PlanAvailability.NOT_AVAILABLE
    stages: tuple[Stage, ...] = ()
    timeline: tuple[TimelineSample, ...] = ()

    @property
    def is_script_parent(self) -> bool:
        """このジョブが SCRIPT 文（親ジョブ）かどうか。"""
        return self.statement_type == "SCRIPT"

    @property
    def elapsed_ms(self) -> int | None:
        """start_time から end_time までの経過時間（ミリ秒）。どちらかが None なら None。"""
        if self.start_time is None or self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() * 1000)

    @property
    def has_plan(self) -> bool:
        """クエリプラン（ステージ情報）が実際に利用可能かどうか。

        plan_availability が AVAILABLE であり、かつ stages が空でない場合のみ True。
        """
        return self.plan_availability is PlanAvailability.AVAILABLE and bool(self.stages)


@dataclass(frozen=True, slots=True)
class Evidence:
    """Finding を裏付ける具体的な数値・根拠。"""

    label: str
    value: float | int | str
    unit: str | None = None
    stage_id: int | None = None
    threshold: float | int | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    """診断ルールが検出した1件の所見。"""

    rule_id: str
    title: str
    severity: Severity
    summary: str
    evidence: tuple[Evidence, ...]
    stage_ids: tuple[int, ...] = ()
    doc_url: str | None = None
    doc_quote: str | None = None
    confidence: Literal["high", "medium", "low"] = "high"


@dataclass(frozen=True, slots=True)
class SkippedRule:
    """データ不足等の理由で実行されなかったルール。"""

    rule_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """1ジョブに対する診断結果全体。"""

    job: Job
    findings: tuple[Finding, ...]
    skipped_rules: tuple[SkippedRule, ...]
    generated_at: datetime
    config_digest: str
