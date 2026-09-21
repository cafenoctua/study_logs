"""bq-job-diagnose の MCP サーバーパッケージ。

`server.py` が実際のツール登録・起動ロジックを持つ。このパッケージ自体は
公開 API を re-export しない（`bq_job_diagnose.mcp_server.server` を直接
import して使う）。
"""

from __future__ import annotations
