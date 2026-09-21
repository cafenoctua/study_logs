"""テストケース: 曖昧な質問が本命。

実 API を叩くので、期待が外れることこそが発見。
外れたときに期待の方を後から書き換えないため、ここに先に書いておく。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    question: str
    expect_clarify: bool
    rationale: str


CASES: tuple[Case, ...] = (
    Case(
        question="先月の関西の売上どうだった？",
        expect_clarify=False,
        rationale="全軸が明示されている。metric=revenue, region=kansai, period=last_month",
    ),
    Case(
        question="最近調子どう？",
        expect_clarify=True,
        rationale="metric も period も特定できない。聞き返すべき",
    ),
    Case(
        question="売れ行きは？",
        expect_clarify=True,
        rationale="revenue（金額）と order_count（件数）が拮抗するはず",
    ),
    Case(
        question="A商品とB商品どっちが上？",
        expect_clarify=True,
        rationale="比較は単一クエリに写像できない。is_answerable が低いはず",
    ),
    Case(
        question="今月の平均単価を日別で",
        expect_clarify=False,
        rationale="aov + day + this_month が明示されている",
    ),
    Case(
        question="来月の売上いくらになりそう？",
        expect_clarify=True,
        rationale="予測は集計クエリでは答えられない。is_answerable が低いはず",
    ),
    Case(
        question="関東の注文件数を四半期ごとに、直近1週間で",
        expect_clarify=True,
        rationale="grain=quarter と period=last_7_days が矛盾する。JEV が気づくかは未知",
    ),
)
