#!/usr/bin/env bash
# dbt v2 を単体バイナリで入れる(Python 不要)。公式インストーラをバージョン固定で使う。
#   dbt 本体 → <prefix>/bin/dbt、DuckDB 用の ADBC ドライバは初回実行時に dbt が自動取得する
# usage: bash scripts/install_dbt.sh [prefix]   (既定: ./.tools)
set -euo pipefail
DBT_VERSION="${DBT_VERSION:-2.0.11}"
PREFIX="${1:-$(cd "$(dirname "$0")/.." && pwd)/.tools}"

if [ -x "$PREFIX/bin/dbt" ] && [ "$("$PREFIX/bin/dbt" --version | cut -d' ' -f2)" = "$DBT_VERSION" ]; then
  echo "dbt $DBT_VERSION already installed at $PREFIX/bin/dbt"; exit 0
fi
curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh \
  | sh -s -- --version "$DBT_VERSION" --prefix "$PREFIX"
"$PREFIX/bin/dbt" --version
