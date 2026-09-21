"""診断結果のレポート層（JSON / Markdown）。

設計上の制約（重要）:
- このパッケージは `google`（google-cloud-bigquery 等）を import してはならない。
  `collect/` の責務である実際の I/O とは分離する。
- JSON レポートは Skill（LLM）との契約（スキーマ）そのものなので、
  互換性を壊す変更は `schema_version` を上げること。
"""

from __future__ import annotations
