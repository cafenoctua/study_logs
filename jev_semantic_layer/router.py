"""ルータ: JEV の確率分布を読んで「SQL を出す」か「聞き返す」かを決める。

この spike の核心。JEV は必ず何かを選んでくるので、
「選んだ」ことと「確信している」ことは別物として扱う必要がある。
その境界をどこに引くかがここの責務。

実測で分かったこと（7ケース / jev-1.13.0）:
  判定に使えるのは is_answerable(noul) ただ1つだった。
  軸ごとの confidence は、聞き返すべき質問に対しても 0.90-1.00 を返す。
  JEV は「曖昧さ」ではなく「尤度」を返すため、
  手がかりが皆無でも最も尤もらしい選択肢を自信を持って選ぶ。
"""

from __future__ import annotations

from dataclasses import dataclass

from .jev_client import ANSWERABLE_KEY, JevCall, JevSemanticClient
from .semantic_model import Grain, Metric, Period, Region
from .sql_builder import build_sql

#: is_answerable(noul) がこれ未満なら、単一クエリに写像できないとみなす。
#: 実測では SQL 対象が 0.79-0.88、clarify 対象が 0.04-0.35 と分離し、
#: 0.50 はその谷の中央にあたる。
ANSWERABLE_THRESHOLD = 0.50


@dataclass
class Resolution:
    """ルータの判断結果。sql か、聞き返しかのどちらか。"""

    question: str
    call: JevCall
    sql: str | None
    not_answerable: bool

    @property
    def clarified(self) -> bool:
        """聞き返した（＝ SQL を出さなかった）か。"""
        return self.sql is None


def top_n(probabilities: dict[str, float], n: int = 2) -> list[tuple[str, float]]:
    """確率分布から上位 n 件を返す。"""
    return sorted(probabilities.items(), key=lambda kv: kv[1], reverse=True)[:n]


def decide(call: JevCall) -> bool:
    """JEV の回答を読み、聞き返すべきかを判断する。

    Returns:
        True なら「この質問は単一の集計クエリに写像できない」。

    軸ごとの confidence を見ない理由は本モジュールの docstring のとおり。
    特筆すべきは、軸単位では検出できない破綻も noul が捉えたこと:
    「関東の注文件数を四半期ごとに、直近1週間で」は
    全軸が高確信度（metric=1.00, period=0.96）でありながら
    組み合わせとして矛盾しており、is_answerable=0.24 で弾けた。
    """
    return call.noul(ANSWERABLE_KEY) < ANSWERABLE_THRESHOLD


def route(client: JevSemanticClient, question: str) -> Resolution:
    """質問を JEV に投げ、判断し、SQL か聞き返しを返す。"""
    call = client.resolve(question)
    not_answerable = decide(call)

    sql: str | None = None
    if not not_answerable:
        # Enum に通すことで、JEV の返した文字列がここで検証される。
        # 未知の値ならここで例外になり、不正な SQL は組み立てられない。
        sql = build_sql(
            metric=Metric(call.choice("metric")[0]),
            grain=Grain(call.choice("grain")[0]),
            region=Region(call.choice("region")[0]),
            period=Period(call.choice("period")[0]),
        )

    return Resolution(
        question=question,
        call=call,
        sql=sql,
        not_answerable=not_answerable,
    )


def clarify_message(res: Resolution) -> str:
    """聞き返し文言を組み立てる。"""
    return (
        "この質問は単一の集計クエリでは答えられません。"
        "対象をひとつに絞って、もう一度お尋ねください。"
    )
