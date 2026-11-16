"""σ段階判定。決定的・純粋関数のみ(DBに触らない)ので pytest で全部検証できる。"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

MAD_SCALE = 1.4826
MIN_HISTORY = 14


@dataclass(frozen=True)
class Verdict:
    stage: int            # -1 = insufficient_history, 0..3
    score: float | None   # σ 換算の偏差(向き考慮後)
    baseline: float | None
    reason: str


def _center_spread(history: list[float], method: str) -> tuple[float, float]:
    if method == "zscore":
        return statistics.fmean(history), statistics.pstdev(history)
    if method == "robust":
        med = statistics.median(history)
        mad = statistics.median(abs(x - med) for x in history)
        return med, mad * MAD_SCALE
    raise ValueError(f"unknown method: {method}")


def classify(history: list[float], value: float, method: str = "zscore",
             direction: str = "both", min_history: int = MIN_HISTORY) -> Verdict:
    if len(history) < min_history:
        return Verdict(-1, None, None, "insufficient_history")

    center, spread = _center_spread(list(history), method)

    if spread == 0:
        if value == center:
            return Verdict(0, 0.0, center, "constant_history_unchanged")
        delta = value - center
        if (direction == "up" and delta < 0) or (direction == "down" and delta > 0):
            return Verdict(0, 0.0, center, "constant_history_ignored_direction")
        return Verdict(3, float("inf"), center, "constant_history_changed")

    z = (value - center) / spread
    if direction == "up":
        score = max(z, 0.0)
    elif direction == "down":
        score = max(-z, 0.0)
    else:
        score = abs(z)

    stage = 3 if score >= 3 else 2 if score >= 2 else 1 if score >= 1 else 0
    return Verdict(stage, score, center, f"{method}:{z:+.2f}")
