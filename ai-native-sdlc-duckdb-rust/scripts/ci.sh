#!/usr/bin/env bash
# ci.yml のローカル版。unit → lint → bigquery-compat → slim-ci → 結果保存。
# forge / monitor は target/release にビルド済みであること(make ci なら自動)。
set -euo pipefail
cd "$(dirname "$0")/.."
export FORGE_PROJECT_DIR=$PWD PATH="$PWD/target/release:$PATH"
PR_NUMBER=${PR_NUMBER:-local}; export PR_NUMBER
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
ATTEMPT=${CI_ATTEMPT:-1}
STATE=artifacts/prod-manifest

record() { forge ops record-ci-run "$SHA" "$PR_NUMBER" "$ATTEMPT" "$1" >/dev/null 2>&1 || true; }
trap 'record failure' ERR

echo "== unit =="
cargo test --workspace --locked --quiet
CHANGED=$(git diff --name-only --diff-filter=AM origin/main...HEAD -- 'models/*.sql' 2>/dev/null \
          | sed "s#^$(git rev-parse --show-prefix 2>/dev/null)##" || true)
if [ -n "$CHANGED" ]; then forge lint $CHANGED; else echo "no changed SQL"; fi

echo "== bigquery-compat (static analysis, no connection) =="
forge bq-compat

echo "== slim-ci (analytics_ci_pr${PR_NUMBER}) =="
rm -f warehouse/ci.duckdb
if [ -f "$STATE/manifest.json" ]; then
  forge build --target ci --select state:modified+ --defer --state "$STATE"
else
  echo "prod manifest がないので全件 build"
  forge build --target ci
fi
forge ops upload-results ci "$SHA"
trap - ERR
record success
echo "CI PASS"
