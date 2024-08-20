#!/bin/bash

# GCSのプリフィックスを事前に入力します
GCS_PREFIX="gs://tpch_sf10_dbtvault_test"

# schemaディレクトリ内のすべてのファイル名を取得します
SCHEMA_DIR="./schema"
SCHEMA_FILES=$(ls $SCHEMA_DIR)

# スキーマファイルごとにGCSのURIを作成し、gsutilコマンドを使ってBigQueryにデータをロードします
for FILE in $SCHEMA_FILES; do
    SCHEMA_FILE_PATH="$SCHEMA_DIR/$FILE"
    GCS_URI="$GCS_PREFIX/${FILE%.json}.csv"

    # GCSにファイルをアップロード
    # gsutil cp $SCHEMA_FILE_PATH $GCS_URI

    # GCS URIからBigQueryにデータをロード（例：ロードするBQのテーブル名はファイル名から生成）
    TABLE_NAME="${FILE%.json}" # 例えばファイルが.jsonで終わる場合のテーブル名生成
    bq load \
        --source_format=CSV \
        --autodetect=true \
        --replace=true \
        --skip_leading_rows=1 \
        tpch_sf10.$TABLE_NAME $GCS_URI
done
