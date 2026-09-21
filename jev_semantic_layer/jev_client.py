"""JEV 公式 SDK の薄いラッパ。

この spike の主目的は実測なので、レイテンシとトークン使用量の記録を
クライアント層に埋め込んでいる。呼び出し側は計測を意識しなくてよい。

API キーは SDK が環境変数 TYPESAFE_API_KEY から読む。
このモジュールはキーの値を一切受け取らず、変数にも保持しない。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from typesafe_sdk import (
    Choice,
    Noul,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
    TypeSafeRateLimitError,
)

from .semantic_model import DIMENSIONS, SCHEMA_DESCRIPTION

ANSWERABLE_KEY = "is_answerable"


class MissingAPIKeyError(RuntimeError):
    """TYPESAFE_API_KEY が未設定。"""


@dataclass
class JevCall:
    """1回の JEV 呼び出しの結果と実測値。"""

    answers: dict[str, Any]
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    model: str

    def choice(self, key: str) -> tuple[str, float, dict[str, float]]:
        """choice 回答を (選択値, confidence, 全分布) で返す。"""
        a = self.answers[key]
        return a.choice, a.confidence, a.probabilities

    def noul(self, key: str) -> float:
        return self.answers[key].noul


def build_questions() -> dict[str, Choice | Noul]:
    """セマンティックモデルから JEV の質問セットを導出する。

    DIMENSIONS に軸を足せば、ここも自動的に追随する。
    """
    questions: dict[str, Choice | Noul] = {
        dim.name: Choice(
            instructions=dim.instructions,
            criteria=dict(dim.criteria),
        )
        for dim in DIMENSIONS
    }
    # 個々の軸を見る前の門番。単一の集計クエリに写像できない質問を弾く。
    questions[ANSWERABLE_KEY] = Noul(
        instructions=(
            "この質問は、上記スキーマに対する『単一の集計クエリ』ひとつで答えられるか？ "
            "複数の対象を比較する、推論や予測を求める、スキーマに無いものを尋ねる "
            "といった場合は No。"
        )
    )
    return questions


class JevSemanticClient:
    """JEV へ問い合わせ、実測値つきで返す。"""

    def __init__(self, timeout: float = 30.0) -> None:
        if not os.environ.get("TYPESAFE_API_KEY"):
            raise MissingAPIKeyError(
                ".env に TYPESAFE_API_KEY を設定してください "
                "(.env.example をコピーして値を入れる)"
            )
        # api_key は渡さない。SDK が環境から読むので、キーはこのコードを通らない。
        self._client = TypeSafeClient(timeout=timeout)
        self._questions = build_questions()

    def resolve(self, question: str) -> JevCall:
        """自然言語の質問を JEV に投げ、全軸の判定を1コールで受け取る。"""
        state = f"{SCHEMA_DESCRIPTION}\n\nユーザーの質問:\n{question}"

        started = time.perf_counter()
        try:
            resp: SystemOneResponse = self._client.system_one(
                state=state,
                questions=self._questions,
            )
        except TypeSafeAuthenticationError as e:
            # キーそのものは出さない。SDK の例外文字列にも含まれない想定だが念のため短く。
            raise MissingAPIKeyError(
                "JEV の認証に失敗しました。TYPESAFE_API_KEY の値を確認してください。"
            ) from e
        except (TypeSafeRateLimitError, TypeSafeAPITimeoutError, TypeSafeAPIConnectionError):
            raise
        except TypeSafeError:
            raise
        latency_ms = (time.perf_counter() - started) * 1000

        return JevCall(
            answers=dict(resp.answers),
            latency_ms=latency_ms,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=resp.model,
        )
