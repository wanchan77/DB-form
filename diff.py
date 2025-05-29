import pandas as pd
from datetime import datetime

# CSV 読み込み
df = pd.read_csv('/Users/wangzhende/intern/DBform/DB_20250425_confirmed.csv', low_memory=False)

# ── 列インデックス（0起点）取得 ───────────────────────────
id_idx    = df.columns.get_loc('施策ユニークNo')             # A列相当
name_idx  = df.columns.get_loc('施策名')                     # B列相当
bv_idx    = df.columns.get_loc('設備更新カウンタ')           # BV列相当

# M,N 列を列番号で指定（ユーザー指定）
m_idx     = 12   # 0起点の13列目が M 列
n_idx     = 13   # 0起点の14列目が N 列

TARGET_LABEL = "対象設備の中で施策を実施する設備の割合"

# ── 設備・燃料 列番号リスト ──────────────────────────────
equip_indices = list(range(93, 199))   # 0起点で CP(94)〜GR(200)
fuel_indices  = list(range(200, 232))  # 0起点で GS(201)〜HW(231)

# ここで必ず出力されるはず
print("▶ equip_indices 範囲:", equip_indices[0], "~", equip_indices[-1])
print("▶ electric_vehicle の列番号:", ev_col_idx)
print("▶ fuel_indices 範囲:",  fuel_indices[0],  "~", fuel_indices[-1])
print("▶ electricity の列番号:",   elec_col_idx)

# ── (1) フィルター前 全5,000行を展開 ─────────────────────
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

# ── (2) フィルター後：BV=1かつMラベルで展開 ───────────────
# エラーチェック表示
base_mask = (df.iloc[:, bv_idx] == 1) & (df.iloc[:, m_idx] == TARGET_LABEL)
print(f"エラーチェック: BV=1かつMラベル'{TARGET_LABEL}'の行数 = {base_mask.sum()}件")

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

# ── (3) フィルター後のサマリ & 詳細 ───────────────────────
summary = (
    exploded
    .groupby(['equipment','fuel'])
    .agg(count=('N','size'), sum_N=('N','sum'))
    .reset_index()
)
overflow_summary = summary[summary['sum_N'] >= 100][['equipment','fuel','count','sum_N']]
details = exploded.merge(
    overflow_summary[['equipment','fuel']],
    on=['equipment','fuel'],
    how='inner'
)


print(f"展開後レコード数 = {len(exploded)}件, summary.count 合計 = {summary['count'].sum()}件")

# ── (4) Excel出力 ───────────────────────────────────────
ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
out_path = f'/Users/wangzhende/intern/DBform/output_{ts}.xlsx'

with pd.ExcelWriter(out_path) as writer:
    pre_summary.to_excel(writer, sheet_name='pre_filter_summary', index=False)
    summary.to_excel(writer, sheet_name='summary', index=False)
    overflow_summary.to_excel(writer, sheet_name='overflow_summary', index=False)
    details[['fuel','equipment','ID','施策名','row_number','M','N']] \
        .to_excel(writer, sheet_name='details', index=False)

print(f"出力完了: {out_path}")


