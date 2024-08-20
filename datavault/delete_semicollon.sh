#!/bin/bash

# ディレクトリを指定
# TARGET_DIR="./schema"

# ディレクトリ内のすべての.csvファイルを取得
CSV_FILES=~/Downloads/order.csv

# 各.csvファイルの中のセミコロンを削除
for FILE in $CSV_FILES; do
    # 一時ファイルにセミコロンを削除した内容を書き込む
    sed 's/;//g' "$FILE" > "${FILE}.tmp"
    
    # 元のファイルをバックアップし、一時ファイルを元のファイル名にリネーム
    mv "$FILE" "${FILE}.bak"
    mv "${FILE}.tmp" "$FILE"
done

echo "セミコロンの削除が完了しました。元のファイルは.bakとしてバックアップされています。"
