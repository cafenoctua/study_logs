---
name: bq-diagnose
description: bq-job-diagnose CLI の出力（決定論的な診断事実）を読み、BigQuery ジョブの性能改善案を組み立てる。/bq-diagnose が呼ばれたとき、または「このクエリが遅い」「スロット消費が多い」「BigQuery のジョブを調べて」「クエリのコストを下げたい」「このジョブ ID を診断して」「直近のジョブで重いものを教えて」と言われたときに必ず使う。CLI の findings をそのまま貼り付けるだけの場面や、改善提案を求められていない場面では使わない。
---

# bq-diagnose: BigQuery ジョブ性能診断

`bq-job-diagnose` CLI が出す決定論的な診断事実（findings）を読み、そこから改善案を組み立てる。
CLI 自体はコード変更提案を一切書かない（`REVIEW_GUIDE.md` の不変条件 I3）。**その提案を書くのがこの Skill の役目。**

## 手順

### Step 1: 入力モードを判定する

ユーザーの依頼から、CLI のどのサブコマンドを使うかを決める。

| ユーザーの依頼 | モード | コマンド |
|---|---|---|
| Job ID が分かっている（「このジョブを調べて」「job_id: xxx」） | 単一ジョブの深掘り | `job` |
| 期間で重いジョブを一覧したい（「直近7日で重いクエリは？」「コストが高いジョブ一覧」） | 期間スキャン | `scan` |
| 期間内の重いジョブそれぞれをフル診断したい（「上位のジョブを全部診断して」） | スキャン＋フル診断 | `drill` |

どれか判断がつかない場合は、ユーザーに Job ID の有無・対象期間を確認する。

### Step 2: CLI を実行して JSON を得る

`--format json` を必ず指定する。project / region はユーザーに確認するか、既知の値を使う。

```bash
# job モード（単一ジョブ）
uv run --project <repo>/bq_job_diagnose bq-job-diagnose job <JOB_ID> \
  --project <PROJECT_ID> --region <REGION> --format json

# scan モード（期間で TopN 一覧。plan が必要なルールは評価対象外）
uv run --project <repo>/bq_job_diagnose bq-job-diagnose scan \
  --project <PROJECT_ID> --region <REGION> --since 7d --format json

# drill モード（TopN それぞれをフル診断）
uv run --project <repo>/bq_job_diagnose bq-job-diagnose drill \
  --project <PROJECT_ID> --region <REGION> --since 7d --top-n 10 --format json
```

**注意（重要）**: 終了コードは `0` が正常終了であり、**findings が存在していても `0` のままである**。
`--fail-on critical` 等を明示的に指定しない限り、findings があることを実行失敗として扱わないこと。
（exit code: `0`=正常, `1`=実行時エラー, `2`=引数エラー, `3`=認証/権限エラー, `4`=ジョブ未検出, `10`=`--fail-on` 指定時のみ）

権限エラー（exit 3）が出た場合は、`roles/bigquery.user` + `roles/bigquery.resourceViewer`
（`bigquery.jobs.listAll` / `bigquery.jobs.create`）が付与されているか確認するようユーザーに伝える。
`scan` は構造的に `bigquery.jobs.listAll` が必須であり、`jobs.get` へのフォールバックは行われない。

### Step 3: findings を読む（ここまでが決定論）

JSON の構造:

```
schema_version, generated_at, config_digest, mode, jobs[], scan_summary
```

各 `jobs[]` エントリ:

```
job          # Job の全フィールド（クエリ本文・プラン・タイムライン・コストの元データ）
cost         # on-demand と Editions 両方の試算（常に両方出力される）
findings[]   # rule_id ごとの検出結果（決定論的事実。CLI が計算済み）
skipped_rules[]  # 前提条件が満たせず評価できなかったルールとその理由
```

`findings[].summary` / `evidence` はすべて CLI が計算した観測事実であり、提案文ではない。
（`REVIEW_GUIDE.md` 1.4: ルールが「〜すべき」のような提案を書いていたらそれ自体がバグ）

---

## ▼▼▼ 決定論と非決定論の境界 ▼▼▼

- **Step 3 までに読んだ数字（findings / cost / skipped_rules）は検証済みの決定論的事実である。Skill はこれを改変しない。** 数値を丸めたり言い換えたりせず、CLI が出した値をそのまま引用すること。
- **Step 4 以降はすべて LLM の推論である。CLI の findings と同じ書式・同じ強さの断定で混ぜて提示しないこと。** ユーザーがどこまで CLI 由来で検証済みか、どこから先が推論かを常に判別できるようにする。提案は必ず「CLI の検出結果」セクションと分けて「改善案の検討（推論）」のようなセクションに置く。

---

### Step 4: rule_id ごとに改善案を組み立てる（ここからが非決定論）

`findings` に出現した `rule_id` ごとに、以下の観点で改善案を検討する。16 種類すべてに対応する。

#### skew（スキュー系）

- **`skew.compute_time`** — 特定ステージの計算時間が偏っている（`compute_ms_max / compute_ms_avg` によるミリ秒ベースの判定）。クエリ本文を読み、JOIN / GROUP BY のキー分布を疑う。偏ったキーの事前集約、`APPROX_COUNT_DISTINCT` 等の `APPROX_` 系への置換、キー再設計（ソルティング等）を検討材料として提示する。

#### shuffle（シャッフル系）

- **`shuffle.spill`** — ディスクへのスピルが発生。**ADVISORY であり非決定的**である旨を必ず添える。同じクエリでも実行のたびに発生有無が変わりうるため、単発ジョブの spill 検出だけでクエリ構造の欠陥と断定しないこと。繰り返し発生する場合のみ、中間結果のサイズ削減（早期フィルタ・列の絞り込み）を検討材料とする。
- **`shuffle.large_output`** — ステージの出力が大きい。後続ステージへの不要な列の持ち越しがないか、集約を早められないかを検討する。

#### filter（フィルタ効率）

- **`filter.low_efficiency`** — 読み込み行数に対して出力行数が少ない（フィルタ効率が低い）。`job.referenced_tables` のスキーマを確認し、パーティション列・クラスタリング列の設計と述語プッシュダウン（`WHERE` 句がパーティション列に効いているか）を検討する。

#### slot（スロット系）

- **`slot.starvation`** — 実行可能なスロットに対してジョブが使えているスロットが不足している兆候。並列実行中の他ジョブとの競合、リザベーションの容量設計を検討材料とする。**`estimated_runnable_units` が取得できるデータソース（INFORMATION_SCHEMA 経路）でのみ評価可能**な点に注意（Step 5 参照）。
- **`slot.wait_dominant`** — 実行時間のうち待機時間が支配的。スロット競合・同時実行数の調整を検討する。

#### join（結合系）

- **`join.broadcast_large`** — ブロードキャスト結合の対象が大きい。結合順序の変更、事前フィルタでの縮小、明示的な `JOIN` ヒントの見直しを検討する。
- **`join.shuffle_heavy`** — シャッフル結合のコストが大きい。結合キーの分布、事前集約の可否を検討する。
- **`join.cardinality_explosion`** — 結合後の行数が異常に増加。結合条件の多重マッチ（意図しない多対多）を疑い、キーの一意性を確認するよう提案する。

#### plan_shape（プラン形状）

- **`plan_shape.repartition_repeat`** — REPARTITION ステップが複数ステージに繰り返し出現。BigQuery 公式ドキュメントの記述どおり、単発なら問題ないが繰り返しはデータ分布の不安定さやシャッフル過多の兆候。クエリ構造の見直し（中間結果の粒度）を検討材料とする。
- **`plan_shape.coalesce_repeat`** — COALESCE ステップの繰り返し出現。同上の観点で検討する。

#### cost（コスト系）

- **`cost.on_demand_bytes`** — オンデマンド課金でのスキャン量が大きい。パーティション/クラスタリングによるスキャン削減、`SELECT *` の見直しを検討する。
- **`cost.editions_slot_time`** — Editions（Standard/Enterprise/Enterprise Plus）でのスロット時間消費が大きい。クエリの並列度・実行時間の削減を検討する。
- **`cost.model_mismatch`** — on-demand と Editions の試算コストが逆転している可能性。**`confidence` が medium であることを明示し、単発ジョブの試算からリザベーション設計を断定しないこと。** 課金モデルの切り替えは、複数ジョブ・複数日の集計傾向を見てから判断すべき事項であり、この finding 単体は「検討のきっかけ」に留める。Editions 側の試算は**コミットメント割引を反映しない上限見積**であることも必ず添える。

#### job（ジョブ状態）

- **`job.error`** — ジョブがエラー終了。エラーメッセージの内容に応じた原因調査（構文・権限・リソース制限）を提案する。
- **`job.resource_warning`** — リソース警告（メモリ超過の兆候等）。クエリの中間結果サイズの見直しを検討する。

### Step 5: skipped_rules を確認し、評価できなかった観点を明示する

`skipped_rules` に列挙されたルールは「問題なし」ではなく「**評価できなかった**」ことを意味する。
これを「no finding」と混同して「問題なし」と報告してはならない（`REVIEW_GUIDE.md` 1.6 の最重要ポイント）。

特に **`jobs.get` 経路（`--no-fallback` を使わずフォールバックした場合、または `job.source` が jobs_api）では `slot.starvation` が構造的に評価不能になる。** この場合、ユーザーへの報告には必ず次のように明示する。

> 「このジョブは jobs.get 経由で取得されたため、スロット競合（slot.starvation）は評価できませんでした。スロット競合の有無を確認したい場合は INFORMATION_SCHEMA 経路（`bigquery.jobs.listAll` 権限）での再診断が必要です。」

「スロット競合は問題なし」という誤った言い方は絶対にしないこと。

### Step 6: 提案をコードブロックで提示し、適用はユーザーの確認後

このリポジトリは Learning モードで動作している（`CLAUDE.md` 規約）。
クエリの書き換え案・設定変更案は必ずコードブロックで提示し、「この変更を適用しますか？」と確認してから実行する。
ユーザーが「適用して」「やって」と明示的に指示するまで、実際のクエリやファイルは変更しない。

## 報告の型

```
## CLI の検出結果（決定論・検証済み）
- <rule_id>: <CLI の summary をそのまま引用>
- ...
（skipped_rules があれば、ここで「評価できなかった観点」として明示）

## 改善案の検討（推論・LLM 判断）
### <rule_id>
<検討材料・提案。confidence の断り書きが必要なものは明示>

```sql
-- 提案するクエリ変更（あれば）
```

この変更を適用しますか？
```
