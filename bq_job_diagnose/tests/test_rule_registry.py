"""rules/__init__.py のルールレジストリのテスト。

TDD: このテストを先に書き、失敗することを確認してから rules/__init__.py を実装する。

レジストリはモジュールグローバル（`rules` モジュール内の `_REGISTRY`）だが、
テストの順序依存を避けるため `Registry` を明示的に生成し
`run_rules(..., registry=registry)` に渡す方式をとる（グローバルを暗黙に
書き換えて後片付けする方式は採らない）。デコレータ `@rule(...)` は
デフォルトでモジュールグローバルなレジストリに登録するが、
`@rule(..., registry=registry)` のように明示的なレジストリを渡すこともできる。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bq_job_diagnose.models import Finding, PlanAvailability, Severity
from bq_job_diagnose.rules import Registry, rule, run_rules
from tests.builders import make_job

RULES_DIR = Path(__file__).parent.parent / "src" / "bq_job_diagnose" / "rules"


def _finding(rule_id: str = "dummy.rule") -> Finding:
    return Finding(
        rule_id=rule_id,
        title="dummy",
        severity=Severity.INFO,
        summary="dummy summary",
        evidence=(),
    )


# ---------------------------------------------------------------------------
# 1. 登録とデコレータの透過性
# ---------------------------------------------------------------------------


class TestRuleDecoratorRegistersAndReturnsUnchanged:
    def test_decorated_function_is_directly_callable(self):
        registry = Registry()

        @rule("test.direct_call", registry=registry)
        def my_rule(job, th):
            return [_finding("test.direct_call")]

        job = make_job()
        result = my_rule(job, None)
        assert list(result) == [_finding("test.direct_call")]

    def test_rule_is_registered_in_registry(self):
        registry = Registry()

        @rule("test.registered", registry=registry)
        def my_rule(job, th):
            return []

        assert "test.registered" in registry.rule_ids()


# ---------------------------------------------------------------------------
# 2. 重複 rule_id は ValueError
# ---------------------------------------------------------------------------


class TestDuplicateRuleIdRaises:
    def test_duplicate_id_raises_value_error_naming_the_id(self):
        registry = Registry()

        @rule("test.dup", registry=registry)
        def rule_one(job, th):
            return []

        with pytest.raises(ValueError, match="test.dup"):

            @rule("test.dup", registry=registry)
            def rule_two(job, th):
                return []


# ---------------------------------------------------------------------------
# 3. 決定論的な実行順序（rule_id でソート）
# ---------------------------------------------------------------------------


class TestDeterministicOrder:
    def test_rules_registered_out_of_order_run_sorted_by_id(self):
        registry = Registry()

        @rule("zzz.last", registry=registry)
        def rule_z(job, th):
            return [_finding("zzz.last")]

        @rule("aaa.first", registry=registry)
        def rule_a(job, th):
            return [_finding("aaa.first")]

        @rule("mmm.middle", registry=registry)
        def rule_m(job, th):
            return [_finding("mmm.middle")]

        job = make_job()
        findings, skipped = run_rules(job, None, registry=registry)
        assert [f.rule_id for f in findings] == ["aaa.first", "mmm.middle", "zzz.last"]


# ---------------------------------------------------------------------------
# 4. 前提条件による自動スキップ
# ---------------------------------------------------------------------------


class TestPreconditionSkips:
    def test_requires_plan_skips_when_job_has_no_plan(self):
        registry = Registry()
        called = {"count": 0}

        @rule("test.needs_plan", requires_plan=True, registry=registry)
        def my_rule(job, th):
            called["count"] += 1
            return [_finding("test.needs_plan")]

        job = make_job(plan_availability=PlanAvailability.CACHE_HIT, stages=())
        findings, skipped = run_rules(job, None, registry=registry)

        assert findings == []
        assert called["count"] == 0, "前提条件を満たさないルールの本体は実行されてはならない"
        assert len(skipped) == 1
        assert skipped[0].rule_id == "test.needs_plan"
        assert "cache_hit" in skipped[0].reason
        assert "プラン" in skipped[0].reason

    def test_requires_plan_reason_includes_actual_plan_availability_value(self):
        registry = Registry()

        @rule("test.needs_plan2", requires_plan=True, registry=registry)
        def my_rule(job, th):
            return [_finding("test.needs_plan2")]

        job = make_job(plan_availability=PlanAvailability.RESTRICTED, stages=())
        findings, skipped = run_rules(job, None, registry=registry)
        assert "restricted" in skipped[0].reason

    def test_requires_timeline_skips_when_timeline_empty(self):
        registry = Registry()
        called = {"count": 0}

        @rule("test.needs_timeline", requires_plan=False, requires_timeline=True, registry=registry)
        def my_rule(job, th):
            called["count"] += 1
            return [_finding("test.needs_timeline")]

        job = make_job(timeline=())
        findings, skipped = run_rules(job, None, registry=registry)

        assert findings == []
        assert called["count"] == 0
        assert len(skipped) == 1
        assert skipped[0].rule_id == "test.needs_timeline"
        assert "タイムライン" in skipped[0].reason

    def test_requires_plan_false_runs_even_without_plan(self):
        registry = Registry()

        @rule("test.no_plan_needed", requires_plan=False, registry=registry)
        def my_rule(job, th):
            return [_finding("test.no_plan_needed")]

        job = make_job(plan_availability=PlanAvailability.CACHE_HIT, stages=())
        findings, skipped = run_rules(job, None, registry=registry)
        assert [f.rule_id for f in findings] == ["test.no_plan_needed"]
        assert skipped == []

    def test_default_requires_plan_true_and_requires_timeline_false(self):
        # デフォルト値の確認: requires_plan=True, requires_timeline=False
        registry = Registry()

        @rule("test.defaults", registry=registry)
        def my_rule(job, th):
            return [_finding("test.defaults")]

        spec = registry.get("test.defaults")
        assert spec.requires_plan is True
        assert spec.requires_timeline is False


# ---------------------------------------------------------------------------
# 5. 例外の分離
# ---------------------------------------------------------------------------


class TestExceptionIsolation:
    def test_raising_rule_does_not_propagate_and_others_still_run(self):
        registry = Registry()

        @rule("test.raises", requires_plan=False, registry=registry)
        def bad_rule(job, th):
            raise RuntimeError("boom")

        @rule("test.succeeds_a", requires_plan=False, registry=registry)
        def good_rule_a(job, th):
            return [_finding("test.succeeds_a")]

        @rule("test.succeeds_b", requires_plan=False, registry=registry)
        def good_rule_b(job, th):
            return [_finding("test.succeeds_b")]

        job = make_job()
        findings, skipped = run_rules(job, None, registry=registry)

        succeeded_ids = {f.rule_id for f in findings}
        assert succeeded_ids == {"test.succeeds_a", "test.succeeds_b"}

        skipped_ids = {s.rule_id for s in skipped}
        assert "test.raises" in skipped_ids

    def test_raising_rule_skipped_reason_contains_exception_class_and_message(self):
        registry = Registry()

        @rule("test.raises2", requires_plan=False, registry=registry)
        def bad_rule(job, th):
            raise ValueError("something specific went wrong")

        job = make_job()
        findings, skipped = run_rules(job, None, registry=registry)

        assert len(skipped) == 1
        assert skipped[0].rule_id == "test.raises2"
        assert "ValueError" in skipped[0].reason
        assert "something specific went wrong" in skipped[0].reason


# ---------------------------------------------------------------------------
# 6. enabled フィルタ（fnmatch パターン）
# ---------------------------------------------------------------------------


class TestEnabledFiltering:
    def test_none_runs_all_rules(self):
        registry = Registry()

        @rule("skew.ratio", requires_plan=False, registry=registry)
        def rule_a(job, th):
            return [_finding("skew.ratio")]

        @rule("cost.bytes_billed", requires_plan=False, registry=registry)
        def rule_b(job, th):
            return [_finding("cost.bytes_billed")]

        job = make_job()
        findings, skipped = run_rules(job, None, enabled=None, registry=registry)
        assert {f.rule_id for f in findings} == {"skew.ratio", "cost.bytes_billed"}

    def test_fnmatch_patterns_filter_rules(self):
        registry = Registry()

        @rule("skew.ratio", requires_plan=False, registry=registry)
        def rule_a(job, th):
            return [_finding("skew.ratio")]

        @rule("skew.other", requires_plan=False, registry=registry)
        def rule_b(job, th):
            return [_finding("skew.other")]

        @rule("cost.bytes_billed", requires_plan=False, registry=registry)
        def rule_c(job, th):
            return [_finding("cost.bytes_billed")]

        job = make_job()
        findings, skipped = run_rules(
            job, None, enabled={"skew.*", "cost.bytes_billed"}, registry=registry
        )
        assert {f.rule_id for f in findings} == {"skew.ratio", "skew.other", "cost.bytes_billed"}

    def test_excluded_rules_produce_no_skipped_rule(self):
        registry = Registry()

        @rule("skew.ratio", requires_plan=False, registry=registry)
        def rule_a(job, th):
            return [_finding("skew.ratio")]

        @rule("cost.bytes_billed", requires_plan=False, registry=registry)
        def rule_b(job, th):
            return [_finding("cost.bytes_billed")]

        job = make_job()
        findings, skipped = run_rules(job, None, enabled={"skew.*"}, registry=registry)
        assert [f.rule_id for f in findings] == ["skew.ratio"]
        assert skipped == [], "ユーザーが明示的に無効化したルールは SkippedRule を生成しない"

    def test_enabled_filter_does_not_call_excluded_rule(self):
        registry = Registry()
        called = {"count": 0}

        @rule("skew.ratio", requires_plan=False, registry=registry)
        def rule_a(job, th):
            called["count"] += 1
            return []

        job = make_job()
        run_rules(job, None, enabled={"cost.*"}, registry=registry)
        assert called["count"] == 0


# ---------------------------------------------------------------------------
# 7. None を返すルールはクラッシュしない
# ---------------------------------------------------------------------------


class TestNoneReturnIsTreatedAsNoFindings:
    def test_rule_returning_none_does_not_crash(self):
        registry = Registry()

        @rule("test.returns_none", requires_plan=False, registry=registry)
        def my_rule(job, th):
            return None

        job = make_job()
        findings, skipped = run_rules(job, None, registry=registry)
        assert findings == []
        assert skipped == []


# ---------------------------------------------------------------------------
# 8. 複数 Finding を yield するルール（ジェネレータ形式）と全ルールの連結
# ---------------------------------------------------------------------------


class TestMultipleFindingsConcatenated:
    def test_generator_style_rule_yielding_multiple_findings(self):
        registry = Registry()

        @rule("test.multi", requires_plan=False, registry=registry)
        def my_rule(job, th):
            yield _finding("test.multi")
            yield _finding("test.multi")

        job = make_job()
        findings, skipped = run_rules(job, None, registry=registry)
        assert len(findings) == 2

    def test_findings_from_all_rules_are_concatenated(self):
        registry = Registry()

        @rule("a.rule", requires_plan=False, registry=registry)
        def rule_a(job, th):
            return [_finding("a.rule"), _finding("a.rule")]

        @rule("b.rule", requires_plan=False, registry=registry)
        def rule_b(job, th):
            return [_finding("b.rule")]

        job = make_job()
        findings, skipped = run_rules(job, None, registry=registry)
        assert len(findings) == 3


# ---------------------------------------------------------------------------
# アーキテクチャ制約: rules/ は collect/ や google 等を import してはならない
# ---------------------------------------------------------------------------


class TestRulesPackageDoesNotImportCollectOrIO:
    """rules/ 配下の全モジュールを AST 解析し、禁止 import が無いことを確認する。

    実際に import して確かめる方法だと「たまたま今は間接的に読み込まれていない」
    だけの偽陰性がありうるため、静的な AST 解析で構文的に締め出す。
    """

    FORBIDDEN_MODULES = ("collect", "google")

    def _iter_rule_py_files(self):
        return sorted(RULES_DIR.rglob("*.py"))

    def _imported_top_level_names(self, tree: ast.Module) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                # 相対 import (from . import x) は level > 0 になる。
                # 絶対 import のトップレベル名だけを拾う。
                if node.module is not None and node.level == 0:
                    names.add(node.module.split(".")[0])
        return names

    def test_no_rule_module_imports_forbidden_packages(self):
        py_files = self._iter_rule_py_files()
        assert py_files, "rules/ ディレクトリに .py ファイルが見つからない"

        violations = []
        for path in py_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = self._imported_top_level_names(tree)
            for forbidden in self.FORBIDDEN_MODULES:
                if forbidden in imported:
                    violations.append(f"{path}: imports {forbidden!r}")

        assert not violations, "\n".join(violations)

    def test_no_rule_module_does_io_via_open_or_requests(self):
        # 明示的な I/O 関数呼び出しの簡易チェック（open() の直接呼び出し等）。
        py_files = self._iter_rule_py_files()
        for path in py_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id != "open", f"{path}: open() の直接呼び出しを検出"
