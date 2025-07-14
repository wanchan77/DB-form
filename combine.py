import pandas as pd
from datetime import datetime

# ファイル名
main_file = "/Users/wangzhende/intern/DBform/DB_20250602.csv"
additional_file = "/Users/wangzhende/intern/DBform/csv/DB_20250605_163947.csv"

# タイムスタンプ付き出力ファイル名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"DB_{timestamp}.csv"

# メインファイル読み込み（ヘッダーあり）
df_main = pd.read_csv(main_file, encoding='utf-8')

# 追加ファイル読み込み（2行目から、ヘッダーなし）
df_additional = pd.read_csv(additional_file, header=None, skiprows=1, encoding='utf-8')

# 列数と行数のチェック
main_cols, main_rows = df_main.shape[1], df_main.shape[0]
add_cols, add_rows = df_additional.shape[1], df_additional.shape[0]

print("=== ファイル構造チェック ===")
print(f"main.file: {main_cols}列, {main_rows}行（ヘッダー除く）")
print(f"additional.file: {add_cols}列, {add_rows}行（2行目以降）")

# 列数不一致ならエラーを出す
if main_cols != add_cols:
    raise ValueError(f"列数が一致しないため結合できません：main({main_cols}列), additional({add_cols}列)")

# 1列目からデータが入っているかチェック（全列NaNの行を削除）
df_additional = df_additional.dropna(how='all')

# df_mainの列名をdf_additionalに適用
df_additional.columns = df_main.columns

# 結合
df_merged = pd.concat([df_main, df_additional], ignore_index=True)

# UTF-8で保存（BOMなし）
df_merged.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n✅ 結合完了: {output_file}")
print(f"出力行数: {df_merged.shape[0]}行")

