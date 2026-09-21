"""インストール済みパッケージとして import できることを検証する。

このテストが存在する理由:
`collect/information_schema.py` が `from scripts.anonymize_fixture import ...` と
書かれていた時期があり、全テストが緑のまま実運用で ModuleNotFoundError になった。
pytest はリポジトリルートを sys.path に入れるため `scripts` が見えるが、
インストールされたパッケージは src/bq_job_diagnose/ の中しか持たないため。

そこでリポジトリルートを sys.path から除いた子プロセスで import を試す。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# CLI が実行時に import する全モジュール。
_RUNTIME_MODULES = [
    "bq_job_diagnose.cli",
    "bq_job_diagnose.anonymize",
    "bq_job_diagnose.collect.information_schema",
    "bq_job_diagnose.collect.jobs_api",
    "bq_job_diagnose.collect.file_collector",
    "bq_job_diagnose.report.json_report",
    "bq_job_diagnose.report.markdown_report",
    "bq_job_diagnose.rules.all",
]


@pytest.mark.parametrize("module", _RUNTIME_MODULES)
def test_module_imports_without_repo_root_on_path(module: str) -> None:
    """リポジトリルートを sys.path に含めずに import できること。

    失敗する場合、src/ の外（scripts/ など）に依存している可能性が高い。
    """
    code = f"import {module}"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd="/",  # リポジトリルートを cwd から外す
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{module} をインストール済みパッケージとして import できません。\n"
        f"src/ の外のモジュールに依存していないか確認してください。\n"
        f"{result.stderr}"
    )


def test_no_src_module_imports_from_scripts() -> None:
    """src/ 配下が `scripts` パッケージを import していないこと。

    `scripts/` はパッケージに含まれないため、実運用で必ず失敗する。
    """
    offenders = []
    for path in (_REPO_ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from scripts" in text or "import scripts" in text:
            offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert offenders == [], f"src/ の外を import しています: {offenders}"
