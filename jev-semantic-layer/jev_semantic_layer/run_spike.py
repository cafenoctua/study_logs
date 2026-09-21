"""全テストケースを実 API に投げ、結果表を出力する。

この spike が答えるべき問い:
  1. JEV の confidence は実際に曖昧さと相関するか
  2. 実測レイテンシ・コストは実用範囲か
  3. この方式を本格的に作る価値があるか
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from typesafe_sdk import TypeSafeError

from .jev_client import ANSWERABLE_KEY, JevSemanticClient, MissingAPIKeyError
from .router import clarify_message, route, top_n
from .semantic_model import DIMENSIONS
from .test_cases import CASES

RULE = "=" * 72


def render(res, case) -> None:
    """1ケース分の結果を表示する。"""
    call = res.call
    print(RULE)
    print(f"Q: {case.question}")
    print(f"   期待: {'clarify' if case.expect_clarify else 'SQL 生成'} — {case.rationale}")
    print(f"   実測: {call.latency_ms:.0f}ms / in={call.input_tokens} tok / model={call.model}")
    print()

    print(f"   {ANSWERABLE_KEY}: {call.noul(ANSWERABLE_KEY):.2f}")
    for dim in DIMENSIONS:
        choice, conf, probs = call.choice(dim.name)
        dist = "  ".join(f"{n}={p:.2f}" for n, p in top_n(probs, 3))
        print(f"   {dim.name:8s}: {choice:12s} conf={conf:.2f}   [{dist}]")
    print()

    actual = "clarify" if res.clarified else "SQL 生成"
    match = "✅ 一致" if res.clarified == case.expect_clarify else "❌ 不一致"
    print(f"   → 判断: {actual}   {match}")
    print()

    if res.sql:
        for line in res.sql.splitlines():
            print(f"     {line}")
    else:
        for line in clarify_message(res).splitlines():
            print(f"     {line}")
    print()


def main() -> int:
    load_dotenv()

    try:
        client = JevSemanticClient()
    except MissingAPIKeyError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    results: list[tuple[object, object]] = []
    failures = 0

    for case in CASES:
        try:
            res = route(client, case.question)
        except TypeSafeError as e:
            print(RULE)
            print(f"Q: {case.question}")
            print(f"   ❌ API エラー: {type(e).__name__}: {e}")
            print()
            failures += 1
            continue

        render(res, case)
        results.append((case, res))

    # --- 集計 ---------------------------------------------------------
    print(RULE)
    print("サマリ")
    print(RULE)

    matched = sum(1 for c, r in results if r.clarified == c.expect_clarify)
    total_ms = sum(r.call.latency_ms for _, r in results)
    total_in = sum(r.call.input_tokens or 0 for _, r in results)

    print(f"  期待と一致: {matched}/{len(results)}")
    if failures:
        print(f"  API エラー: {failures} 件")
    if results:
        print(f"  平均レイテンシ: {total_ms / len(results):.0f}ms")
        print(f"  合計入力トークン: {total_in}")
    print()

    mismatches = [(c, r) for c, r in results if r.clarified != c.expect_clarify]
    if mismatches:
        print("  期待と外れたケース（これが発見）:")
        for c, r in mismatches:
            got = "clarify した" if r.clarified else "SQL を出した"
            want = "clarify すべき" if c.expect_clarify else "SQL を出すべき"
            print(f"    - 「{c.question}」 {want}が、{got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
