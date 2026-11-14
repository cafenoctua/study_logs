# ローカル完結の AI-Native SDLC サンプル。クラウドは一切使わない。
PY ?= python3.14
export DBT_PROFILES_DIR := $(CURDIR)
export DBT_PROJECT_DIR := $(CURDIR)

.PHONY: setup ops dev test lint ci deploy monitor kpi seed-history clean

setup:            ## venv 作成と依存インストール
	$(PY) -m venv .venv && .venv/bin/pip install -r requirements.txt

ops:              ## ops スキーマ(prod.duckdb 内)を作成
	$(PY) scripts/init_ops.py

dev:              ## 開発ターゲットで build
	dbt build --target dev

test:             ## フックとσ判定のユニットテスト
	pytest -q

lint:             ## SQL lint
	dbt lint

ci:               ## Slim CI 相当(state:modified+ / defer)
	bash scripts/ci.sh

deploy:           ## 人間の承認ゲート付き本番デプロイ
	bash scripts/deploy.sh

monitor:          ## collect → detect →(段階2以上なら)診断プロンプト生成
	$(PY) monitoring/collect.py && $(PY) monitoring/detect.py

kpi:              ## 週次KPI
	$(PY) scripts/run_sql.py monitoring/sql/kpi.sql

seed-history:     ## 監視デモ用に過去28日分の擬似スナップショットを投入
	$(PY) scripts/seed_history.py

clean:
	rm -rf target logs artifacts warehouse/*.duckdb
