import pandas as pd

# CSVファイルの読み込み（ファイルパスは適宜変更してください）
df = pd.read_csv("/Users/wangzhende/intern/DBform/dbform_test.csv")

# 1行目（ヘッダー）の列名を取得して表形式で表示
columns_info = pd.DataFrame({
    "列番号": range(1, len(df.columns) + 1),
    "列名": df.columns
})

print(columns_info)

from datetime import datetime

# タイムスタンプ付きのファイル名を作成
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# UTF-8エンコーディングでCSVファイルを保存（BOM付き）
output_path_utf8 = f"/Users/wangzhende/intern/DBform/column_headers_info_{timestamp}_utf8.csv"
columns_info.to_csv(output_path_utf8, index=False, encoding='utf-8-sig')

output_path_utf8
