"""PreToolUse: 本番設定・デプロイ・フック自身の編集を exit 2 でブロックする。
LOCK_TESTS=1 のときはテストと schema.yml も保護(バグ修正中のテスト改変を防ぐ)。
解析できない入力は通す(fail-open)。"""
from __future__ import annotations

import fnmatch
import json
import os
import sys

ALWAYS = [
    "profiles.yml",
    "scripts/deploy.sh",
    "workflows/deploy.yml",
    ".github/workflows/deploy.yml",
    ".claude/hooks/*",
    ".claude/settings.json",
]
TESTS = ["tests/*", "tests_dbt/*", "models/*schema.yml", "models/**/schema.yml"]


def _rel(path: str, root: str) -> str:
    p = os.path.abspath(path)
    r = os.path.abspath(root)
    return os.path.relpath(p, r).replace(os.sep, "/") if p.startswith(r) else path


def check(path: str, root: str, lock_tests: bool) -> str | None:
    rel = _rel(path, root)
    pats = ALWAYS + (TESTS if lock_tests else [])
    for pat in pats:
        if fnmatch.fnmatch(rel, pat):
            return f"blocked: {rel} は保護対象です({pat})。人間に変更を依頼してください。"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
        ti = data.get("tool_input", {})
        path = ti.get("file_path") or ti.get("notebook_path")
    except Exception:
        return 0
    if not path:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    msg = check(path, root, os.environ.get("LOCK_TESTS") == "1")
    if msg:
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
