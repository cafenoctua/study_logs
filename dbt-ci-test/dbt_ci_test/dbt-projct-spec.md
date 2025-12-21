# プロジェクト概要
このプロジェクトでは、dbtのCIを探求することを目的としています
その中でdbtが持つテスト機能、外部ツール、パッケージによるリンターフォーマッター、プロジェクト構成の違反を活用した堅牢なCI構成を検討するためにテストプロジェクトと実際に動くCIを作ります

## 実行基盤
### dbt project構成
- 利用するdbt engine: dbt-core
- DWH: BigQuery

#### profile構成
- dev: ローカル開発で利用して、書き込み先データセットを環境変数または、その他の方法で制御できるようにしてほしい
- ci: github actionsで利用して、これもdev同様に書き込み先データセットを変更できるようになっている
- prod: 本番環境でgoogle cloudリソースを使って実行される、書き込み先データセットは固定されている

### CIの実行基盤
- github actions

## 利用するソースデータ
- `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`

## dbt　projectで作るデータパイプライン
`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` をソースデータとして、以下のようなディメンジョナルモデリングされたパイプラインを作ります

すべてのテーブルの粒度は、日付に丸めてください

### dimension
- ユーザー情報
  - ユーザーID
  - ユーザーの初回アクセス日時
- 利用デバイス
- アクセスした地域
- アプリケーション情報

### fact
- 各日の合計利用時間
- 各日の合計アクセス数
- 当日までのLTV

## CIについて
下記全てのCIは独立して実行されるように構成を取ります
また、全てのCIがworkflow dispatchによる手動トリガーに対応していること
workflow dispatchには適宜必要なパラメーター設定が可能な状態にしてください

### テスト戦略
基本戦略として、変更の入ったモデルとその下流のモデルだけ動作確認とデータテスト、ユニットテストを行います
変更の上流のモデルの参照先は、`defer`を活用して本番環境の上流モデルを参照するようにしている

deferのための本番環境のmanifest.jsonは `dbt parse` で本番環境をパースした結果から生成してそのmanifest.jsonをprod_stateディレクトリにあるmanifest.jsonを都度上書きして配置してください

これら結果を以下の形式にして該当するPRコメントに残すようにしている
dbt build実行結果
- model実行の成功数、失敗数、失敗したモデル名
- data test実行の成功数、失敗数、失敗したテストの詳細
- unit test実行の成功数、失敗数、失敗したテストの詳細

詳細については、githubのコメント機能でdetailを使ってスリムに表示してください

### リンター・フォーマッター
SDF Lintを活用したリンター・フォーマッターを実行します
フォーマッターで修正しつつそれでもリンターで違反する箇所をまとめた内容を該当するPRコメントとして返して
リンターの指摘がなければ全て成功した旨をPRに返して

### プロジェクト構成違反
dbt-project-evaluatorを活用して構成違反を検知してください
検知した結果で違反しているものの詳細はPRコメントとして返してください
成功した場合もその旨をPRコメントとして返してください

構成の詳細は、以下ドキュメントを参照してください
- [dbt-project-evaluator-in-ci](./dbt-project-evaluator-in-ci.md)
- [dbt-project-evaluators-selectors-design](./dbt-project-evaluators-selectors-design.md)

## dbtの実行方法
[dbt-project-setting-vs-selectors](./dbt-project-setting-vs-selectors.md)を元にプロジェクト構成とselectors.ymlを設定してください

