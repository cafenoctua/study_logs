"""診断結果を JSON レポート（Skill との契約）に変換する。

設計上の制約（重要）:
- このモジュールが返す dict は Skill（LLM）が読む契約そのものである。
  スキーマを崩す変更（キーの削除・意味変更）は SCHEMA_VERSION を上げること。
- `models` / `cost` / `config` / `rules` にのみ依存する。`google` を import しない。
- `datetime` は ISO8601 文字列、`StrEnum` は `.value`、`tuple` は `list` に
  変換する。`TableRef` は `str(TableRef)`（"project.dataset.table"）の
  文字列表現に変換する（構造化した dict ではなく文字列を採用した理由:
  レポートの主要な消費者である Skill は表示にしか使わず、フィールドの
  組み合わせ照合が必要になる場面が無いため、単純さを優先した）。
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from bq_job_diagnose.models import Job, SkippedRule, Source, TableRef

# ルール実行前に全ルールモジュールを import し、`@rule` デコレータによる
# default_registry() への登録を発火させる（各モジュールは import されて
# 初めて登録される設計。tests/test_rules_registration*.py と同じパターン）。
# モジュールオブジェクト自体をこのリストで「使う」ことで、リンターに
# 未使用importと判定されないようにする。
from bq_job_diagnose.rules import (
    cost as _rules_cost,
)
from bq_job_diagnose.rules import (
    filter_efficiency as _rules_filter_efficiency,
)
from bq_job_diagnose.rules import (
    job_status as _rules_job_status,
)
from bq_job_diagnose.rules import (
    joins as _rules_joins,
)
from bq_job_diagnose.rules import (
    plan_shape as _rules_plan_shape,
)
from bq_job_diagnose.rules import (
    skew as _rules_skew,
)
from bq_job_diagnose.rules import (
    slot_starvation as _rules_slot_starvation,
)
from bq_job_diagnose.rules import (
    spill as _rules_spill,
)

_ALL_RULE_MODULES = (
    _rules_cost,
    _rules_filter_efficiency,
    _rules_job_status,
    _rules_joins,
    _rules_plan_shape,
    _rules_skew,
    _rules_slot_starvation,
    _rules_spill,
)

if TYPE_CHECKING:
    from bq_job_diagnose.cost import CostComparison
    from bq_job_diagnose.models import Diagnosis

SCHEMA_VERSION = "1"

# Severity の重要度順（critical が最優先）。report のソート順にのみ使う。
_SEVERITY_ORDER = {"critical": 0, "warning": 1, "advisory": 2, "info": 3}


def _serialize_value(value: Any) -> Any:
    """任意の値を `json.dumps` でそのまま扱える形へ再帰的に変換する。"""
    if isinstance(value, TableRef):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _serialize_value(getattr(value, f.name)) for f in fields(value)}
    return value


def _job_to_dict(job: Job) -> dict[str, Any]:
    """`Job` の全フィールドを JSON 互換な dict に変換する。"""
    return {f.name: _serialize_value(getattr(job, f.name)) for f in fields(job)}


def _cost_to_dict(cost: CostComparison) -> dict[str, Any]:
    return {
        "actual_model": cost.actual_model.value,
        "on_demand": _serialize_value(cost.on_demand),
        "editions": _serialize_value(cost.editions),
        "cheaper_model": cost.cheaper_model.value if cost.cheaper_model is not None else None,
        "savings_ratio": cost.savings_ratio,
    }


def _finding_sort_key(finding_dict: dict[str, Any]) -> tuple[int, str]:
    return (_SEVERITY_ORDER.get(finding_dict["severity"], 99), finding_dict["rule_id"])


def append_starvation_skip_if_needed(
    job: Job,
    findings: list[Any],
    skipped_rules: list[SkippedRule],
) -> list[SkippedRule]:
    """`slot.starvation` の「未評価」を正しく表現するための後処理。

    `slot.starvation` ルールは以下の2状況のどちらでも Finding を生成しない:
      (a) 健全（starvation が実際に発生していない）
      (b) `estimated_runnable_units` が全サンプルで None
          （jobs.get 経路など、このデータソースが構造的に取得できない）

    ルール関数自体は SkippedRule を生成する手段を持たない（run_rules の
    前提条件チェックのみが SkippedRule を生成できる設計のため）。
    そのため、レポート生成時にこの後処理でギャップを埋める:
    `job.source is Source.JOBS_API` である、または全 TimelineSample の
    `estimated_runnable_units` が None であり、かつ `slot.starvation` の
    Finding が1件も無い場合に限り、SkippedRule を追加する。

    既に `slot.starvation` の Finding または SkippedRule が存在する場合は
    何もしない（二重追加を防ぐ）。

    引数の `findings` / `skipped_rules` は変更しない（新しい list を返す）。
    """
    has_starvation_finding = any(
        getattr(f, "rule_id", None) == "slot.starvation" for f in findings
    )
    if has_starvation_finding:
        return list(skipped_rules)

    already_skipped = any(s.rule_id == "slot.starvation" for s in skipped_rules)
    if already_skipped:
        return list(skipped_rules)

    all_none = not any(
        sample.estimated_runnable_units is not None for sample in job.timeline
    )
    structurally_unavailable = job.source is Source.JOBS_API or all_none

    if not structurally_unavailable:
        return list(skipped_rules)

    reason = (
        "estimated_runnable_units を取得できないデータソースのため "
        "slot.starvation は評価できません"
        + (
            " (source=jobs_api)"
            if job.source is Source.JOBS_API
            else " (全タイムラインサンプルで estimated_runnable_units が None)"
        )
    )
    return [*skipped_rules, SkippedRule(rule_id="slot.starvation", reason=reason)]


def _diagnosis_to_job_entry(diagnosis: Diagnosis, thresholds: Any) -> dict[str, Any]:
    from bq_job_diagnose.cost import compare

    job = diagnosis.job
    cost = compare(job, thresholds)

    skipped_rules = append_starvation_skip_if_needed(
        job, list(diagnosis.findings), list(diagnosis.skipped_rules)
    )

    findings_list = [_serialize_value(f) for f in diagnosis.findings]
    findings_list.sort(key=_finding_sort_key)

    return {
        "job": _job_to_dict(job),
        "cost": _cost_to_dict(cost),
        "findings": findings_list,
        "skipped_rules": [_serialize_value(s) for s in skipped_rules],
    }


def build_json_report(
    *,
    mode: Literal["job", "scan", "drill"],
    diagnoses: list[Diagnosis],
    scan_summary: dict[str, Any] | None = None,
    generated_at: datetime,
    config_digest: str,
    thresholds: Any | None = None,
) -> dict[str, Any]:
    """診断結果一式から Skill 契約用の JSON レポート dict を組み立てる。

    `thresholds` を省略した場合はデフォルト設定（`load_thresholds()`）を使う。
    ジョブごとの cost 試算に必要。
    """
    if thresholds is None:
        from bq_job_diagnose.config import load_thresholds

        thresholds = load_thresholds()

    jobs = [_diagnosis_to_job_entry(diag, thresholds) for diag in diagnoses]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "config_digest": config_digest,
        "mode": mode,
        "jobs": jobs,
        "scan_summary": scan_summary,
    }
