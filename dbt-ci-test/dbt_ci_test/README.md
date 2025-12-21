# CI検討

## targetの工夫も取り入れたい
target ciに統一されると複数のPRがあると処理が競合する

## 軽量なdbt unit test
```
dbt test --select state:modified+ --test_type unit \
  --target ci \
  --exclude package:dbt_project_evaluator
```

## 軽量なdbt build と data test
```
dbt build --select state:modified+ \
  --defer --state ./prod-manifest \
  --target ci \
  --exclude package:dbt_project_evaluator
```
を使って差分のみかつ元データはすでに実装されているものを参照した動作確認を構築できる

prod-manifestの生成は、`dbt parse -t prod` で可能なため前段で実行してmanifest.jsonを作ってから上記コマンドを実行すると良い

## dbt evaluatorを使った構造解析
https://github.com/dbt-labs/dbt-project-evaluator

以下の様なコマンドの実行で良さそう
```
dbt build --select package:dbt_project_evaluator
```

CIの実行でエラーでは無く警告表示のほうが表現上良さそなため以下のような設定をすると良い
```yaml
data_tests:
  dbt_project_evaluator:
    +severity: "{{ env_var('DBT_PROJECT_EVALUATOR_SEVERITY', 'warn') }}"
```

また、実行環境に応じて実行するかの設定をできるため以下を設定しておくとよい
```yaml
models:
  dbt_project_evaluator:
    +enabled: "{{ env_var('DBT_PROJECT_EVALUATOR_ENABLED', 'true') | lower == 'true' | as_bool }}"
```

`DBT_PROJECT_EVALUATOR_ENABLED` という環境変数に応じて実行するかを決定できる

参考文献
- https://docs.getdbt.com/guides/set-up-ci?step=3
- https://dbt-labs.github.io/dbt-project-evaluator/latest/ci-check/#2-run-this-package-for-each-pull-request



## SDF lintを使ったリンター
参考文献
- https://www.getdbt.com/blog/1000x-faster-sql-linting

既存のdbt project上で使えることを確認

以下の手順で使える

1. インストール
```
curl -LSfs https://cdn.sdf.com/releases/download/install.sh | sh -s
```

2. sdfコマンドで初期化
```
sdf init
```
3. workspace.sdf.ymlを以下のように設定するとmodels以下を対象にリンター・フォーマッターを実行する
```yaml
workspace:
  edition: '1.3'
  name: dbt_ci_test
  description: dbt ci test
  includes:
    - path: models
  defaults:
    dialect: bigquery
    preprocessor: jinja

---
  # This the default lint configuration
  sdf-args:
    lint: >
      -w capitalization-keywords=consistent
      -w capitalization-literals=consistent
      -w capitalization-types=consistent
      -w capitalization-functions=consistent
      -w references-quoting
      -w structure-else-null
      -w structure-unused-cte
      -w structure-distinct
```

⚠️: jinja関数をエラーと認識してしまうため解決方法しりたひ
この解決方法は、以下の通り
結論                                                                                                                                                                                                          

SDF1501マクロエラーをlintから除外する設定は存在しません。                                                                                                                                                     

ただし、カスタムマクロを定義することで解決できます。                                                                                                                                                          

対処方法: ダミーのrefマクロを作成                                                                                                                                                                             

1. macros/ref.jinjaを作成:                                                                                                                                                                                    
```sql
{%- macro ref(model_name) -%}                                                                                                                                                                                 
{{ model_name }}                                                                                                                                                                                              
{%- endmacro -%}                                                                                                                                                                                              
```

2. workspace.sdf.ymlにマクロディレクトリを追加:                                                                                                                                                               
```yaml
includes:                                                                                                                                                                                                     
  - path: models                                                                                                                                                                                              
  - path: macros                                                                                                                                                                                              
    type: macro                                                                                                                                                                                               
```

これにより、SDFがdbtのrefマクロを認識し、lintがエラーなく通ります。                                                                                                                                           

注意点                                                                                                                                                                                                        
- このダミーマクロはlint用です。実際のdbt実行時はdbt本体のrefが使われます                                                                                                                                     
- sourceやconfigなど他のdbtマクロも使っている場合は、同様にダミーマクロを追加してください   