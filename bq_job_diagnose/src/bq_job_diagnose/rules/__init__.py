"""診断ルールのレジストリ（フレームワークのみ、実ルールは含まない）。

設計上の制約（重要・Phase 5 で証明された分離を守る）:
- このパッケージ（`rules/` 以下すべて）は `collect/` を import してはならない。
  ルール関数のシグネチャは `(Job, Thresholds) -> Iterable[Finding]` のみであり、
  ジョブがどのデータソース（INFORMATION_SCHEMA / Jobs API）由来かをルールが
  知る手段を持たない。この制約は `tests/test_rule_registry.py` の
  AST 解析テストで機械的に検証している。
- 同じ理由で `google`（google-cloud-bigquery 等）も import してはならない。
  実際の I/O は `collect/` の責務であり、`rules/` は純粋関数の集まりである。

レジストリの状態管理について:
テストの順序非依存性を保つため、レジストリはグローバル1個に固定しない。
`Registry` クラスをテスト側で明示的に生成し、`@rule(..., registry=...)` /
`run_rules(..., registry=...)` の両方に渡すことで、各テストが完全に独立した
レジストリを使えるようにする（モジュールグローバルを書き換えて後片付けする
方式は、テストの実行順序や並列実行に弱いため採らない）。
本番コードでは `registry` を省略すればモジュールグローバルな `_REGISTRY`
（`default_registry()` で取得可能）が暗黙に使われる。
"""

from __future__ import annotations

import fnmatch
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bq_job_diagnose.models import Finding, Job, SkippedRule

if TYPE_CHECKING:
    from bq_job_diagnose.config import Thresholds

# ルール関数の型。Job と Thresholds のみを受け取り、Finding の iterable を返す。
# None を返す実装（return を書き忘れた等）も許容し、run_rules 側で空扱いにする。
RuleFn = Callable[["Job", "Thresholds"], "Iterable[Finding] | None"]


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """登録された1ルールのメタデータ。"""

    rule_id: str
    fn: RuleFn
    requires_plan: bool = True
    requires_timeline: bool = False


class Registry:
    """ルールを rule_id で管理するレジストリ。"""

    def __init__(self) -> None:
        self._rules: dict[str, RuleSpec] = {}

    def register(self, spec: RuleSpec) -> None:
        """ルールを登録する。同じ rule_id が既に登録済みなら ValueError。"""
        if spec.rule_id in self._rules:
            raise ValueError(
                f"ルール ID が重複しています: {spec.rule_id!r} "
                f"（同じ rule_id を持つルールが既に登録されています。コピペミスを確認してください）"
            )
        self._rules[spec.rule_id] = spec

    def get(self, rule_id: str) -> RuleSpec:
        return self._rules[rule_id]

    def rule_ids(self) -> list[str]:
        return list(self._rules.keys())

    def specs_sorted(self) -> list[RuleSpec]:
        """rule_id の昇順でソートされたルール一覧。

        report の出力を安定させ golden テストがフレークしないようにするため、
        run_rules は常にこの順序でルールを実行する。
        """
        return [self._rules[rule_id] for rule_id in sorted(self._rules)]


# 本番コードから利用するモジュールグローバルなレジストリ。
_REGISTRY = Registry()


def default_registry() -> Registry:
    """モジュールグローバルなレジストリを返す。"""
    return _REGISTRY


def rule(
    rule_id: str,
    *,
    requires_plan: bool = True,
    requires_timeline: bool = False,
    registry: Registry | None = None,
) -> Callable[[RuleFn], RuleFn]:
    """ルール関数を登録するデコレータ。

    デコレートされた関数自体はそのまま（未加工で）返すため、
    ユニットテストからは登録の有無に関わらず直接呼び出せる。

    `registry` を省略した場合はモジュールグローバルなレジストリに登録される。
    テストでは独立したレジストリを明示的に渡すこと（`Registry()` で生成）。
    """
    target_registry = registry if registry is not None else _REGISTRY

    def decorator(fn: RuleFn) -> RuleFn:
        spec = RuleSpec(
            rule_id=rule_id,
            fn=fn,
            requires_plan=requires_plan,
            requires_timeline=requires_timeline,
        )
        target_registry.register(spec)
        return fn

    return decorator


def _precondition_skip_reason(spec: RuleSpec, job: Job) -> str | None:
    """前提条件を満たさない理由の説明文を返す。満たしていれば None。"""
    if spec.requires_plan and not job.has_plan:
        return f"プランが利用できません ({job.plan_availability.value})"
    if spec.requires_timeline and not job.timeline:
        return "タイムラインが利用できません (timeline が空です)"
    return None


def run_rules(
    job: Job,
    thresholds: Thresholds,
    *,
    enabled: set[str] | None = None,
    registry: Registry | None = None,
) -> tuple[list[Finding], list[SkippedRule]]:
    """登録済みルールを rule_id の昇順で実行し、Finding と SkippedRule を返す。

    - `enabled` が None なら全ルールを実行する。
      fnmatch パターンの集合が渡された場合、いずれかのパターンに一致する
      rule_id のルールのみを実行する。一致しなかったルールはユーザーによる
      意図的な無効化とみなし、SkippedRule を生成しない（前提条件スキューと
      区別するため）。
    - `requires_plan` / `requires_timeline` を満たさないルールは呼び出されず、
      具体的な理由を持つ SkippedRule を生成する。
    - ルールが例外を送出した場合はそれを捕捉し、例外クラス名とメッセージを
      含む SkippedRule に変換する。他のルールの実行は継続する。
    - ルールが None を返した場合は Finding 無しとして扱う。
    """
    target_registry = registry if registry is not None else _REGISTRY

    findings: list[Finding] = []
    skipped: list[SkippedRule] = []

    for spec in target_registry.specs_sorted():
        if enabled is not None and not any(
            fnmatch.fnmatch(spec.rule_id, pattern) for pattern in enabled
        ):
            continue

        skip_reason = _precondition_skip_reason(spec, job)
        if skip_reason is not None:
            skipped.append(SkippedRule(rule_id=spec.rule_id, reason=skip_reason))
            continue

        try:
            result = spec.fn(job, thresholds)
        except Exception as exc:  # noqa: BLE001 - 意図的に全例外を捕捉し隔離する
            reason = f"ルール実行中に例外が発生しました: {type(exc).__name__}: {exc}"
            skipped.append(SkippedRule(rule_id=spec.rule_id, reason=reason))
            continue

        if result is None:
            continue
        findings.extend(result)

    return findings, skipped
