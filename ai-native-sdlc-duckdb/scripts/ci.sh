#!/usr/bin/env bash
# ci.yml のローカル版。unit → dbt-slim-ci → 結果保存。
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR=$PWD DBT_PROJECT_DIR=$PWD
PR_NUMBER=${PR_NUMBER:-local}; export PR_NUMBER
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
ATTEMPT=${CI_ATTEMPT:-1}
STATE=artifacts/prod-manifest

record() { python ci/record.py ci_run "$SHA" "$PR_NUMBER" "$ATTEMPT" "$1" >/dev/null || true; }
trap 'record failure' ERR

echo "== unit =="
pytest -q
CHANGED=$(git diff --name-only --diff-filter=AM origin/main...HEAD -- 'models/*.sql' 2>/dev/null \
          | sed "s#^$(git rev-parse --show-prefix)##" || true)
if [ -n "$CHANGED" ]; then dbt lint $CHANGED; else echo "no changed SQL"; fi

echo "== bigquery-compat (static analysis, no connection) =="
dbt compile --target bq_compat --static-analysis strict

echo "== dbt-slim-ci (analytics_ci_pr${PR_NUMBER}) =="
rm -f warehouse/ci.duckdb
if [ -f "$STATE/manifest.json" ]; then
  dbt build --target ci --select state:modified+ --defer --state "$STATE"
else
  echo "prod manifest がないので全件 build"
  dbt build --target ci
fi
python ci/upload_run_results.py ci "$SHA"
trap - ERR
record success
echo "CI PASS"
