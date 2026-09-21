"""閾値設定（thresholds）のロードと属性アクセス可能な表現。

`default_thresholds.yaml`（パッケージ同梱）をベースに、ユーザー指定の YAML を
ディープマージして `Thresholds` を構築する。未知のキーはタイポとみなし
`ValueError` を送出する（サイレントに無視しない）。

`config_digest()` はマージ後の設定を正規化して sha256 したダイジェストを返し、
診断結果（Diagnosis.config_digest）の再現性確認に使う。
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class GlobalThresholds:
    min_stage_duration_ms: int
    min_job_elapsed_ms: int


@dataclass(frozen=True, slots=True)
class SkewThresholds:
    ratio_warning: float
    ratio_critical: float
    min_compute_ms_max: int
    min_compute_share_of_stage: float


@dataclass(frozen=True, slots=True)
class ShuffleThresholds:
    spill_always_advisory: bool
    spill_bytes_notable: int
    output_bytes_warning: int


@dataclass(frozen=True, slots=True)
class FilterThresholds:
    efficiency_critical: float
    efficiency_warning: float
    min_records_read: int


@dataclass(frozen=True, slots=True)
class SlotThresholds:
    runnable_units_threshold: int
    consecutive_samples: int
    max_completed_growth_ratio: float
    wait_share_warning: float
    wait_share_critical: float


@dataclass(frozen=True, slots=True)
class JoinThresholds:
    broadcast_input_bytes_warning: int
    cardinality_explosion_ratio: float
    min_output_records: int


@dataclass(frozen=True, slots=True)
class PricingThresholds:
    as_of: str
    currency: str
    on_demand_price_per_tib: float
    editions_price_per_slot_hour: Mapping[str, float]
    default_edition_for_estimate: str


@dataclass(frozen=True, slots=True)
class CostThresholds:
    on_demand_amount_warning: float
    on_demand_amount_critical: float
    editions_amount_warning: float
    editions_amount_critical: float
    model_mismatch_savings_ratio: float
    billed_over_processed_ratio: float
    min_bytes_billed_for_ratio: int
    repeated_query_min_count: int
    repeated_query_total_amount: float


@dataclass(frozen=True, slots=True)
class PlanShapeThresholds:
    repartition_min_stages: int
    coalesce_min_stages: int


@dataclass(frozen=True, slots=True)
class ScanThresholds:
    default_top_n: int
    default_lookback_days: int
    default_rank_by: str


@dataclass(frozen=True, slots=True)
class Thresholds:
    """全閾値設定への属性アクセスを提供するトップレベルの入れ物。

    `global` は Python の予約語のため、属性名は `global_` とする
    （YAML 上のキー名は `global` のまま）。
    """

    version: int
    global_: GlobalThresholds
    skew: SkewThresholds
    shuffle: ShuffleThresholds
    filter: FilterThresholds
    slot: SlotThresholds
    join: JoinThresholds
    pricing: PricingThresholds
    cost: CostThresholds
    plan_shape: PlanShapeThresholds
    scan: ScanThresholds


# YAML のトップレベルキー名 -> (Thresholds の属性名, セクション dataclass 型)
_SECTIONS: dict[str, tuple[str, type]] = {
    "global": ("global_", GlobalThresholds),
    "skew": ("skew", SkewThresholds),
    "shuffle": ("shuffle", ShuffleThresholds),
    "filter": ("filter", FilterThresholds),
    "slot": ("slot", SlotThresholds),
    "join": ("join", JoinThresholds),
    "pricing": ("pricing", PricingThresholds),
    "cost": ("cost", CostThresholds),
    "plan_shape": ("plan_shape", PlanShapeThresholds),
    "scan": ("scan", ScanThresholds),
}


def _load_default_raw() -> dict[str, Any]:
    """パッケージ同梱の default_thresholds.yaml を dict として読み込む。"""
    ref = importlib.resources.files("bq_job_diagnose").joinpath("default_thresholds.yaml")
    with importlib.resources.as_file(ref) as path:
        text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("default_thresholds.yaml のトップレベルは mapping である必要があります")
    return data


def _deep_merge(
    base: Mapping[str, Any], override: Mapping[str, Any], *, path: str = ""
) -> dict[str, Any]:
    """override を base にディープマージする。

    override に base（=正しいスキーマ）に存在しないキーがあれば ValueError。
    ネストされた dict 同士は再帰的にマージし、それ以外（スカラーやリスト）は
    override の値で置き換える。
    """
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        key_path = f"{path}.{key}" if path else str(key)
        if key not in base:
            raise ValueError(f"未知の設定キーです: {key_path}")
        base_value = base[key]
        if isinstance(base_value, dict) and isinstance(value, dict):
            result[key] = _deep_merge(base_value, value, path=key_path)
        elif isinstance(base_value, dict) and not isinstance(value, dict):
            raise ValueError(
                f"設定キー {key_path} は mapping である必要がありますが、"
                f"{type(value).__name__} が指定されました"
            )
        else:
            result[key] = value
    return result


def _build_thresholds(data: dict[str, Any]) -> Thresholds:
    version = data.get("version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"設定ファイルの version が不一致です: 期待値={SCHEMA_VERSION}, 実際={version!r}"
        )

    section_kwargs: dict[str, Any] = {"version": version}
    for yaml_key, (attr_name, section_cls) in _SECTIONS.items():
        section_data = data[yaml_key]
        section_kwargs[attr_name] = section_cls(**section_data)

    return Thresholds(**section_kwargs)


def load_thresholds(path: Path | None = None) -> Thresholds:
    """閾値設定をロードする。

    パッケージ同梱の default_thresholds.yaml をベースとし、`path` が
    指定されていればその YAML をディープマージして上書きする
    （指定されたキーのみが上書きされ、兄弟キーはデフォルトのまま残る）。

    未知のキー（タイポ等）や version 不一致は ValueError を送出する。
    """
    default_raw = _load_default_raw()

    if path is None:
        merged = default_raw
    else:
        user_text = Path(path).read_text(encoding="utf-8")
        user_raw = yaml.safe_load(user_text)
        if user_raw is None:
            user_raw = {}
        if not isinstance(user_raw, dict):
            raise ValueError(f"{path} のトップレベルは mapping である必要があります")
        merged = _deep_merge(default_raw, user_raw)

    return _build_thresholds(merged)


def _to_plain(obj: Any) -> Any:
    """dataclass インスタンスを再帰的にプレーンな dict/list/scalar に変換する。"""
    if hasattr(obj, "__dataclass_fields__"):
        return {
            f: _to_plain(getattr(obj, f))
            for f in obj.__dataclass_fields__
        }
    if isinstance(obj, Mapping):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def config_digest(thresholds: Thresholds) -> str:
    """マージ後の設定内容から再現性確認用のダイジェスト（sha256 の先頭12桁）を計算する。"""
    plain = _to_plain(thresholds)
    canonical = json.dumps(plain, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:12]
