"""解決済みの Enum から SQL を決定論的に組み立てる。

この spike の主要な主張点。JEV はここに一切関与しない。
入力は Enum だけなので、文字列連結をしていても
SQL インジェクションも存在しないカラム名も構造上起こりえない
（Enum に無い値は、そもそもこの関数に到達できない）。
"""

from __future__ import annotations

from .semantic_model import Grain, Metric, Period, Region

_METRIC_SQL: dict[Metric, str] = {
    Metric.REVENUE: "SUM(f.revenue)",
    Metric.ORDER_COUNT: "COUNT(DISTINCT f.order_id)",
    Metric.AOV: "SAFE_DIVIDE(SUM(f.revenue), COUNT(DISTINCT f.order_id))",
}

_GRAIN_SQL: dict[Grain, str] = {
    Grain.DAY: "d.date",
    Grain.MONTH: "d.month",
    Grain.QUARTER: "d.quarter",
}

_REGION_SQL: dict[Region, str | None] = {
    Region.KANTO: "r.region_name = '関東'",
    Region.KANSAI: "r.region_name = '関西'",
    Region.ALL: None,  # 絞り込みなし
}

_PERIOD_SQL: dict[Period, str] = {
    Period.LAST_MONTH: (
        "d.date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH) "
        "AND d.date < DATE_TRUNC(CURRENT_DATE(), MONTH)"
    ),
    Period.THIS_MONTH: "d.date >= DATE_TRUNC(CURRENT_DATE(), MONTH) AND d.date <= CURRENT_DATE()",
    Period.LAST_QUARTER: (
        "d.date >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 QUARTER), QUARTER) "
        "AND d.date < DATE_TRUNC(CURRENT_DATE(), QUARTER)"
    ),
    Period.LAST_7_DAYS: "d.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
}


def build_sql(metric: Metric, grain: Grain, region: Region, period: Period) -> str:
    """4つの軸から1本の集計クエリを組み立てる。"""
    select_metric = _METRIC_SQL[metric]
    group_col = _GRAIN_SQL[grain]

    where = [_PERIOD_SQL[period]]
    region_pred = _REGION_SQL[region]
    if region_pred is not None:
        where.append(region_pred)

    where_clause = "\n  AND ".join(where)

    return (
        f"SELECT\n"
        f"  {group_col} AS period,\n"
        f"  {select_metric} AS {metric.value}\n"
        f"FROM fact_sales AS f\n"
        f"JOIN dim_date AS d ON f.order_date = d.date_key\n"
        f"JOIN dim_region AS r ON f.region_key = r.region_key\n"
        f"WHERE {where_clause}\n"
        f"GROUP BY period\n"
        f"ORDER BY period"
    )
