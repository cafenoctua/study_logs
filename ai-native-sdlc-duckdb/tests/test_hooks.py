import json
import subprocess
import sys
from pathlib import Path

import lint_sql
from protect_paths import check

ROOT = "/repo"
HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "protect_paths.py"


def test_blocks_profiles_and_deploy():
    assert check("/repo/profiles.yml", ROOT, False)
    assert check("/repo/scripts/deploy.sh", ROOT, False)
    assert check("/repo/.claude/hooks/lint_sql.py", ROOT, False)


def test_allows_models():
    assert check("/repo/models/marts/fct_orders.sql", ROOT, False) is None


def test_lock_tests_protects_tests_and_schema():
    assert check("/repo/tests/test_severity.py", ROOT, False) is None
    assert check("/repo/tests/test_severity.py", ROOT, True)
    assert check("/repo/models/marts/schema.yml", ROOT, True)


def test_hook_exit_codes(tmp_path):
    def run(payload, env=None):
        return subprocess.run([sys.executable, str(HOOK)], input=payload, text=True,
                              capture_output=True, env={"CLAUDE_PROJECT_DIR": "/repo", **(env or {})}).returncode
    assert run(json.dumps({"tool_input": {"file_path": "/repo/profiles.yml"}})) == 2
    assert run(json.dumps({"tool_input": {"file_path": "/repo/models/x.sql"}})) == 0
    assert run("not json") == 0  # fail-open


def test_lint_targets_only_model_sql():
    assert lint_sql.target_sql({"tool_input": {"file_path": "/repo/models/a.sql"}})
    assert lint_sql.target_sql({"tool_input": {"file_path": "/repo/README.md"}}) is None
