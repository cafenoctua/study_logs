"""セマンティックモデル: このレイヤーが「意味」として認めるものの全体。

ここが唯一の定義源。JEV に渡す criteria も、SQL 組み立ても、両方ここから導出する。
定義を二箇所に書かないことが重要で、それによって
「JEV が選べる値」と「SQL が組み立てられる値」が構造的にズレなくなる。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Metric(StrEnum):
    """集計したい指標。"""

    REVENUE = "revenue"
    ORDER_COUNT = "order_count"
    AOV = "aov"


class Grain(StrEnum):
    """時間軸の粒度。"""

    DAY = "day"
    MONTH = "month"
    QUARTER = "quarter"


class Region(StrEnum):
    """地域フィルタ。ALL は絞り込みなし。"""

    KANTO = "kanto"
    KANSAI = "kansai"
    ALL = "all"


class Period(StrEnum):
    """対象期間。"""

    LAST_MONTH = "last_month"
    THIS_MONTH = "this_month"
    LAST_QUARTER = "last_quarter"
    LAST_7_DAYS = "last_7_days"


# --- JEV に渡す説明文 -------------------------------------------------
#
# JEV は criteria の説明文を読んで判断するため、この文言が精度を直接左右する。
# 「何であるか」だけでなく「何でないか」を書くと、隣接する選択肢との
# 境界が JEV に伝わりやすい（revenue と aov の区別など）。

METRIC_CRITERIA: dict[str, str] = {
    Metric.REVENUE: "売上金額の合計。「売上」「いくら売れた」「金額」を問うもの。件数ではない。",
    Metric.ORDER_COUNT: "注文の件数。「何件」「注文数」「いくつ売れた」を問うもの。金額ではない。",
    Metric.AOV: "平均注文単価（売上 ÷ 注文件数）。「単価」「客単価」「1件あたり」を問うもの。",
}

GRAIN_CRITERIA: dict[str, str] = {
    Grain.DAY: "日単位で分けて見たい。「日別」「日ごと」「デイリー」。",
    Grain.MONTH: "月単位で分けて見たい。「月別」「月ごと」。粒度の指定が無い場合もこれが既定。",
    Grain.QUARTER: "四半期単位で分けて見たい。「四半期」「Q1」「クォーター」。",
}

REGION_CRITERIA: dict[str, str] = {
    Region.KANTO: "関東地方に絞る。「関東」「東京」「首都圏」。",
    Region.KANSAI: "関西地方に絞る。「関西」「大阪」「近畿」。",
    Region.ALL: "地域を絞らず全体を見る。地域の言及が無い場合はこれ。",
}

PERIOD_CRITERIA: dict[str, str] = {
    Period.LAST_MONTH: "先月（1か月前の月の初日から末日まで）。",
    Period.THIS_MONTH: "今月（今月の初日から今日まで）。",
    Period.LAST_QUARTER: "前四半期。",
    Period.LAST_7_DAYS: "直近7日間。「最近1週間」「ここ1週間」。",
}


@dataclass(frozen=True)
class Dimension:
    """解決すべき1つの軸。JEV の1つの choice 質問に対応する。"""

    name: str
    enum: type[StrEnum]
    criteria: dict[str, str]
    instructions: str


# ルータが解決する軸の一覧。ここに1行足せば JEV の質問も1つ増える。
DIMENSIONS: tuple[Dimension, ...] = (
    Dimension(
        name="metric",
        enum=Metric,
        criteria=METRIC_CRITERIA,
        instructions="この質問が知りたがっている指標はどれか？",
    ),
    Dimension(
        name="grain",
        enum=Grain,
        criteria=GRAIN_CRITERIA,
        instructions="結果をどの時間粒度で分けるべきか？",
    ),
    Dimension(
        name="region",
        enum=Region,
        criteria=REGION_CRITERIA,
        instructions="どの地域に絞るべきか？",
    ),
    Dimension(
        name="period",
        enum=Period,
        criteria=PERIOD_CRITERIA,
        instructions="どの期間を対象にすべきか？",
    ),
)


# JEV に与えるスキーマの説明。state の一部として渡す。
SCHEMA_DESCRIPTION = """\
分析対象は小売の売上データウェアハウスである。

テーブル:
- fact_sales (order_id, order_date, region_key, product_key, revenue)
- dim_date (date_key, date, month, quarter)
- dim_region (region_key, region_name)
- dim_product (product_key, product_name)

このデータで答えられるのは「売上金額・注文件数・平均単価」を
「日/月/四半期」の粒度で、「地域」と「期間」で絞って集計することのみ。\
"""
