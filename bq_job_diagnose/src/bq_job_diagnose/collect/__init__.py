"""BigQuery INFORMATION_SCHEMA へのアクセスを担うパッケージ。

`sql.py` は SQL 文字列を組み立てる純粋関数のみを持ち、ネットワーク呼び出しは
行わない（`google.cloud` に依存しない）。実際の API 呼び出しは Phase 10 で
別モジュールとして追加される。
"""

from __future__ import annotations
