# ローカル完結の AI-Native SDLC サンプル(Rust 版)。クラウドは一切使わない。
BIN := $(CURDIR)/target/release
export FORGE_PROJECT_DIR := $(CURDIR)
export PATH := $(BIN):$(PATH)

.PHONY: setup build ops dev test lint bq-compat ci deploy monitor kpi seed-history clean

setup:            ## Rust バイナリ(forge / monitor / guard)と sqruff を入れる
	cargo build --release --locked
	command -v sqruff >/dev/null || cargo install sqruff --locked

build:
	cargo build --release --locked

ops: build        ## ops スキーマ(prod.duckdb 内)を作成
	forge ops init

dev: build        ## 開発ターゲットで build
	forge build --target dev

test:             ## Rust のテスト(フック・σ判定・forge の結合テスト)
	cargo test --workspace --locked

lint: build       ## SQL lint(描画後の SQL を sqruff で)
	forge lint

bq-compat: build  ## BigQuery で通らない書き方を接続なしで検出
	forge bq-compat

ci: build         ## Slim CI 相当(state:modified+ / defer)
	bash scripts/ci.sh

deploy: build     ## 人間の承認ゲート付き本番デプロイ
	bash scripts/deploy.sh

monitor: build    ## collect → detect →(段階2以上なら)診断プロンプト生成
	monitor collect && monitor detect

kpi: build        ## 週次KPI
	forge query --read-only monitoring/sql/kpi.sql

seed-history: build ## 監視デモ用に過去28日分の擬似スナップショットを投入
	monitor seed-history

clean:
	rm -rf forge_target artifacts warehouse/*.duckdb
