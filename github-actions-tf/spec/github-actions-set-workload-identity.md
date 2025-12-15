# 要件
- リソース作成にterraformを利用
- 作成するクラウドプロバイダー先
  - google cloud
- google cloud project: `sweepsump`
- 作成するリソース
  - workladidentity pool
    - 紐づけ先リポジトリ: cafenoctua/study_logs
    - 紐づけサービスアカウント: ここで作成するサービスアカウント
  - service account
    - サービスアカウント名: dbt-actions
    - 付与するrole
      - BigQuery Admin

## terraform開発規約
禁止処理
- `terraform apply`

利用するバージョン
- terraform 1.14.2

以下の手順で開発を進めること
1. リソース作成に必要なディレクトリを作成
2. ディレクトリ移動して以下ファイルを作成
   - provider.tf
   - versions.tf
   - locals.tf
3. `terraform init` で初期化
4. 要件にあるリソース作成
5. `terraform validation` で有効性を確認
6. `terraform plan` が成功するか確認
   1. 失敗する場合は、エラー解消するまで修正を繰り返す
