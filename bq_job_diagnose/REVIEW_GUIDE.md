# bq-job-diagnose レビューガイド

このプロジェクトのコードをレビューするとき、**何を最優先で見るか**をまとめたもの。
一般的なコードレビュー観点（命名・重複・テスト有無）ではなく、**このプロジェクト固有の、壊れやすく、壊れても静かに間違った結果を出す箇所**に絞っている。

対象: `bq_job_diagnose/`（CLI）と `.claude/skills/bq-diagnose/`（Skill）

---

## 0. このプロジェクトの構造的な主張

レビューの判断基準はすべてここから導かれる。

> **決定論で書ける部分は全てプログラムに落とし、判断が要る部分だけ LLM に渡す。
> その境界を「型」と「モジュール依存」で構造的に強制する。**

具体的には 3 つの不変条件がある。これを壊す変更は、動いていてもレビューで止める。

| # | 不変条件 | 壊れたときに起きること |
|---|---|---|
| I1 | `rules/` は `collect/` を import しない | ルールがデータソースで分岐し始め、片方の経路でしか正しくない診断が生まれる |
| I2 | `None`（取得不能）と `0`（値がゼロ）を混同しない | RLS 制限ジョブが「0 バイトスキャン」に見え、コスト集計が静かに狂う |
| I3 | CLI は観測事実のみ出力し、提案を書かない | 決定論と非決定論が混ざり、どこまでが検証済みの数字か誰にも分からなくなる |

---

## 1. 最優先レビュー観点

### 1.1 比率フィールドの誤用（最も危険）

**背景**: BigQuery の `compute_ratio_avg` / `compute_ratio_max` 等は、**クエリ全体で最も遅いワーカーの時間**を分母に正規化された値。ステージ内の偏りを表さない。

**防御**: `models.Stage` にこれらのフィールドを**意図的に持たせていない**。存在しなければ誤用できない。

**レビューで見ること**:
- [ ] `Stage` に `*_ratio_*` という名前のフィールドが追加されていないか
- [ ] `tests/test_models.py` の `Stage.__slots__` 回帰ガードが残っているか
- [ ] スキュー判定が `compute_ms_max / compute_ms_avg`（ミリ秒）で書かれているか

```python
# ✗ 却下。ratio はクエリ全体基準で、ステージ内偏りではない
if stage.compute_ratio_max > 0.9: ...

# ✓ 正しい
ratio = stage.compute_skew_ratio      # compute_ms_max / compute_ms_avg
if ratio is not None and ratio >= th.skew.ratio_critical: ...
```

**なぜ「コメントで注意書き」では不十分か**: ドキュメントを読んだ人でも誤解する種類の罠だから。型から消すのが唯一確実な防御。

---

### 1.2 `None` と `0` の混同

**背景**: BigQuery は「取得できなかった」と「値がゼロ」を同じ列で返す。

| 状況 | `total_bytes_billed` | 意味 |
|---|---|---|
| キャッシュヒット | `0` | 課金ゼロ（正常） |
| 行レベルアクセスポリシー | `None` | 取得不能（権限） |

**レビューで見ること**:
- [ ] `or 0` / `int(x or 0)` / `x if x else 0` のような**黙った既定値**がないか
- [ ] 新しい数値フィールドが `_as_int()` を通っているか（`int()` の直書き禁止）
- [ ] コスト計算で `amount=None`（試算不能）と `amount=0.0`（課金ゼロ）が区別されているか

```python
# ✗ 却下。RLS 制限ジョブが「0 バイト」になる
total = job.total_bytes_billed or 0

# ✓ 正しい。取得不能は伝播させる
if job.total_bytes_billed is None:
    return CostEstimate(amount=None, unavailable_reason="total_bytes_billed が取得できません")
```

**確認コマンド**:
```bash
grep -rn "or 0\b" src/ | grep -v test    # 黙った既定値の検出
```

---

### 1.3 `rules/` の依存方向

**レビューで見ること**:
- [ ] `rules/` 配下のどのモジュールも `collect` / `google` / `requests` を import していないか
- [ ] ルール関数の引数が `(Job, Thresholds)` のみか（`row` や `client` を受け取っていないか）
- [ ] `tests/test_rule_registry.py` の AST ベース import チェックが残っているか

```bash
grep -rnE "^\s*(from|import)\s+(bq_job_diagnose\.)?collect\b|^\s*(from|import)\s+google|requests" \
  src/bq_job_diagnose/rules/
# 何も出ないこと
```

**なぜ重要か**: Phase 5 のパリティテストが「INFORMATION_SCHEMA 経路と jobs.get 経路から同じ `Job` が出る」ことを証明している。その上でルールが `Job` しか見なければ、**ルールは自動的に両経路で正しい**。依存が漏れた瞬間この保証が消える。

---

### 1.4 ルールが提案を書いていないか（I3 の実体）

**レビューの唯一の判定基準**: `Finding.summary` に「〜すべき」「〜を検討してください」が入っていたら却下。

```python
# ✗ 却下。提案は Skill の仕事
summary="パーティション列でフィルタすべきです"

# ✓ 正しい。観測事実のみ
summary=(
    f"ステージ {stage.name} は {records_read:,} 行読み込み "
    f"{records_written:,} 行を出力（フィルタ効率 {eff:.2%}）"
)
```

**理由**: CLI が出す数字は検証済みの決定論的事実、Skill が出す提案は LLM の推論。混ぜると、ユーザーがどこまで信頼してよいか判断できなくなる。

---

### 1.5 SQL 生成

**レビューで見ること**:
- [ ] `creation_time >= @start_time` 相当のフィルタが**全ビルダー**にあるか（省くと 180 日分を全スキャン。BigQuery は強制しない）
- [ ] 識別子（project / region）が**必ずバリデータを通って**から f-string に入っているか
- [ ] ユーザー入力が生 SQL に連結されていないか（`rank_by` のような列名指定も Python 側の辞書で固定式にマップすること）
- [ ] `SELECT *` がないか（スキーマ変更で静かに壊れる）
- [ ] SQL 中の `@name` と返却パラメータが**双方向で一致**しているか

**SCRIPT 除外の非対称性**（意図的。統一してはいけない）:

| ビルダー | `statement_type != 'SCRIPT'` | 理由 |
|---|---|---|
| `build_scan_sql` | **あり** | 親は子の `total_slot_ms` を合算保持 → 二重計上 |
| `build_repeated_query_sql` | **あり** | 同上 |
| `build_job_sql` | **なし** | 親を明示指定されたら親として扱う |
| `build_children_sql` | **なし** | 子の列挙が目的 |

---

### 1.6 `skipped_rules` を潰していないか

**背景**: 「問題が検出されなかった」と「評価できなかった」の混同は、診断ツール最大の失敗モード。

**レビューで見ること**:
- [ ] ルールが例外を投げたとき、握りつぶさず `SkippedRule` になるか
- [ ] skip 理由が**具体的な原因**を含むか（実装済みの文字列は以下）

```
プランが利用できません (cache_hit)
タイムラインが利用できません (timeline が空です)
ルール実行中に例外が発生しました: RuntimeError: 想定外の値
```

- [ ] `--disable-rules` で除外したルールが `skipped_rules` に**入っていない**か
  （前提未達 = 評価不能、ユーザーが切った = 意図的。混ぜると本当の「評価不能」が埋もれる）
- [ ] レポート（JSON / Markdown）に `skipped_rules` が出力されているか

---

### 1.7 コスト推定

- [ ] on-demand と Editions の**両方**が常に試算されているか（片方だけではモデル移行を判断できない）
- [ ] 単価が YAML から読まれているか（ハードコード禁止。地域・契約で変わる）
- [ ] `CostEstimate` に `basis_value` / `basis_unit` / `price_ref` が残っているか
      → **試算額より「何にどの単価を掛けたか」のほうが寿命が長い**。これが無いと単価が古いことに誰も気づけない
- [ ] Editions 試算が「コミットメント割引を反映しない上限見積」と明記されているか
- [ ] `cost.model_mismatch` の `confidence` が `medium` 以下か
      （単発ジョブの試算からリザベーション設計を語るのは飛躍。最終判断は Skill 側）

---

## 2. テストのレビュー

### 2.1 「緑であること」は品質の証明にならない

**必ず確認すること**: そのテストは**落ちうるか**。

```bash
# 例: パリティテストが本当に比較しているかの確認手順
# 1. フィクスチャを 1 フィールドだけ意図的に壊す
# 2. 該当テストが FAIL することを確認
# 3. 復元して緑に戻す
```

除外セットが広すぎて何も比較していないテストは、緑でも無価値。

### 2.2 除外セットは 2 種類を混ぜない

`SDK_UNAVAILABLE_JOB_FIELDS` のような除外リストには、性質の違う 2 つが混入しうる。

| 種類 | 例 | 扱い |
|---|---|---|
| 構造的に取得不可能 | `resource_warning`（INFORMATION_SCHEMA 専用列） | 恒久的に正しい除外 |
| **実装していないだけ** | かつての `dml_statistics` | **バグの隠蔽**。実装して除外から外す |

**見分け方**: REST API にそのフィールドが実在するか確認する。実在するなら実装漏れ。

- [ ] 除外セットの各エントリに「なぜ取得できないか」の理由が書かれているか
- [ ] 除外セット内の名前が実在するフィールド名であることを検証するテストがあるか（typo で除外が静かに広がるのを防ぐ）

### 2.3 やらないテスト

- [ ] `bigquery.Client` をモックして「呼ばれたこと」を検証していないか
      → モックの振る舞いのテストであって価値がない。`FileCollector` + フィクスチャで実データ形状を通すこと
- [ ] テストが GCP にアクセスしていないか（Phase 0-9 は認証なしで完走できる設計）

### 2.4 フィクスチャ

- [ ] 匿名化されているか（`user_email` / `project_id` / `query` / `referenced_tables` / `labels`）
      → 学習リポジトリで公開 PR を出す以上、必須
- [ ] エッジケースが揃っているか

| フィクスチャ | 検証する罠 |
|---|---|
| `leaf_no_input_stages` | `input_stages` **キー自体が存在しない**（空配列ではない） |
| `cache_hit` | プランなしが正常終了する（エラーではない） |
| `rls_masked` | `job_stages` 空 + バイト数 `None` → `RESTRICTED` |
| `script_parent` | 上と**列の形が同じ**だが `statement_type` で切り分け → `NOT_AVAILABLE` |
| `skewed_join` | int64 が JSON 文字列で届く |
| `spill_heavy` | 大きな数値、`spilled > 0` |

---

## 3. Skill（`.claude/skills/bq-diagnose/SKILL.md`）のレビュー

### 3.1 決定論と非決定論の境界が明記されているか

SKILL.md の手順には、**どこまでが CLI の事実でどこからが LLM の推論か**を示す境界線が必要。

- [ ] Step 3（findings を読む）と Step 4（改善案を組み立てる）の間に境界が明示されているか
- [ ] 「CLI が出した数字を Skill が改変しない」と書かれているか
- [ ] 「Skill の提案を CLI の findings と混ぜて提示しない」と書かれているか

### 3.2 `skipped_rules` の扱い

- [ ] 評価できなかった観点をユーザーに明示する手順があるか
      → 特に jobs.get フォールバック時は `slot.starvation` が**構造的に評価不能**になる。
        これを黙っていると「スロット競合は問題なし」という嘘になる

### 3.3 description の書き方

`.claude/skills/rag-log/SKILL.md` 等と同じ形式に揃える。

- [ ] YAML frontmatter の `description` が**日本語**で、発火条件を具体的に列挙しているか
      （「/bq-diagnose が呼ばれたとき、または『このクエリが遅い』『スロット消費が多い』と言われたとき」のような形）
- [ ] 手順が `## 手順` → `### Step N:` の構成になっているか

### 3.4 Learning モード規約

- [ ] ファイル編集前にユーザーへ確認を求める手順が含まれているか
      （このリポジトリの `CLAUDE.md` の規約。Skill 内でも守る必要がある）

---

## 4. レビュー実施手順

```bash
cd bq_job_diagnose

# 1. 全テストが緑か
uv run pytest -q

# 2. lint
uv run ruff check src tests

# 3. 依存方向（何も出力されないこと）
grep -rnE "^\s*(from|import)\s+(bq_job_diagnose\.)?collect\b|^\s*(from|import)\s+google|requests" \
  src/bq_job_diagnose/rules/

# 4. 黙った既定値の検出（ヒットしたら 1 件ずつ意図を確認）
grep -rn "or 0\b" src/ | grep -v test

# 5. SELECT * の検出（何も出ないこと）
grep -rn "SELECT \*" src/ | grep -vE ":\s*#"   # コメント行を除外

# 6. 生成 SQL の目視確認
uv run bq-job-diagnose job <ID> --project <P> --region <R> --dry-run-sql
```

---

## 5. レビューの姿勢

- **指摘には必ず根拠を添える。** BigQuery 公式ドキュメントの記述、または上記の不変条件 I1-I3 のどれに違反するかを示す
- **良い点も言及する。** 特に「誤用できない設計」（型から消す、依存を切る）になっている箇所
- **Learning モードのため、コード変更は提示のみ。** 適用はユーザーの確認後
- **「動いているから良い」で通さない。** このプロジェクトの失敗モードは「動くが静かに間違った数字を出す」であり、テストの緑とは独立している

---

## 付録: 判断に迷ったときの問い

1. この変更で、**同じジョブを別経路で取得したときに違う診断結果**になりうるか？ → なるなら I1 違反
2. この数値が `None` のとき、`0` として扱われる経路はあるか？ → あるなら I2 違反
3. この文章は**観測した事実**か、それとも**推論・提案**か？ → 後者が CLI 側にあれば I3 違反
4. このテストは**落ちうる**か？ → 落ちないなら検証していない
5. この除外は**構造的に不可能**だからか、それとも**まだ実装していない**からか？ → 後者ならバグの隠蔽
