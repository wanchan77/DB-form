import pandas as pd
from datetime import datetime

# タイムスタンプ生成
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# ファイルパス（必要に応じて変更）
input_csv_path = "/Users/wangzhende/intern/DBform/dbform_test_wind.csv"
target_format_csv_path = "/Users/wangzhende/intern/DBform/DB_20250325_modify.csv"
output_csv_path = f"/Users/wangzhende/intern/DBform/final_converted_dbform_utf8_{timestamp}.csv"

# 入力CSVとターゲットCSVを読み込む
df_input = pd.read_csv(input_csv_path)
df_target = pd.read_csv(target_format_csv_path)

# ターゲットの列情報を取得
target_column_names = df_target.columns.tolist()
num_target_columns = len(target_column_names)

# フォーム列 → ターゲット列 のマッピング（1始まり）
form_to_target_map = {
    9: 2, 10: 3, 11: 5, 12: 7, 13: 8, 14: 10, 15: 11, 16: 12, 17: 13, 18: 14,
    19: 15, 20: 16, 21: 17, 22: 18, 23: 19, 24: 20, 25: 21, 26: 22, 27: 23, 28: 24,
    35: 25, 36: 26, 37: 27, 39: 28, 40: 29, 41: 30, 43: 31, 44: 32, 45: 33, 47: 34,
    48: 35, 49: 36, 51: 37, 52: 38, 53: 39, 55: 40, 56: 41, 57: 42, 59: 43, 60: 44,
    61: 45, 63: 46, 64: 47, 65: 48, 67: 49, 68: 50, 69: 51, 71: 52, 72: 53, 73: 54,
    75: 55, 76: 56, 77: 57, 79: 58, 80: 59, 81: 60, 83: 61, 84: 62, 85: 63, 87: 64,
    88: 65, 89: 66, 91: 67, 92: 68, 93: 69, 95: 70, 96: 71, 97: 72,
    100: 232, 101: 233, 102: 234, 103: 235, 104: 236, 105: 237,
    107: 238, 108: 239, 109: 240, 111: 241, 112: 242, 113: 243,
    115: 244, 116: 245, 117: 246, 119: 259, 120: 260,
    121: 254, 122: 255, 123: 256, 124: 257,
}

# Scope1とScope2の設備名 → 英語コードの変換マッピング
scope1_mapping = {
    "空調(ボイラ)": "air_conditioning_boiler",
    "空調(冷凍機)": "air_conditioning_refrigerator",
    "空調(ウォータチラー空冷式)": "air_conditioning_air-cooled_water_chiller",
    "空調(ウォータチラー水冷式)": "air_conditioning_water-cooled_water_chiller",
    "空調(GHP)(パッケージ式)": "air_conditioning_GHP_package_type",
    "冷蔵/冷凍": "refrigeration_and_freezing",
    "給湯": "hot_water_supply",
    "発電": "power_generation",
    "自動車": "automobile",
    "タクシー": "taxi",
    "バス": "bus",
    "トラック": "truck",
    "重機/建機(トラック除く)": "heavy_machinery_and_construction_machinery_excluding_truck",
    "船舶": "ship",
    "航空機": "aircraft",
    "溶解炉": "melting_furnace_SCOPE1",
    "焼却炉": "incinerator",
    "生産用ボイラー": "production_boiler",
    "バーナー": "burner",
    "生産用ヒーター": "production_heater",
    "クリーンルーム用空調(ボイラ)": "air_conditioning_for_clean_room_boiler",
    "クリーンルーム用空調(冷凍機)": "air_conditioning_for_clean_room_refrigerator",
    "クリーンルーム用空調(ウォータチラー空冷式)": "air_conditioning_for_clean_room_air-cooled_water_chiller",
    "クリーンルーム用空調(ウォータチラー水冷式)": "air_conditioning_for_clean_room_water-cooled_water_chiller",
    "クリーンルーム用空調(GHP)(パッケージ式)": "air_conditioning_for_clean_room_GHP_package_type",
    "焼鈍炉": "annealing_furnace_SCOPE1",
    "乾燥炉": "drying_furnace_SCOPE1",
    "焼結炉/焼成炉": "sintering_furnace_firing_furnace_SCOPE1",
    "焼入れ炉": "hardening_furnace_SCOPE1",
    "鍛造炉・鍛造加熱炉": "forging_furnace_forging_heating_furnace_SCOPE1",
    "メッキ槽・電着塗装": "plating_tank_SCOPE1",
    "焼戻し炉": "tempering_furnace_SCOPE1",
    "衣類用乾燥機": "clothing_dryer_SCOPE1",
    "工業用乾燥機": "industrial_dryer_SCOPE1",
    "自家用発電機": "private_power_generator",
    "その他(SCOPE1)": "others_SCOPE1",
    "SCOPE1全体": "total_SCOPE1",
}

scope2_mapping = {
    "空調(電気)(パッケージ式)": "electric_air_conditioning_package_type",
    "空調(電気)(冷凍機)": "electric_air_conditioning_refrigerator",
    "空調(電気)(ウォーターチラー水冷式)": "electric_air_conditioning_water-cooled_water_chiller",
    "空調(電気)(ウォーターチラー空冷式)": "electric_air_conditioning_air-cooled_water_chiller",
    "冷蔵/冷凍": "electric_refrigeration_and_freezing",
    "給湯": "electric_hot_water_supply",
    "照明": "lighting",
    "サーバー機器": "server_equipment",
    "エレベータ": "elevator",
    "コンプレッサー": "compressor",
    "ポンプ": "pump",
    "送風機/給気・排気ファン": "fan_supply_and_exhaust_fan",
    "電気自動車": "electric_vehicle",
    "電気タクシー": "electric_taxi",
    "電気バス": "electric_bus",
    "電動トラック": "electric_truck",
    "織機": "loom",
    "ベルトコンベア": "belt_conveyor",
    "その他生産用モーター": "other_production_motors",
    "溶解炉": "melting_furnace_SCOPE2",
    "ヒーター": "heater",
    "自動販売機(飲料)": "vending_machine_beverages",
    "シャッター": "shutter",
    "錠剤印刷機": "tablet_printing_machine",
    "錠剤検査機": "tablet_inspection_machine",
    "集塵機": "dust_collector",
    "攪拌機": "mixer",
    "充填機": "filling_machine",
    "包装機": "packaging_machine",
    "クリーンルーム用空調(電気)(パッケージ式)": "electric_air_conditioning_for_clean_room_package_type",
    "クリーンルーム用空調(電気)(冷凍機)": "electric_air_conditioning_for_clean_room_refrigerator",
    "クリーンルーム用空調(電気)(ウォータチラー空冷式)": "electric_air_conditioning_for_clean_room_water-cooled_water_chiller",
    "クリーンルーム用空調(電気)(ウォータチラー水冷式)": "electric_air_conditioning_for_clean_room_air-cooled_water_chiller",
    "パソコン": "personal_computer",
    "焼鈍炉": "annealing_furnace_SCOPE2",
    "乾燥炉": "drying_furnace_SCOPE2",
    "焼結炉/焼成炉": "sintering_furnace_firing_furnace_SCOPE2",
    "旋盤・マシニングセンタ": "lathe_machining_center",
    "スポット溶接": "spot_welding",
    "ブラスター": "blaster",
    "樹脂射出成形機": "plastic_injection_molding_machine",
    "ゴム射出成形機": "rubber_injection_molding_machine",
    "ダイカストマシン": "die_casting_machine",
    "プレス機": "press_machine",
    "複合機/コピー機": "multifunction_printer_copier",
    "焼入れ炉": "hardening_furnace_SCOPE2",
    "鍛造炉・鍛造加熱炉": "forging_furnace_forging_heating_furnace_SCOPE2",
    "樹脂圧縮成形機": "resin_compression_molding_machine",
    "ゴム圧縮成形機": "rubber_compression_molding_machine",
    "樹脂押出成形機": "resin_extrusion_molding_machine",
    "ゴム押出成形機": "rubber_extrusion_molding_machine",
    "ゴム加硫槽（ゴム二次加硫工程）": "rubber_vulcanization_tank_secondary_rubber_vulcanization_process",
    "メッキ槽・電着塗装": "plating_tank_SCOPE2",
    "生産用チラー_水冷式": "production_chiller_water_cooled",
    "生産用チラー_空冷式": "production_chiller_air_cooled",
    "焼戻し炉": "tempering_furnace_SCOPE2",
    "衣類用乾燥機": "clothing_dryer_SCOPE2",
    "工業用乾燥機": "industrial_dryer_SCOPE2",
    "真空ポンプ": "vacuum_pump",
    "放電加工機": "electric_discharge_machine",
    "Scope2温水利用先_空調": "scope2_hot_water_usage_air_conditioning",
    "Scope2温水利用先_給湯": "scope2_hot_water_usage_hot_water_supply",
    "Scope2温水利用先_その他": "scope2_hot_water_usage_other",
    "Scope2冷水利用先_空調": "scope2_cold_water_usage_air_conditioning",
    "Scope2冷水利用先_その他": "scope2_cold_water_usage_other",
    "現場用照明": "site_lighting",
    "曝気・水処理用ブロワ": "aeration_water_treatment_blower",
    "その他用途のブロワ": "other_purpose_blower",
    "その他(SCOPE2)": "others_SCOPE2",
    "SCOPE2全体": "total_SCOPE2"
}

# 燃料名の日本語→英語マッピング（画像を元に手動定義）
fuel_mapping = {
    "軽油": "light_oil",
    "原油": "crude_oil",
    "灯油": "kerosene",
    "LPG": "LPG",
    "LNG": "LNG",
    "揮発油": "gasoline",
    "コンデンセート": "condensate",
    "ナフサ": "naphtha",
    "A重油": "A_heavy_oil",
    "B・C重油": "B_and_C_heavy_oil",
    "石油アスファルト": "petroleum_asphalt",
    "石油コークス": "petroleum_coke",
    "水素ガス": "hydrogen_gas",
    "その他可燃性天然ガス": "other_combustible_natural_gas",
    "原料炭": "raw_coal",
    "一般炭": "general_coal",
    "無煙炭": "smokeless_coal",
    "石炭コークス": "coal_coke",
    "コールタール": "coal_tar",
    "コークス炉ガス": "coke_oven_gas",
    "高炉ガス": "blast_furnace_gas",
    "転炉ガス": "converter_gas",
    "都市ガス": "city_gas",
    "その他燃料": "other_fuels",
    "産業用蒸気": "industrial_steam",
    "産業用以外の蒸気": "non-industrial_steam",
    "温水": "hot_water",
    "冷水": "cold_water",
    "その他": "others",
    "電力": "electricity",
    "全体(カーボンオフセット)": "total_carbon_offset"
}

# Scope1/2マッピング（設備→コード, フラグ）
scope1_id_map = {
    "SCOPE1全体": (0, 1), "その他(SCOPE1)": (1, 0), "その他 産業用熱源用(ボイラー、冷凍機、チラー、熱交換器)": (2, 0),
    "その他 産業用動力用(タービン)": (3, 0), "空調(ボイラ)": (4, 1), "空調(冷凍機)": (5, 1), "空調(ウォータチラー空冷式)": (6, 1),
    "空調(ウォータチラー水冷式)": (7, 1), "冷蔵/冷凍": (8, 0), "給湯": (9, 1), "発電": (10, 0), "自動車": (11, 1),
    "トラック": (12, 1), "重機/建機(トラック除く)": (13, 0), "船舶": (14, 0), "航空機": (15, 0), "化学薬品の原料": (16, 0),
    "鉱業用原料・燃料": (17, 0), "業務/産業 燃料": (18, 0), "溶解炉": (19, 0), "焼却炉": (20, 0), "脱水・乾燥機": (21, 0),
    "農林・水産": (22, 0), "生産用ボイラー": (23, 0), "バーナー": (24, 0), "空調(GHP)(パッケージ式)": (25, 0),
    "クリーンルーム用空調(ボイラ)": (27, 0), "クリーンルーム用空調(冷凍機)": (28, 0),
    "クリーンルーム用空調(ウォータチラー空冷式)": (29, 0), "クリーンルーム用空調(ウォータチラー水冷式)": (30, 0),
    "クリーンルーム用空調(GHP)(パッケージ式)": (31, 0), "焼鈍炉": (32, 0), "乾燥炉": (33, 0), "焼結炉/焼成炉": (34, 0),
    "ダイカストマシン": (35, 0), "焼入れ炉": (36, 0), "鍛造炉・鍛造加熱炉": (37, 0), "メッキ槽・電着塗装": (38, 0),
    "焼戻し炉": (39, 0), "衣類用乾燥機": (40, 0), "工業用乾燥機": (41, 0), "自家用発電機": (42, 0),
    "タクシー": (43, 1), "バス": (44, 1),
}

scope2_id_map = {
    "SCOPE2全体": (50, 1), "その他(SCOPE2)": (51, 1), "空調(電気)(パッケージ式)": (52, 1), "空調(電気)(個別式)": (53, 1),
    "冷蔵/冷凍": (54, 0), "給湯": (55, 1), "照明": (56, 1), "OA機器(パソコン、コピー機等)": (57, 1),
    "サーバー機器": (58, 1), "エレベータ": (59, 1), "コンプレッサー": (60, 0), "ポンプ": (61, 0),
    "送風機/給気・排気ファン": (62, 0), "電気自動車": (63, 1), "織機": (64, 0), "ベルトコンベア": (65, 0),
    "その他生産用モーター": (66, 0), "溶解炉": (67, 0), "ヒーター": (68, 0), "自動販売機(飲料)": (69, 1),
    "空調(電気)(冷凍機)": (70, 1), "空調(電気)(ウォータチラー空冷式)": (71, 1),
    "空調(電気)(ウォータチラー水冷式)": (72, 1), "シャッター": (73, 1), "錠剤印刷機": (74, 0),
    "錠剤検査機": (75, 0), "集塵機": (76, 0), "攪拌機": (77, 0), "充填機": (78, 0), "包装機": (79, 0),
    "クリーンルーム用空調(電気)(パッケージ式)": (80, 0), "クリーンルーム用空調(電気)(冷凍機)": (81, 0),
    "クリーンルーム用空調(電気)(ウォータチラー空冷式)": (82, 0),
    "クリーンルーム用空調(電気)(ウォータチラー水冷式)": (83, 0), "焼鈍炉": (84, 0), "乾燥炉": (85, 0),
    "焼結炉/焼成炉": (86, 0), "旋盤・マシニングセンタ": (87, 0), "スポット溶接": (88, 0), "ブラスター": (89, 0),
    "樹脂射出成形機": (90, 0), "ゴム射出成形機": (91, 0), "ダイカストマシン": (92, 0), "プレス機": (93, 0),
    "パソコン": (94, 1), "複合機/コピー機": (95, 1), "電動トラック": (96, 1), "焼入れ炉": (97, 0),
    "鍛造炉・鍛造加熱炉": (98, 0), "樹脂圧縮成形機": (100, 0), "ゴム圧縮成形機": (101, 0),
    "樹脂押出成形機": (102, 0), "ゴム押出成形機": (103, 0), "ゴム加硫槽（ゴム二次加硫工程）": (104, 0),
    "メッキ槽・電着塗装": (105, 0), "生産用チラー_水冷式": (106, 0), "生産用チラー_空冷式": (107, 0),
    "焼戻し炉": (108, 0), "真空ポンプ": (109, 0), "衣類用乾燥機": (110, 0), "工業用乾燥機": (111, 0),
    "放電加工機": (112, 0), "Scope2温水利用先_空調": (113, 1), "Scope2温水利用先_給湯": (114, 1),
    "Scope2温水利用先_その他": (115, 0), "Scope2冷水利用先_空調": (116, 1), "Scope2冷水利用先_その他": (117, 0),
    "現場用照明": (118, 0), "曝気・水処理用ブロワ": (119, 0), "その他用途のブロワ": (120, 0),
    "電気タクシー": (121, 1), "電気バス": (122, 1),
}

# 対応表：入力ファイル4列目 or 8列目の値をキーにして、出力ファイル248列目にセットする値
category_mapping = {
    "1(運用改善系)": 3,
    "2(設備投資系)": 4,
    "3(燃料転換系_1)": 6,
    "4(燃料転換系_2)": 6,
    "5(自由入力)": None  # これは緑施策など8列目で処理する
}

green_policy_mapping = {
    "1(運用改善系)": 3,
    "2(設備投資系)": 4,
    "3(燃料転換系_1)": 6,
    "4(燃料転換系_2)": 6,
    "5(緑施策)": 3  # これは緑施策など8列目で処理する
}

# 空のDataFrame（ターゲット形式）を作成
final_df = pd.DataFrame(columns=target_column_names)

# Scopeフラグ確認用リスト
scope_flag_issues = []

# 設備フラグ確認用リスト
equipment_flag_issues = []

# 燃料フラグ確認用リスト
fuel_flag_issues = []

# エラートラッキング
id_issues = []
gs_flag_issues = []

# フラグ問題チェック用
category_issues = []

id_list = []
shisaku_list = []  # 施策名（入力ファイル9列目）
kubun_list = []    # 区分（入力ファイル4列目）

pairing_issues = []  # 相互ID参照の失敗記録用

# 設備名の処理対象列（Scope1: 94〜130列 → index 93-129、Scope2: 131〜200 → index 130-199）
scope1_cols = target_column_names[93:130]
scope2_cols = target_column_names[130:200]

# Scope1/2に関係なく、燃料のフラグ対象列（共通）201〜231列 → index 200〜230
fuel_cols = target_column_names[200:231]

# 各行を処理
for i, row in df_input.iterrows():
    new_row = [""] * num_target_columns

    # 入力ファイル125~127列直接マッピング (index 124~126)
    for j in range(3):  # 0,1,2
        val = row[124 + j]
        if pd.notna(val):
            new_row[72 + j] = val  # 出力73~75列 (index 72~74)

    # 入力129列直接マッピング (index 128) → 出力249列 (index 248)
    val_129 = row[128]
    if pd.notna(val_129):
        new_row[248] = val_129

    # 入力138列直接マッピング (index 137) → 出力253列 (index 252)
    val_138 = row[137]
    if pd.notna(val_138):
        new_row[252] = val_138

    # 入力150列直接マッピング (index 149) → 出力250列 (index 249)
    val_150 = row[149]
    if pd.notna(val_150):
        new_row[249] = val_150

    # 入力151列直接マッピング (index 150) → 出力251列 (index 250)
    val_151 = row[150]
    if pd.notna(val_151):
        new_row[250] = val_151

    # 入力152列直接マッピング (index 151) → 出力252列 (index 251)
    val_152 = row[151]
    if pd.notna(val_152):
        new_row[251] = val_152

    # 通常のマッピングコピー
    for form_idx, target_idx in form_to_target_map.items():
        if form_idx <= len(row) and target_idx <= num_target_columns:
            new_row[target_idx - 1] = row[form_idx - 1]

    scope_val = str(row[0]).strip()
    equipment_name = str(row[1]).strip()
    fuel_name = str(row[2]).strip()  # 入力ファイルの3列目
    val_col4 = str(row[3]).strip()
    val_col8 = str(row[7]).strip()
    val_col125 = str(row[124]).strip() # 入力ファイルの125列目増加フラグ
    val_col126 = str(row[125]).strip() # 入力ファイルの126列目設備更新フラグ
    val_col127 = str(row[126]).strip() # 入力ファイルの127列目絶対値フラグ

    # Scopeフラグ処理
    if scope_val == "Scope1":
        new_row[75] = "1"  # 76列目
    elif scope_val == "Scope2":
        new_row[76] = "1"  # 77列目
    else:
        scope_flag_issues.append(i + 2)

    # 設備英語化＆該当列に1を立てる
    if scope_val == "Scope1" and equipment_name in scope1_mapping:
        eng = scope1_mapping[equipment_name]
        if eng in scope1_cols:
            col_idx = target_column_names.index(eng)
            new_row[col_idx] = "1"
        else:
            equipment_flag_issues.append(i + 2)
    elif scope_val == "Scope2" and equipment_name in scope2_mapping:
        eng = scope2_mapping[equipment_name]
        if eng in scope2_cols:
            col_idx = target_column_names.index(eng)
            new_row[col_idx] = "1"
        else:
            equipment_flag_issues.append(i + 2)
    else:
        equipment_flag_issues.append(i + 2)

    # 燃料英語化＆該当列に1を立てる
    if fuel_name in fuel_mapping:
        eng_fuel = fuel_mapping[fuel_name]
        if eng_fuel in fuel_cols:
            col_idx = target_column_names.index(eng_fuel)
            new_row[col_idx] = "1"
        else:
            fuel_flag_issues.append(i + 2)
    else:
        fuel_flag_issues.append(i + 2)

    # ID & フラグの処理
    if scope_val == "Scope1" and equipment_name in scope1_id_map:
        code, flag = scope1_id_map[equipment_name]
        new_row[0] = f"{str(code).zfill(3)}s2r{i + 857}"
        new_row[246] = str(flag)
    elif scope_val == "Scope2" and equipment_name in scope2_id_map:
        code, flag = scope2_id_map[equipment_name]
        new_row[0] = f"{str(code).zfill(3)}s2r{i + 857}"
        new_row[246] = str(flag)
    else:
        id_issues.append(i + 2)
        gs_flag_issues.append(i + 2)

    if val_col4 in category_mapping and category_mapping[val_col4] is not None:
        new_row[247] = category_mapping[val_col4]  # ← df_final ではなく new_row を使うのが正解
    elif val_col4 == "5(自由入力)" and val_col8 in green_policy_mapping:
        new_row[247] = green_policy_mapping[val_col8]
    else:
        category_issues.append(i + 2)
    
    # ▼ 入力125列目（index 124）：増加フラグが1 → new_row[247]を6に上書き
    if str(row[124]).strip() == "1":
        new_row[247] = 6

    # ▼ 入力126列目（index 125）：設備更新フラグが1 かつ 現在 new_row[247] が3 → 4に変更
    if new_row[247] == 3 and str(row[125]).strip() == "1":
        new_row[247] = 4

    # ▼ 入力127列目（index 126）：絶対値フラグが1 → new_row[247] を2に変更
    if str(row[126]).strip() == "1":
        new_row[247] = 2

    id_list.append(new_row[0])             # 出力1列目のID
    shisaku_list.append(str(row[8]).strip())  # 施策名（入力ファイル9列目）
    kubun_list.append(str(row[3]).strip())    # 区分（入力ファイル4列目）

    final_df.loc[len(final_df)] = new_row

for i in range(len(df_input)):
    my_shisaku = shisaku_list[i]
    my_kubun = kubun_list[i]

    # 探すべき対象の区分
    if my_kubun == "3(燃料転換系_1)":
        target_kubun = "4(燃料転換系_2)"
    elif my_kubun == "4(燃料転換系_2)":
        target_kubun = "3(燃料転換系_1)"
    else:
        continue  # 関係ない区分はスキップ

    # 該当施策名・ターゲット区分が一致する行を探す
    matched = False
    for j in range(len(df_input)):
        if shisaku_list[j] == my_shisaku and kubun_list[j] == target_kubun:
            final_df.iloc[i, 8] = id_list[j]  # 出力ファイル9列目（index 8）にIDをセット
            matched = True
            break

    if not matched:
        pairing_issues.append(i + 2)  # エラー行（Excelで見える行番号で）


# ファイルをUTF-8（BOM付き）で保存（Excelでも文字化けしない）
final_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

# ターミナル出力
# 出力ログ
if not id_issues:
    print("✅ ID問題なし")
else:
    for r in id_issues:
        print(f"⚠️ {r}行目ID問題あり")

if not gs_flag_issues:
    print("✅ 一般/専門フラグ問題なし")
else:
    for r in gs_flag_issues:
        print(f"⚠️ {r}行目一般/専門フラグ問題あり")

if not scope_flag_issues:
    print("✅ Scopeフラグ問題なし")
else:
    for row_num in scope_flag_issues:
        print(f"⚠️ {row_num}行目Scopeフラグ問題あり")

if not equipment_flag_issues:
    print("✅ 設備フラグ問題なし")
else:
    for row_num in equipment_flag_issues:
        print(f"⚠️ {row_num}行目設備フラグ問題あり")
    
# 燃料フラグチェック結果の表示
if not fuel_flag_issues:
    print("✅ 燃料フラグ問題なし")
else:
    for row_num in fuel_flag_issues:
        print(f"⚠️ {row_num}行目燃料フラグ問題あり")

# ログ出力
if not category_issues:
    print("✅ 施策分類問題なし")
else:
    for r in category_issues:
        print(f"⚠️ {r}行目施策分類問題あり")

if not pairing_issues:
    print("✅ ペアID問題なし")
else:
    for row in pairing_issues:
        print(f"⚠️ {row}行目相互ペアID問題あり")

print(f"📁 変換済みファイル保存先: {output_csv_path}")

