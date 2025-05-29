import pandas as pd
import sys

# CSV を読み込む（パスは適宜合わせてください）
df = pd.read_csv('/Users/wangzhende/intern/DBform/DB_20250425_confirmed.csv', low_memory=False)

# 列番号を取得
ev_col_idx   = df.columns.get_loc('electric_vehicle')
elec_col_idx = df.columns.get_loc('electricity')

# equip_indices / fuel_indices の定義
equip_indices = list(range(93, 200))   # CP(94列目=0起点93)～GR(200列目=0起点199)
fuel_indices  = list(range(200, 232))  # GS(201列目=0起点200)～HW(231列目=0起点230)＋electricity(232列目=0起点231)

# 結果を出力
print("▶ equip_indices 範囲:", equip_indices[0], "~", equip_indices[-1], flush=True)
print("▶ electric_vehicle の列番号:", ev_col_idx,     flush=True)
print("▶ fuel_indices 範囲:",  fuel_indices[0],  "~", fuel_indices[-1],  flush=True)
print("▶ electricity の列番号:",   elec_col_idx,   flush=True)

# ここで終了させる
sys.exit(0)
