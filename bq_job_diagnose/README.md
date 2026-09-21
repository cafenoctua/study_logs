# bq-job-diagnose

BigQuery ジョブのクエリプラン（Query Plan）とタイムライン（Timeline）から、性能問題を**決定論的に**診断する CLI。

## 設計方針: 決定論（CLI）と非決定論（Skill）の分離

このプロジェクトの構造的な主張は一つ。

> **決定論で書ける部分は全てプログラムに落とし、判断が要る部分だけ LLM に渡す。**

- **この CLI（`bq-job-diagnose`）は観測事実のみを出力する。** ジョブのプラン・タイムラインから計算された数値（スキュー比率、フィルタ効率、コスト試算など）を、閾値と比較して機械的に判定するだけで、「〜すべき」のような改善提案は一切書かない。
- **改善提案は Claude Code の Agent Skill（`.claude/skills/bq-diagnose/SKILL.md`）が担う。** CLI が出した JSON を読み、クエリ本文やスキーマも踏まえた非決定論的な推論（LLM の判断）として改善案を組み立てる。

この分離を壊す変更（CLI が提案文を書く、Skill が CLI の数値を改変する等）は構造的な不変条件違反であり、`REVIEW_GUIDE.md` のレビュー観点で必ず止められる。

```
BigQuery ジョブ
   │
   ▼
bq-job-diagnose CLI  ── 決定論。数値・findings を出力するのみ
   │  (JSON)
   ▼
/bq-diagnose Skill   ── 非決定論。findings を読んで改善案を LLM が組み立てる
   │
   ▼
ユーザーへの提案（Learning モードのため、適用はユーザー確認後）
```

## インストール / 実行

```bash
cd bq_job_diagnose
uv sync
uv run bq-job-diagnose --help
```

`--install-completion` / `--show-completion` でシェル補完も利用できる。

## 3 モードの実例コマンド

`bq-job-diagnose` には 3 つのサブコマンドがある。

| コマンド | 用途 |
|---|---|
| `job` | 単一ジョブを深掘り診断する |
| `scan` | 期間スキャンで TopN のジョブを一覧する（plan が必要なルールは評価対象外） |
| `drill` | TopN のジョブそれぞれに対してフル診断を行う |

### `job` — 単一ジョブの深掘り診断

```bash
uv run bq-job-diagnose job <JOB_ID> \
  --project my-project --region asia-northeast1 --format json
```

主なオプション（`uv run bq-job-diagnose job --help` より）:

| オプション | 説明 |
|---|---|
| `--project`, `-p` | GCP プロジェクト ID（省略時は ADC のデフォルト） |
| `--region`, `-r` | BigQuery region（例: `us`, `asia-northeast1`）。デフォルト `us` |
| `--config` | 閾値設定 YAML へのパス |
| `--format` | 出力形式（`markdown` / `json` / `both`）。デフォルト `markdown` |
| `--output`, `-o` | 出力先（省略時は標準出力。`both` の場合は拡張子なしのベース名） |
| `--rules` | 実行するルールの fnmatch パターン（カンマ区切り） |
| `--disable-rules` | 無効化するルールの fnmatch パターン（カンマ区切り） |
| `--no-fallback` | `jobs.get` へのフォールバックを行わない |
| `--dry-run-sql` | 実行される SQL とパラメータを表示して終了する（GCP にアクセスしない） |
| `--verbose`, `-v` | 詳細メッセージを標準エラーに出力する |
| `--fail-on` | 指定した重大度以上の所見があれば終了コードを変える |
| `--created-on` | ジョブの実行日（`YYYY-MM-DD`）。分かっていれば検索を高速化する |
| `--stage-limit` | レポートに含めるステージ数の上限。デフォルト `15` |

### `scan` — 期間スキャン

```bash
uv run bq-job-diagnose scan \
  --project my-project --region asia-northeast1 \
  --since 7d --top-n 20 --rank-by slot_ms --format json
```

主なオプション（`job` と共通のものに加えて）:

| オプション | 説明 |
|---|---|
| `--since` | 相対期間（例: `7d`） |
| `--from` / `--to` | 開始 / 終了日時（ISO8601） |
| `--top-n` | 上位 N 件（省略時は設定ファイルの既定値） |
| `--rank-by` | ランキング基準（`slot_ms` / `bytes_billed` / `elapsed`） |
| `--user` | `user_email` で絞り込む |
| `--min-slot-ms` | `total_slot_ms` の下限で絞り込む |

`--no-fallback` は `scan` では常にフォールバックしないため意味を持たない（後述の「必要な IAM」参照）。

### `drill` — TopN ジョブのフル診断

```bash
uv run bq-job-diagnose drill \
  --project my-project --region asia-northeast1 \
  --since 7d --top-n 10 --rank-by bytes_billed --format json
```

`scan` のオプションに加えて `--from-scan <path>`（保存済み `scan` JSON から GCP にアクセスせず再診断する）が使える。`--top-n` の上限は 50。

## 必要な IAM ロールと権限

- `roles/bigquery.user` + `roles/bigquery.resourceViewer`
- 実際に使われる権限: `bigquery.jobs.listAll`, `bigquery.jobs.create`

**INFORMATION_SCHEMA は 180 日で保持期限が切れる。** `job` コマンドは `created_on` を省略すると 7日 → 30日 → 180日と段階的に検索範囲を広げるが、180日を超えるジョブは見つからない。

**region 修飾子は必須。** BigQuery の region はテーブルパスに埋め込む識別子であり、SQL パラメータとして束縛できないため、CLI 側で `validate_region` により厳格に検証してから SQL に組み込む（大文字は拒否、`region-` プレフィックスは自動的に正規化）。

**`scan` は構造的に `bigquery.jobs.listAll` が必須であり、`jobs.get` へフォールバックしない。** `job` / `drill` の単一ジョブ取得は権限不足時に `jobs.get` へフォールバックできるが、期間内のジョブ一覧を取得する `scan` はその性質上 INFORMATION_SCHEMA 経由でしか実現できない（`jobs.get` は job_id 単位でしか取得できないため）。`bigquery.jobs.listAll` が無い場合、`scan` は権限エラー（終了コード 3）で失敗する。

## 閾値のカスタマイズ

`--config <path>` で閾値設定 YAML を差し替えられる。デフォルトは `src/bq_job_diagnose/default_thresholds.yaml`。

**単価（`pricing` セクション）は必ず自分の契約値で上書きすること。** デフォルト値は参考値であり、`pricing.as_of`（例: `"2026-09"`）で基準時点が明示されている。割引・コミットメントを含む実際の契約単価とは異なる。

```yaml
pricing:
  as_of: "2026-09"
  currency: USD
  on_demand_price_per_tib: 6.25
  editions_price_per_slot_hour:
    STANDARD: 0.04
    ENTERPRISE: 0.06
    ENTERPRISE_PLUS: 0.10
```

## 16 ルール一覧

| rule_id | 何を検出するか | 前提データ |
|---|---|---|
| `skew.compute_time` | ステージ内の計算時間の偏り（`compute_ms_max / compute_ms_avg`） | plan |
| `shuffle.spill` | ディスクへのスピル発生（ADVISORY・非決定的） | plan |
| `shuffle.large_output` | ステージ出力サイズの過大 | plan |
| `filter.low_efficiency` | 読み込み行数に対する出力行数の少なさ（フィルタ効率） | plan |
| `slot.starvation` | 実行可能スロットに対するスロット不足の兆候 | timeline（`estimated_runnable_units` が必要） |
| `slot.wait_dominant` | 実行時間に占める待機時間の支配 | timeline |
| `join.broadcast_large` | ブロードキャスト結合対象の過大 | plan |
| `join.shuffle_heavy` | シャッフル結合のコスト過大 | plan |
| `join.cardinality_explosion` | 結合後の行数の異常増加 | plan |
| `plan_shape.repartition_repeat` | REPARTITION ステップの繰り返し出現 | plan |
| `plan_shape.coalesce_repeat` | COALESCE ステップの繰り返し出現 | plan |
| `cost.on_demand_bytes` | オンデマンド課金でのスキャン量過大 | job（バイト数） |
| `cost.editions_slot_time` | Editions でのスロット時間消費過大 | job（スロット時間） |
| `cost.model_mismatch` | on-demand と Editions の試算コスト逆転の可能性（confidence: medium） | job |
| `job.error` | ジョブのエラー終了 | job |
| `job.resource_warning` | リソース警告 | job |

## 終了コード

| コード | 意味 |
|---|---|
| `0` | 正常終了（**findings が存在していても 0**） |
| `1` | 実行時エラー |
| `2` | 引数エラー |
| `3` | 認証・権限エラー |
| `4` | ジョブ未検出 |
| `10` | `--fail-on critical` / `--fail-on warning` 指定時、該当重大度以上の finding があった場合のみ |

## コスト推定

コストは **on-demand と Editions（Standard/Enterprise/Enterprise Plus）の両方が常に併記される。** 片方だけでは課金モデルの移行判断ができないため。

- on-demand: スキャンしたバイト数 × TiB 単価
- Editions: 消費スロット時間 × スロット時間単価

**Editions 側の試算はコミットメント割引を反映しない上限見積である。** 実際の契約でコミットメント割引を受けている場合、実コストはこの試算より低くなる。`cost.model_mismatch` finding の `confidence` が `medium` に固定されているのはこのためで、単発ジョブの試算からリザベーション設計を断定すべきではない（最終判断は `/bq-diagnose` Skill 側の推論に委ねる）。

## 開発向け

```bash
cd bq_job_diagnose
uv run pytest         # 全テスト（GCP にアクセスしない。FileCollector + フィクスチャで完結）
uv run ruff check src tests
```

レビュー観点は `REVIEW_GUIDE.md` にまとまっている。コードレビューを依頼する場合は `/bq-review` スキル（`.claude/skills/bq-review/SKILL.md`）を使うこと。

テストは `bigquery.Client` をモックせず、`FileCollector` と `tests/fixtures/` 配下のフィクスチャで INFORMATION_SCHEMA / jobs.get 双方のデータ形状を再現しており、GCP アクセスなしで完走する（Phase 0-9 の設計方針）。
