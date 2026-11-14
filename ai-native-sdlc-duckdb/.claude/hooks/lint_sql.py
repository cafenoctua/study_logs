"""PostToolUse: 編集した SQL 1ファイルだけ `dbt lint`(v2 内蔵の SQLFluff 互換 linter)で lint。違反は exit 2 で Claude に返し、その場で直させる。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys


def target_sql(data: dict) -> str | None:
    path = (data.get("tool_input") or {}).get("file_path") or ""
    norm = path.replace(os.sep, "/")
    if norm.endswith(".sql") and "/models/" in f"/{norm}":
        return path
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    path = target_sql(data)
    if not path or not shutil.which("dbt"):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    r = subprocess.run(["dbt", "lint", path],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"lint violations in {path}:\n{r.stdout[-4000:]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
