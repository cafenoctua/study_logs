"""MCP サーバ: Claude から JEV セマンティックレイヤーを呼べるようにする。

役割分担:
    Claude  — ユーザーとの対話、実行可否の確認
    このツール — JEV に意味解決させ、判断結果を返す（確認は取らない）
    JEV     — 選ぶだけ
    コード   — SQL を決定論的に組み立てる

ツールが確認を取らない（elicitation を使わない）のは意図的。
判断材料を返して Claude に説明させる方が、
「metric は revenue と判断されましたが比較質問なので実行できません」のような
文脈に応じた説明ができる。

注意: stdout は MCP のプロトコル channel なので、
このモジュールとその依存は stdout に何も書いてはならない（ログは stderr）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from typesafe_sdk import TypeSafeError

from .jev_client import ANSWERABLE_KEY, JevSemanticClient, MissingAPIKeyError
from .router import clarify_message, route
from .semantic_model import DIMENSIONS

# MCP サーバは任意の cwd から起動されるため、.env はこのファイルからの相対で解決する。
# （キーをコマンド履歴に残さないよう、-e での受け渡しは避ける）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

mcp = MCPServer(name="jev-semantic-layer")

TOOL_DESCRIPTION = """\
架空の小売売上データウェアハウスに対する自然言語の質問を、
JEV (TypeSafe AI) を使って型安全な SQL に解決する。

扱えるのは、売上金額・注文件数・平均単価を、日/月/四半期の粒度で、
地域(関東/関西/全体)と期間(先月/今月/前四半期/直近7日)で絞った集計のみ。

複数商品の比較・将来予測・スキーマ外の質問には SQL を返さず、
status="clarify" を返す。その場合は自分で SQL を書かず、
返された reason をユーザーに伝えて質問を絞り込んでもらうこと。

SQL は生成するのみで、実行はしない。\
"""

# クライアントは遅延初期化する。
# 起動時にキーが無くてもサーバ自体は立ち、
# 呼び出し時にエラーを返せるようにするため（Claude が原因を説明できる）。
_client: JevSemanticClient | None = None


def _get_client() -> JevSemanticClient:
    global _client
    if _client is None:
        _client = JevSemanticClient()
    return _client


def _resolved_axes(call: Any) -> dict[str, dict[str, Any]]:
    """各軸の判断を Claude が読める形に整形する。"""
    out: dict[str, dict[str, Any]] = {}
    for dim in DIMENSIONS:
        value, confidence, probabilities = call.choice(dim.name)
        out[dim.name] = {
            "value": value,
            "confidence": round(confidence, 3),
            "probabilities": {k: round(v, 3) for k, v in probabilities.items()},
        }
    return out


@mcp.tool(description=TOOL_DESCRIPTION)
def resolve_metric_query(question: str) -> dict[str, Any]:
    """自然言語の質問を JEV で解決し、SQL か聞き返しを返す。"""
    try:
        client = _get_client()
        res = route(client, question)
    except MissingAPIKeyError as e:
        # キーの値は決してメッセージに含めない。
        return {
            "status": "error",
            "message": str(e),
            "hint": "jev-semantic-layer-wt/.env に TYPESAFE_API_KEY を設定してください",
        }
    except TypeSafeError as e:
        return {
            "status": "error",
            "message": f"JEV API の呼び出しに失敗しました: {type(e).__name__}",
        }

    call = res.call
    payload: dict[str, Any] = {
        "status": "clarify" if res.clarified else "resolved",
        "question": question,
        "sql": res.sql,
        "is_answerable": round(call.noul(ANSWERABLE_KEY), 3),
        "resolved": _resolved_axes(call),
        "measured": {
            "latency_ms": round(call.latency_ms),
            "input_tokens": call.input_tokens,
            "model": call.model,
        },
    }

    if res.clarified:
        payload["reason"] = clarify_message(res)
        # 軸ごとの confidence が高くても答えられないことがある、と明示する。
        # これが無いと Claude は「metric=1.00 なら大丈夫だろう」と誤読しうる。
        payload["note"] = (
            "resolved の各軸は参考値。confidence が高くても "
            "is_answerable が低ければこの質問には答えられない。"
            "自分で SQL を書かず、reason をユーザーに伝えること。"
        )

    return payload


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
