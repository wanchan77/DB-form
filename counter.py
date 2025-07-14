import pandas as pd
from datetime import datetime
import os

# ── 1. CSV読み込み ─────────────────────────────────────────
df = pd.read_csv(
    '/Users/wangzhende/intern/DBform/DB_20250602_104225.csv',
    low_memory=False
)

# ── 2. 列番号(0起点)指定 ─────────────────────────────────
equip_indices = list(range(93, 200))
fuel_indices  = list(range(200, 234))

# ── 3. フラグ列を強制的に int 化 ─────────────────────────────
flag_idxs = equip_indices + fuel_indices
df.iloc[:, flag_idxs] = (
    df.iloc[:, flag_idxs]
      .apply(pd.to_numeric, errors='coerce')
      .fillna(0)
      .astype(int)
)

# ── 4. その他の列インデックス取得 ───────────────────────────
id_idx    = df.columns.get_loc('施策ユニークNo')
name_idx  = df.columns.get_loc('施策名')
bv_idx    = df.columns.get_loc('設備更新カウンタ')
m_idx     = 12
n_idx     = m_idx + 1
c_idx     = 2  # GHG削減量（ton-CO2）の列（C列）

# ── 5. デバッグ：列番号確認 ─────────────────────────────────
ev_col_idx   = df.columns.get_loc('electric_vehicle')
elec_col_idx = df.columns.get_loc('electricity')
print("▶ equip_indices 範囲:", equip_indices[0], "~", equip_indices[-1])
print("▶ electric_vehicle の列番号:", ev_col_idx)
print("▶ fuel_indices 範囲:",  fuel_indices[0],  "~", fuel_indices[-1])
print("▶ electricity の列番号:",   elec_col_idx)

# ── 6. エラーチェック：マスク行数 ─────────────────────────────
TARGET_LABEL = "対象設備の中で施策を実施する設備の割合"
base_mask = (
    (df.iloc[:, bv_idx] == 1) &
    (df.iloc[:, m_idx] == TARGET_LABEL) &
    (df.iloc[:, c_idx].notna())  # GHG削減量が空欄でない
)
print(f"エラーチェック: BV=1かつMラベル'{TARGET_LABEL}'かつGHG削減量ありの行数 = {base_mask.sum()}件")

# ── 7. フィルター前 全レコード展開 ───────────────────────────
records_all = []
for idx, row in df.iterrows():
    for ei in equip_indices:
        if row.iloc[ei] == 1:
            for fi in fuel_indices:
                if row.iloc[fi] == 1:
                    records_all.append({
                        'equipment': df.columns[ei],
                        'fuel':      df.columns[fi],
                        'N':         row.iloc[n_idx],
                    })
exploded_all = pd.DataFrame(records_all)
pre_summary = (
    exploded_all
    .groupby(['equipment','fuel'])
    .agg(count_all=('N','size'), sum_N_all=('N','sum'))
    .reset_index()
)

# ── 8. フィルター後(BV＆M＆GHGあり) レコード展開 ───────────────────────
records = []
for idx, row in df.iterrows():
    if not base_mask[idx]:
        continue
    for ei in equip_indices:
        if row.iloc[ei] == 1:
            for fi in fuel_indices:
                if row.iloc[fi] == 1:
                    records.append({
                        'row_number': idx + 2,
                        'equipment':  df.columns[ei],
                        'fuel':       df.columns[fi],
                        'ID':         row.iloc[id_idx],
                        '施策名':     row.iloc[name_idx],
                        'M':          row.iloc[m_idx],
                        'N':          row.iloc[n_idx],
                    })
exploded = pd.DataFrame(records)

# ── 9. フィルター後サマリ & 詳細抽出 ─────────────────────────
summary = (
    exploded
    .groupby(['equipment','fuel'])
    .agg(count=('N','size'), sum_N=('N','sum'))
    .reset_index()
)
overflow_summary = summary[summary['sum_N'] > 100][['equipment','fuel','count','sum_N']]
details = exploded.merge(
    overflow_summary[['equipment','fuel']],
    on=['equipment','fuel'],
    how='inner'
)

# ── 10. デバッグ：展開後レコード数の確認 ─────────────────────
print(f"② 展開後レコード数        = {len(exploded)}件")
print(f"③ summary.count 合計      = {summary['count'].sum()}件")

# ── 11. デバッグ：展開漏れ行の確認 ─────────────────────────
no_combo = base_mask & (
    (df.iloc[:, equip_indices].sum(axis=1) == 0) |
    (df.iloc[:, fuel_indices].sum(axis=1) == 0)
)
print("equip×fuelペアがないマスク行数:", no_combo.sum())
print(df.loc[no_combo, ['施策ユニークNo','施策名']])

# ── 12. Excel出力 ─────────────────────────────────────────
ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
out_file = f"output_{ts}.xlsx"
cwd      = os.getcwd()
out_path = os.path.join(cwd, out_file)

with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
    pre_summary.to_excel(writer,       sheet_name='pre_filter_summary', index=False)
    summary.to_excel(writer,           sheet_name='summary',             index=False)
    overflow_summary.to_excel(writer, sheet_name='overflow_summary',    index=False)
    details[['fuel','equipment','ID','施策名','row_number','M','N']] \
        .to_excel(writer,            sheet_name='details',             index=False)

print(f"出力完了: {out_path}")






