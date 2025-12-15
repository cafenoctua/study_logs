# 要件
- github actionsでdbt cliが実行可能になるようにdbt-coreの実行環境を作って
- ワークフローの最後に `dbt --version` を実行して
- google cloudへの認証をしてBigQueryへのアクセスを可能したい(利用する認証情報は、github secretsを使って以下のように設定している)
  - workload_identity_provider: `WIP_DBT`
  - service_account: `WIP_SA_DBT`