#!/usr/bin/env bash
# deploy.yml のローカル版。人間の承認(environment: production 相当)→ prod build → manifest 保存 → 記録
set -euo pipefail
cd "$(dirname "$0")/.."
export DBT_PROFILES_DIR=$PWD DBT_PROJECT_DIR=$PWD
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)

if [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" != "main" ] && [ "${ALLOW_NON_MAIN:-0}" != "1" ]; then
  echo "本番デプロイは main からのみ(練習なら ALLOW_NON_MAIN=1)"; exit 1
fi

echo "deploy $SHA to prod. Approver name (空なら中止):"
read -r APPROVER
[ -n "$APPROVER" ] || { echo "aborted"; exit 1; }

python scripts/init_ops.py >/dev/null
if dbt build --target prod; then
  mkdir -p artifacts/prod-manifest
  cp target/manifest.json artifacts/prod-manifest/manifest.json   # GCS の代わり
  python ci/upload_run_results.py prod "$SHA"
  python ci/record.py deployment "$SHA" "$APPROVER" success
else
  python ci/upload_run_results.py prod "$SHA" || true
  python ci/record.py deployment "$SHA" "$APPROVER" failed
  exit 1
fi
