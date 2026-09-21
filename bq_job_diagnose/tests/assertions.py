"""ルールのテストで共有するアサーションヘルパー。

制約3（Finding.summary は観測事実のみ、提案を書かない）を機械的に検証するための
共有ヘルパーをここに置く。各ルールのテストで生成された Finding すべてに対して
`assert_no_suggestion_words` を適用すること。
"""

from __future__ import annotations

from bq_job_diagnose.models import Finding

# summary に含まれてはならない「提案」を示す語のリスト。
SUGGESTION_WORDS = ["すべき", "ましょう", "検討", "推奨", "してください"]


def assert_no_suggestion_words(finding: Finding) -> None:
    """Finding.summary に提案を示唆する語が含まれていないことを確認する。

    `Finding.summary` は観測事実のみを記述し、「〜すべき」「〜を検討」のような
    提案は Skill（LLM）側の責務とする（REVIEW_GUIDE.md 1.4 参照）。
    """
    for word in SUGGESTION_WORDS:
        assert word not in finding.summary, (
            f"summary に提案を示唆する語 {word!r} が含まれています: {finding.summary!r}"
        )
