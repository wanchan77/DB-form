import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import re
import json
from pathlib import Path

# === Google Sheets 接続設定 ===
st.write("\u2705 認証情報をロード中...")

# secrets から Google 認証情報を取得（明示的に dict に変換）
credentials_info = dict(st.secrets["google_sheets"])

# 正しい OAuth スコープを設定
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# 認証情報を設定
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)
client = gspread.authorize(creds)

# Google Sheets に接続
try:
    spreadsheet = client.open_by_key("1hPxEranr8y9teHaiT-6MMShsljbCRLhhrv3huMmOmaY")
    sheet = spreadsheet.worksheet("form2test")
    st.write("\u2705 Google Sheets に接続成功！")
except Exception as e:
    st.error(f"\u274C Google Sheets への接続エラー: {e}")

# 簡略化
ss = st.session_state

# dfの読み込み
df = pd.read_csv('DB_20250425_industrial_steam_0528update.csv', low_memory=False)

# === ページ管理のためのセッション変数を初期化 ===
if "page" not in ss:
    ss["page"] = "page1"

if "user_input" not in ss:
    ss["user_input"] = {}

if 'selected_option_persist' not in ss:
    ss['selected_option_persist'] = None

if 'selected_option_temp' not in ss:
    ss['selected_option_temp'] = ss['selected_option_persist']

if 'strategy_number_persist' not in ss:
    ss['strategy_number_persist'] = ''

if 'strategy_number_temp' not in ss:
    ss['strategy_number_temp'] = ss['strategy_number_persist']


# ページ遷移関数
def next_page(next_page_name):
    ss["page"] = next_page_name
    st.rerun()


# ページ遷移しても、入力した内容を保持するための関数
def store_content(option_persist, option_temp):
    ss[option_persist] = ss[option_temp]


# # 計算式を区切ってリストにする関数
# def split_formula(formula_str):
#     # NaNや'なし'の場合は空リストを返す
#     if pd.isna(formula_str) or formula_str == 'なし':
#         return []
    
#     # <>とその中身を削除
#     without_angle = re.sub(r'<[^>]*>', '', formula_str)
    
#     # = + - × ÷ などで分割
#     split_list = re.split(r'[=\÷×\-+\(\)]', without_angle)
    
#     # 前後の空白を削除 & 空文字を除去
#     split_list = [x.strip() for x in split_list if x.strip() != '']
    
#     # 数字のみの要素を除去
#     filtered_list = [x for x in split_list if not re.match(r'^-?\d+(\.\d+)?$', x)]

#     to_delete_list = [
#         'CO2削減量',
#         'GHG削減量',
#         'コスト削減額',
#         '投資額',
#         '追加投資額',
#         '推測値'
#     ]
    
#     # さらに上記のリストの文字列を消去する
#     filtered_list = [item for item in filtered_list if not any(substr in item for substr in to_delete_list)]
    
#     return filtered_list

to_delete_list = [
    'CO2削減量',
    'GHG削減量',
    'コスト削減額',
    '投資額',
    '追加投資額',
    '推測値'
]

def split_formula(formula_str):
    # NaN や 'なし' は空リスト
    if pd.isna(formula_str) or formula_str == 'なし':
        return []

    # <...> を削除
    text = re.sub(r'<[^>]*>', '', formula_str)

    # 演算子を '|' に置換して分割
    parts = re.sub(r'[=÷×\+\-]', '|', text).split('|')

    tokens = []
    for p in parts:
        # 前後空白と端の丸括弧を除去
        p = p.strip().strip('()')
        # 空 or 数字だけのものはスキップ
        if not p or re.fullmatch(r'-?\d+(?:\.\d+)?', p):
            continue
        if p in to_delete_list:
            continue
        tokens.append(p)

    return tokens

# ちゃんと<>が閉じられているか確かめるための関数
def has_unclosed_tag(text):
    unclosed = 0
    for char in text:
        if char == '<':
            unclosed += 1
        elif char == '>':
                unclosed -= 1
    if unclosed == 0:
        return True
    else:
        return False

# 施策分類フラグ対応辞書
strategy_classification_flag_dict = {
    0: '再エネ',
    1: 'CO2フリー電力',
    2: 'カーボンクレジット',
    3: '省エネ運用系',
    4: '省エネ投資系',
    5: '省エネ設備更新系',
    6: '燃料転換',
    7: 'バイオマス'
}

# scope1設備種の日英対応辞書
equipment_translation_dict_scope1 = {
                    'air_conditioning_boiler': '空調(ボイラ)',
                    'air_conditioning_refrigerator': '空調(冷凍機)',
                    'air_conditioning_air-cooled_water_chiller': '空調(ウォータチラー空冷式)',
                    'air_conditioning_water-cooled_water_chiller': '空調(ウォータチラー水冷式)',
                    'air_conditioning_GHP_package_type': '空調(GHP)(パッケージ式)',
                    'refrigeration_and_freezing': '冷蔵/冷凍',
                    'hot_water_supply': '給湯',
                    'power_generation': '発電',
                    'automobile': '自動車',
                    'taxi': 'タクシー',
                    'bus': 'バス',
                    'truck': 'トラック',
                    'heavy_machinery_and_construction_machinery_excluding_truck': '重機/建機(トラック除く)',
                    'ship': '船舶',
                    'aircraft': '航空機',
                    'melting_furnace_SCOPE1': '溶解炉',
                    'incinerator': '焼却炉',
                    'production_boiler': '生産用ボイラー',
                    'burner': 'バーナー',
                    'production_heater': '生産用ヒーター',
                    'air_conditioning_for_clean_room_boiler': 'クリーンルーム用空調(ボイラ)',
                    'air_conditioning_for_clean_room_refrigerator': 'クリーンルーム用空調(冷凍機)',
                    'air_conditioning_for_clean_room_air-cooled_water_chiller': 'クリーンルーム用空調(ウォータチラー空冷式)',
                    'air_conditioning_for_clean_room_water-cooled_water_chiller': 'クリーンルーム用空調(ウォータチラー水冷式)',
                    'air_conditioning_for_clean_room_GHP_package_type': 'クリーンルーム用空調(GHP)(パッケージ式)',
                    'annealing_furnace_SCOPE1': '焼鈍炉',
                    'drying_furnace_SCOPE1': '乾燥炉',
                    'sintering_furnace_firing_furnace_SCOPE1': '焼結炉/焼成炉',
                    'hardening_furnace_SCOPE1': '焼入れ炉',
                    'forging_furnace_forging_heating_furnace_SCOPE1': '鍛造炉・鍛造加熱炉',
                    'plating_tank_SCOPE1': 'メッキ槽・電着塗装',
                    'tempering_furnace_SCOPE1': '焼戻し炉',
                    'clothing_dryer_SCOPE1': '衣類用乾燥機',
                    'industrial_dryer_SCOPE1': '工業用乾燥機',
                    'private_power_generator': '自家用発電機',
                    'others_SCOPE1': 'SCOPE1全体',
                    'total_SCOPE1': 'その他(SCOPE1)'
                }

# scope1燃料種の日英対応辞書
fuel_translation_dict_scope1 = {
                    'light_oil': '軽油',
                    'crude_oil': '原油',
                    'kerosene': '灯油',
                    'LPG': 'LPG',
                    'LNG': 'LNG',
                    'gasoline': '揮発油',
                    'condensate': 'コンデンセート',
                    'naphtha': 'ナフサ',
                    'A_heavy_oil': 'A重油',
                    'B_and_C_heavy_oil': 'B・C重油',
                    'petroleum_asphalt': '石油アスファルト',
                    'petroleum_coke': '石油コークス',
                    'hydrogen_gas': '水素ガス',
                    'other_combustible_natural_gas': 'その他可燃性天然ガス',
                    'raw_coal': '原料炭',
                    'general_coal': '一般炭',
                    'smokeless_coal': '無煙炭',
                    'coal_coke': '石炭コークス',
                    'coal_tar': 'コールタール',
                    'coke_oven_gas': 'コークス炉ガス',
                    'blast_furnace_gas': '高炉ガス',
                    'converter_gas': '転炉ガス',
                    'city_gas': '都市ガス',
                    'other_fuels': 'その他燃料',
                    'industrial_steam': '産業用蒸気',
                    'non-industrial_steam': '産業用以外の蒸気',
                    'others': 'その他',
                    'total_carbon_offset': '全体(カーボンオフセット)'
                }
                
# scope2設備種の日英対応辞書
equipment_translation_dict_scope2 = {
                    'electric_air_conditioning_package_type': '空調(電気)(パッケージ式)',
                    'electric_air_conditioning_refrigerator': '空調(電気)(冷凍機)',
                    'electric_air_conditioning_water-cooled_water_chiller': '空調(電気)(ウォータチラー水冷式)',
                    'electric_air_conditioning_air-cooled_water_chiller': '空調(電気)(ウォータチラー空冷式)',
                    'electric_refrigeration_and_freezing': '冷蔵/冷凍',
                    'electric_hot_water_supply': '給湯',
                    'lighting': '照明',
                    'server_equipment': 'サーバー機器',
                    'elevator': 'エレベータ',
                    'compressor': 'コンプレッサー',
                    'pump': 'ポンプ',
                    'fan_supply_and_exhaust_fan': '送風機/給気・排気ファン',
                    'electric_vehicle': '電気自動車',
                    'electric_taxi': '電気タクシー',
                    'electric_bus': '電気バス',
                    'electric_truck': '電動トラック',
                    'loom': '織機',
                    'belt_conveyor': 'ベルトコンベア',
                    'other_production_motors': 'その他生産用モーター',
                    'melting_furnace_SCOPE2': '溶解炉',
                    'heater': 'ヒーター',
                    'vending_machine_beverages': '自動販売機(飲料)',
                    'shutter': 'シャッター',
                    'tablet_printing_machine': '錠剤印刷機',
                    'tablet_inspection_machine': '錠剤検査機',
                    'dust_collector': '集塵機',
                    'mixer': '攪拌機',
                    'filling_machine': '充填機',
                    'packaging_machine': '包装機',
                    'electric_air_conditioning_for_clean_room_package_type': 'クリーンルーム用空調(電気)(パッケージ式)',
                    'electric_air_conditioning_for_clean_room_refrigerator': 'クリーンルーム用空調(電気)(冷凍機)',
                    'electric_air_conditioning_for_clean_room_water-cooled_water_chiller': 'クリーンルーム用空調(電気)(ウォータチラー空冷式)',
                    'electric_air_conditioning_for_clean_room_air-cooled_water_chiller': 'クリーンルーム用空調(電気)(ウォータチラー水冷式)',
                    'personal_computer': 'パソコン',
                    'annealing_furnace_SCOPE2': '焼鈍炉',
                    'drying_furnace_SCOPE2': '乾燥炉',
                    'sintering_furnace_firing_furnace_SCOPE2': '焼結炉/焼成炉',
                    'lathe_machining_center': '旋盤・マシニングセンタ',
                    'spot_welding': 'スポット溶接',
                    'blaster': 'ブラスター',
                    'plastic_injection_molding_machine': '樹脂射出成形機',
                    'rubber_injection_molding_machine': 'ゴム射出成形機',
                    'die_casting_machine': 'ダイカストマシン',
                    'press_machine': 'プレス機',
                    'multifunction_printer_copier': '複合機/コピー機',
                    'hardening_furnace_SCOPE2': '焼入れ炉',
                    'forging_furnace_forging_heating_furnace_SCOPE2': '鍛造炉・鍛造加熱炉',
                    'resin_compression_molding_machine': '樹脂圧縮成形機',
                    'rubber_compression_molding_machine': 'ゴム圧縮成形機',
                    'resin_extrusion_molding_machine': '樹脂押出成形機',
                    'rubber_extrusion_molding_machine': 'ゴム押出成形機',
                    'rubber_vulcanization_tank_secondary_rubber_vulcanization_process': 'ゴム加硫槽（ゴム二次加硫工程）',
                    'plating_tank_SCOPE2': 'メッキ槽・電着塗装',
                    'production_chiller_water_cooled': '生産用チラー_水冷式',
                    'production_chiller_air_cooled': '生産用チラー_空冷式',
                    'tempering_furnace_SCOPE2': '焼戻し炉',
                    'clothing_dryer_SCOPE2': '衣類用乾燥機',
                    'industrial_dryer_SCOPE2': '工業用乾燥機',
                    'vacuum_pump': '真空ポンプ',
                    'electric_discharge_machine': '放電加工機',
                    'scope2_hot_water_usage_air_conditioning': 'Scope2温水利用先_空調',
                    'scope2_hot_water_usage_hot_water_supply': 'Scope2温水利用先_給湯',
                    'scope2_hot_water_usage_other': 'Scope2温水利用先_その他',
                    'scope2_cold_water_usage_air_conditioning': 'Scope2冷水利用先_空調',
                    'scope2_cold_water_usage_other': 'Scope2冷水利用先_その他',
                    'site_lighting': '現場用照明',
                    'aeration_water_treatment_blower': '曝気・水処理用ブロワ',
                    'other_purpose_blower': 'その他用途のブロワ',
                    'others_SCOPE2': 'SCOPE2全体',
                    'total_SCOPE2': 'その他(SCOPE2)'
                }

# scope2燃料種の日英対応辞書
fuel_translation_dict_scope2 = {'hot_water': '温水', 'cold_water': '冷水', 'electricity': '電力'}



# ** 1ページ目 **
if ss["page"] == "page1":
    TEMPLATE_OPTIONS = ['使用しない', 'csvファイルを読み込む', 'jsonファイルを読み込む']
    selected_option = st.selectbox(
        '既存の施策をテンプレートとして使用しますか？', 
        TEMPLATE_OPTIONS,
        key='selected_option_temp', 
        on_change=store_content, 
        args=('selected_option_persist', 'selected_option_temp')
    )

    if selected_option == '使用しない':
        st.title("施策基本情報入力")

        # session_stateに格納されていない場合
        if 'default_scope_persist' not in ss:
            ss['default_scope_persist'] = 'Scope1'
        if 'default_scope_temp' not in ss:
            ss['default_scope_temp'] = ss['default_scope_persist']

        if 'default_equipment_name_persist' not in ss:
            ss['default_equipment_name_persist'] = ''
        if 'default_equipment_name_temp' not in ss:
            ss['default_equipment_name_temp'] = ss['default_equipment_name_persist']

        if 'default_fuel_name_persist' not in ss:
            ss['default_fuel_name_persist'] = ''
        if 'default_fuel_name_temp' not in ss:
            ss['default_fuel_name_temp'] = ss['default_fuel_name_persist']
        
        if 'default_formula_template_persist' not in ss:
            ss['default_formula_template_persist'] = '1(運用改善系)'
        if 'default_formula_template_temp' not in ss:
            ss['default_formula_template_temp'] = ss['default_formula_template_persist']

        if 'default_scope_fuel_conversion_persist' not in ss:
            ss['default_scope_fuel_conversion_persist']= ''
        if 'default_scope_fuel_conversion_temp' not in ss:
            ss['default_scope_fuel_conversion_temp']= ss['default_scope_fuel_conversion_persist']
        
        if 'default_equipment_fuel_conversion_persist' not in ss:
            ss['default_equipment_fuel_conversion_persist'] = ''
        if 'default_equipment_fuel_conversion_temp' not in ss:
            ss['default_equipment_fuel_conversion_temp'] = ss['default_equipment_fuel_conversion_persist']

        if 'default_fuel_fuel_conversion_persist' not in ss:
            ss['default_fuel_fuel_conversion_persist'] = ''
        if 'default_fuel_fuel_conversion_temp' not in ss:
            ss['default_fuel_fuel_conversion_temp'] = ss['default_fuel_fuel_conversion_persist']

        if 'default_measure_type_persist' not in ss:
            ss['default_measure_type_persist'] = ''
        if 'default_measure_type_temp' not in ss:
            ss['default_measure_type_temp'] = ss['default_measure_type_persist']

        if 'default_施策名_persist' not in ss:
            ss['default_施策名_persist'] = ''
        if 'default_施策名_temp' not in ss:
            ss['default_施策名_temp'] = ss['default_施策名_persist']

        scope = st.selectbox(
            "どのScopeですか？", 
            ["Scope1", "Scope2"],
            key='default_scope_temp',
            on_change=store_content,
            args=('default_scope_persist', 'default_scope_temp')
        )
        ss["user_input"]["Scope"] = scope
        
        if scope == "Scope1":
            equipment_options = [
                "",
                "空調(ボイラ)",
                "空調(冷凍機)",
                "空調(ウォータチラー空冷式)",
                "空調(ウォータチラー水冷式)",
                "空調(GHP)(パッケージ式)",
                "冷蔵/冷凍",
                "給湯",
                "発電",
                "自動車",
                "タクシー",
                "バス",
                "トラック",
                "重機/建機(トラック除く)",
                "船舶",
                "航空機",
                "溶解炉",
                "焼却炉",
                "生産用ボイラー",
                "バーナー",
                "生産用ヒーター",
                "クリーンルーム用空調(ボイラ)",
                "クリーンルーム用空調(冷凍機)",
                "クリーンルーム用空調(ウォータチラー空冷式)",
                "クリーンルーム用空調(ウォータチラー水冷式)",
                "クリーンルーム用空調(GHP)(パッケージ式)",
                "焼鈍炉",
                "乾燥炉",
                "焼結炉/焼成炉",
                "焼入れ炉",
                "鍛造炉・鍛造加熱炉",
                "メッキ槽・電着塗装",
                "焼戻し炉",
                "衣類用乾燥機",
                "工業用乾燥機",
                "自家用発電機",
                "SCOPE1全体",
                "その他(SCOPE1)"
            ]   
    
            fuel_options = ["", "軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "産業用蒸気", "産業用以外の蒸気", "その他", "全体(カーボンオフセット)"]
        else:
            equipment_options = [
                "",
                "空調(電気)(パッケージ式)",
                "空調(電気)(冷凍機)",
                "空調(電気)(ウォータチラー水冷式)",
                "空調(電気)(ウォータチラー空冷式)",
                "冷蔵/冷凍",
                "給湯",
                "照明",
                "サーバー機器",
                "エレベータ",
                "コンプレッサー",
                "ポンプ",
                "送風機/給気・排気ファン",
                "電気自動車",
                "電気タクシー",
                "電気バス",
                "電動トラック",
                "織機",
                "ベルトコンベア",
                "その他生産用モーター",
                "溶解炉",
                "ヒーター",
                "自動販売機(飲料)",
                "シャッター",
                "錠剤印刷機",
                "錠剤検査機",
                "集塵機",
                "攪拌機",
                "充填機",
                "包装機",
                "クリーンルーム用空調(電気)(パッケージ式)",
                "クリーンルーム用空調(電気)(冷凍機)",
                "クリーンルーム用空調(電気)(ウォータチラー空冷式)",
                "クリーンルーム用空調(電気)(ウォータチラー水冷式)",
                "パソコン",
                "焼鈍炉",
                "乾燥炉",
                "焼結炉/焼成炉",
                "旋盤・マシニングセンタ",
                "スポット溶接",
                "ブラスター",
                "樹脂射出成形機",
                "ゴム射出成形機",
                "ダイカストマシン",
                "プレス機",
                "複合機/コピー機",
                "焼入れ炉",
                "鍛造炉・鍛造加熱炉",
                "樹脂圧縮成形機",
                "ゴム圧縮成形機",
                "樹脂押出成形機",
                "ゴム押出成形機",
                "ゴム加硫槽（ゴム二次加硫工程）",
                "メッキ槽・電着塗装",
                "生産用チラー_水冷式",
                "生産用チラー_空冷式",
                "焼戻し炉",
                "衣類用乾燥機",
                "工業用乾燥機",
                "真空ポンプ",
                "放電加工機",
                "Scope2温水利用先_空調",
                "Scope2温水利用先_給湯",
                "Scope2温水利用先_その他",
                "Scope2冷水利用先_空調",
                "Scope2冷水利用先_その他",
                "現場用照明",
                "曝気・水処理用ブロワ",
                "その他用途のブロワ",
                "SCOPE2全体",
                "その他(SCOPE2)"
            ]   
    
            fuel_options = ["", "温水", "冷水", "電力"]
    
        equipment = st.selectbox(
            "どの設備の施策ですか？", 
            equipment_options,
            key='default_equipment_name_temp',
            on_change=store_content,
            args=('default_equipment_name_persist', 'default_equipment_name_temp')
        )
        ss["user_input"]["設備"] = equipment
    
        fuel = st.selectbox(
            "どの燃料ですか？", 
            fuel_options,
            key='default_fuel_name_temp',
            on_change=store_content,
            args=('default_fuel_name_persist', 'default_fuel_name_temp')
        )
        ss["user_input"]["燃料"] = fuel
    
        formula_template = st.selectbox(
            "式はテンプレですか？", 
            ["1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(自由入力)"],
            key='default_formula_template_temp',
            on_change=store_content,
            args=('default_formula_template_persist', 'default_formula_template_temp')
        )
        ss["user_input"]["テンプレ"] = formula_template
    
        neworold_scope = st.selectbox(
            "燃料転換前or燃料転換後はどのScopeですか？(今回入力していない方の施策について)", 
            ["","Scope1", "Scope2"],
            key='default_scope_fuel_conversion_temp',
            on_change=store_content,
            args=('default_scope_fuel_conversion_persist', 'default_scope_fuel_conversion_temp')
        )
        ss["user_input"]["Neworoldscope"] = neworold_scope
    
        if neworold_scope == "Scope1":
            neworold_scope_equipment_options = ["","空調(ボイラ)", "空調(冷凍機)", "空調(ウォータチラー空冷式)", "空調(ウォータチラー水冷式)", "空調(GHP)(パッケージ式)", "冷蔵/冷凍", "給湯", "発電", "自動車", "トラック", "重機/建機(トラック除く)", "船舶", "航空機", "溶解炉", "焼却炉", "生産用ボイラー", "バーナー", "生産用ヒーター", "クリーンルーム用空調(ボイラ)", "クリーンルーム用空調(冷凍機)", "クリーンルーム用空調(ウォータチラー空冷式)", "クリーンルーム用空調(ウォータチラー水冷式)", "クリーンルーム用空調(GHP)(パッケージ式)", "焼鈍炉", "乾燥炉", "焼結炉/焼成炉", "焼入れ炉", "鍛造炉・鍛造加熱炉", "メッキ槽・電着塗装", "焼戻し炉", "衣類用乾燥機", "工業用乾燥機", "自家用発電機", "その他(SCOPE1)", "SCOPE1全体"]
            neworold_scope_fuel_options = ["","軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "全体(カーボンオフセット)"]
        else:
            neworold_scope_equipment_options = ["","空調(電気)(パッケージ式)", "空調(電気)(冷凍機)", "空調(電気)(ウォーターチラー水冷式)", "空調(電気)(ウォーターチラー空冷式)", "冷蔵/冷凍", "給湯", "照明", "サーバー機器", "エレベータ", "コンプレッサー", "ポンプ", "送風機/給気・排気ファン", "電気自動車", "電動トラック", "その他(SCOPE2)", "SCOPE2全体"]
            neworold_scope_fuel_options = ["","電力","産業用蒸気", "産業用以外の蒸気", "温水", "冷水", "その他", "全体(カーボンオフセット)"]
    
        neworold_scope_equipment = st.selectbox(
            "燃料転換前or燃料転換後はどの設備の施策ですか？(今回入力していない方の施策について)", 
            neworold_scope_equipment_options,
            key='default_equipment_fuel_conversion_temp',
            on_change=store_content,
            args=('default_equipment_fuel_conversion_persist', 'default_equipment_fuel_conversion_temp')
        )
        ss["user_input"]["neworold_scope_設備"] = neworold_scope_equipment
    
        neworold_scope_fuel = st.selectbox(
            "燃料転換前or燃料転換後はどの燃料ですか？(今回入力していない方の施策について)", 
            neworold_scope_fuel_options,
            key='default_fuel_fuel_conversion_temp',
            on_change=store_content,
            args=('default_fuel_fuel_conversion_persist', 'default_fuel_fuel_conversion_temp')
        )
        ss["user_input"]["neworold_scope_燃料"] = neworold_scope_fuel
    
        measure_type = st.selectbox(
            "施策の種類はどれですか？(自由入力の場合のみ入力)", 
            ["","1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(緑施策)"],
            key='default_measure_type_temp',
            on_change=store_content,
            args=('default_measure_type_persist', 'default_measure_type_temp')
        )
        ss["user_input"]["施策の種類"] = measure_type
    
        measures = st.text_input(
            "施策名はなんですか？", 
            key='default_施策名_temp',
            on_change=store_content,
            args=('default_施策名_persist', 'default_施策名_temp')
        )
        ss["user_input"]["施策名"] = measures
    
        if st.button("次へ"):
            if formula_template.startswith("1"):
                next_page("page2A")
            elif formula_template.startswith("2"):
                next_page("page2B")
            elif formula_template.startswith("3"):
                next_page("page2C")
            elif formula_template.startswith("4"):
                next_page("page2D")
            elif formula_template.startswith("5") and measure_type == "5(緑施策)":
                next_page("page2F")
            else:
                next_page("page2E")

    elif selected_option == 'csvファイルを読み込む':
        strategy_number = str(st.text_input(
            'テンプレートとして使用する施策ユニークNoを入力してください', 
            key='strategy_number_temp', 
            on_change=store_content, 
            args=('strategy_number_persist', 'strategy_number_temp')
        ))

        if (df['施策ユニークNo'] == strategy_number).any() == True and strategy_number != '':
            filtered_df = df[df['施策ユニークNo'] == strategy_number]
            st.write(f'「{filtered_df['施策名'].iloc[0]}」をテンプレートとして使用します')

            # 読み込んだ施策のデフォルト値を設定
            if 'default_施策名_persist' not in ss:
                ss['default_施策名_persist'] = filtered_df['施策名'].iloc[0]
            if 'default_施策名_temp' not in ss:
                ss['default_施策名_temp'] = ss['default_施策名_persist']

            if 'default_scope_persist' not in ss:
                if filtered_df['Scope1'].iloc[0] == 1:
                    ss['default_scope_persist'] = 'Scope1'
                if filtered_df['Scope2'].iloc[0] == 1:
                    ss['default_scope_persist'] = 'Scope2'
            if 'default_scope_temp' not in ss:
                ss['default_scope_temp'] = ss['default_scope_persist']

            if 'default_一般/専門フラグ_persist' not in ss:
                ss['default_一般/専門フラグ_persist'] = filtered_df['一般/専門フラグ'].iloc[0]
            if 'default_一般/専門フラグ_temp' not in ss:
                ss['default_一般/専門フラグ_temp'] = ss['default_一般/専門フラグ_persist']

            if 'default_施策分類フラグ_persist' not in ss:
                ss['default_施策分類フラグ_persist'] = filtered_df['施策分類フラグ'].iloc[0]
            if 'default_施策分類フラグ_temp' not in ss:
                ss['default_施策分類フラグ_temp'] = ss['default_施策分類フラグ_persist']
            
            empty_vals = {"", "なし"}
            if 'default_measure_type_persist' not in ss:
                if ss['default_施策分類フラグ_persist'] == 3:
                    ss['default_measure_type_persist'] = "1(運用改善系)"
                elif ss['default_施策分類フラグ_persist'] == 4 or ss['default_施策分類フラグ_persist'] == 5:
                    ss['default_measure_type_persist'] = "2(設備投資系)"
                elif ss['default_施策分類フラグ_persist'] == 6 and ss['default_施策名_persist'].endswith('_1'):
                    ss['default_measure_type_persist'] = "3(燃料転換系_1)"
                elif ss['default_施策分類フラグ_persist'] == 6 and ss['default_施策名_persist'].endswith('_2'):
                    ss['default_measure_type_persist'] = "4(燃料転換系_2)"
                elif all(x in empty_vals for x in (ss['default_GHG削減量（ton-CO2）_persist'], ss['default_GHG削減量（ton-CO2）（CO2フリー計算用）_persist'], ss['default_コスト削減額（円/年）_persist'], ss['default_コスト削減額（円/年）（CO2フリー計算用)_persist'], ss['default_投資額（円）_persist'], ss['default_追加投資額（円）_persist'])):
                    ss['default_measure_type_persist'] = "5(緑施策)"
                else:
                    ss['default_measure_type_persist'] = ''
            if 'default_measure_type_temp' not in ss:
                ss['default_measure_type_temp'] = ss['default_measure_type_persist']

            # 燃料転換施策の場合、scope・設備・燃料・施策名を考慮する
            if ss['default_施策分類フラグ_persist'] == 6:
                if ss['default_施策名_persist'].endswith('_1'):
                    common_part = ss['default_施策名_persist'].removesuffix("_1")
                    # common_part + '_2'で終わる施策を探す
                    target_df = df[df["施策名"].str.startswith(common_part+'_2', na=False)]
                    if target_df['Scope1'].iloc[0] == 1:
                        if 'default_scope_after_fuel_conversion_persist' not in ss: 
                            ss['default_scope_after_fuel_conversion_persist'] = 'Scope1'
                        if 'default_scope_after_fuel_conversion_temp' not in ss: 
                            ss['default_scope_after_fuel_conversion_temp'] = ss['default_scope_after_fuel_conversion_persist']

                        # 設備種フラグが立っている位置を特定し、列名を取得する
                        equipment_row_slice = target_df.iloc[0]['air_conditioning_boiler': 'total_SCOPE1']
                        equipment_target_col = equipment_row_slice[equipment_row_slice == 1].index[0]
                        if 'default_equipment_after_fuel_conversion_persist' not in ss:
                            ss['default_equipment_after_fuel_conversion_persist'] = equipment_translation_dict_scope1[equipment_target_col]
                        if 'default_equipment_after_fuel_conversion_temp' not in ss:
                            ss['default_equipment_after_fuel_conversion_temp'] = ss['default_equipment_after_fuel_conversion_persist']

                        #燃料種フラグが立っている位置を特定し、列名を取得する
                        range_cols = target_df.loc[:, 'light_oil': 'non-industrial_steam'].columns.tolist()
                        single_cols = ['others','total_carbon_offset']
                        cols_to_check = range_cols + single_cols
                        fuel_row_slice = target_df.iloc[0][cols_to_check]
                        fuel_target_col = fuel_row_slice[fuel_row_slice == 1].index[0]
                        if 'default_fuel_after_fuel_conversion_persist' not in ss:
                            ss['default_fuel_after_fuel_conversion_persist'] = fuel_translation_dict_scope1[fuel_target_col]
                        if 'default_fuel_after_fuel_conversion_temp' not in ss:
                            ss['default_fuel_after_fuel_conversion_temp'] = ss['default_fuel_after_fuel_conversion_persist']

                    elif target_df['Scope2'].iloc[0] == 1:
                        if 'default_scope_after_fuel_conversion_persist' not in ss:
                            ss['default_scope_after_fuel_conversion_persist'] = 'Scope2'
                        if 'default_scope_after_fuel_conversion_temp' not in ss:
                            ss['default_scope_after_fuel_conversion_temp'] = ss['default_scope_after_fuel_conversion_persist']

                        # 設備種フラグが立っている位置を特定し、列名を取得する
                        equipment_row_slice = target_df.iloc[0]['electric_air_conditioning_package_type': 'total_SCOPE2']
                        equipment_target_col = equipment_row_slice[equipment_row_slice == 1].index[0]
                        if 'default_equipment_after_fuel_conversion_persist' not in ss:
                            ss['default_equipment_after_fuel_conversion_persist'] = equipment_translation_dict_scope2[equipment_target_col]
                        if 'default_equipment_after_fuel_conversion_temp' not in ss:
                            ss['default_equipment_after_fuel_conversion_temp'] = ss['default_equipment_after_fuel_conversion_persist']

                        # 燃料種フラグが立っている位置を特定し、列名を取得する
                        cols_to_check = ['hot_water', 'cold_water', 'electricity']
                        fuel_row_slice = target_df.iloc[0][cols_to_check]
                        fuel_target_col = fuel_row_slice[fuel_row_slice == 1].index[0]
                        if 'default_fuel_after_fuel_conversion_persist' not in ss:
                            ss['default_fuel_after_fuel_conversion_persist'] = fuel_translation_dict_scope2[fuel_target_col]
                        if 'default_fuel_after_fuel_conversion_temp' not in ss:
                            ss['default_fuel_after_fuel_conversion_temp'] = ss['default_fuel_after_fuel_conversion_persist']
        
                elif ss['default_施策名_persist'].endswith('_2'):
                    common_part = ss['default_施策名_persist'].removesuffix("_2")
                    # common_part + '_1'で終わる施策を探す
                    target_df = df[df["施策名"].str.startswith(common_part+'_1', na=False)]
                    if target_df['Scope1'].iloc[0] == 1:
                        if 'default_scope_before_fuel_conversion_persist' not in ss:
                            ss['default_scope_before_fuel_conversion_persist'] = 'Scope1'
                        if 'default_scope_before_fuel_conversion_temp' not in ss:
                            ss['default_scope_before_fuel_conversion_temp'] = ss['default_scope_before_fuel_conversion_persist']

                        # 設備種フラグが立っている位置を特定し、列名を取得する
                        equipment_row_slice = target_df.iloc[0]['air_conditioning_boiler': 'total_SCOPE1']
                        equipment_target_col = equipment_row_slice[equipment_row_slice == 1].index[0]
                        if 'default_equipment_before_fuel_conversion_persist' not in ss:
                            ss['default_equipment_before_fuel_conversion_persist'] = equipment_translation_dict_scope1[equipment_target_col]
                        if 'default_equipment_before_fuel_conversion_temp' not in ss:
                            ss['default_equipment_before_fuel_conversion_temp'] = ss['default_equipment_before_fuel_conversion_persist']

                        #燃料種フラグが立っている位置を特定し、列名を取得する
                        range_cols = target_df.loc[:, 'light_oil': 'non-industrial_steam'].columns.tolist()
                        single_cols = ['others','total_carbon_offset']
                        cols_to_check = range_cols + single_cols
                        fuel_row_slice = target_df.iloc[0][cols_to_check]
                        fuel_target_col = fuel_row_slice[fuel_row_slice == 1].index[0]
                        if 'default_fuel_before_fuel_conversion_persist' not in ss:
                            ss['default_fuel_before_fuel_conversion_persist'] = fuel_translation_dict_scope1[fuel_target_col]
                        if 'default_fuel_before_fuel_conversion_temp' not in ss:
                            ss['default_fuel_before_fuel_conversion_temp'] = ss['default_fuel_before_fuel_conversion_persist']

                    elif target_df['Scope2'].iloc[0] == 1:
                        if 'default_scope_before_fuel_conversion_persist' not in ss:
                            ss['default_scope_before_fuel_conversion_persist'] = 'Scope2'
                        if 'default_scope_before_fuel_conversion_temp' not in ss:
                            ss['default_scope_before_fuel_conversion_temp'] = ss['default_scope_before_fuel_conversion_persist']

                        # 設備種フラグが立っている位置を特定し、列名を取得する
                        equipment_row_slice = target_df.iloc[0]['electric_air_conditioning_package_type': 'total_SCOPE2']
                        equipment_target_col = equipment_row_slice[equipment_row_slice == 1].index[0]
                        if 'default_equipment_before_fuel_conversion_persist' not in ss:
                            ss['default_equipment_before_fuel_conversion_persist'] = equipment_translation_dict_scope2[equipment_target_col]
                        if 'default_equipment_before_fuel_conversion_temp' not in ss:
                            ss['default_equipment_before_fuel_conversion_temp'] = ss['default_equipment_before_fuel_conversion_persist']

                        # 燃料種フラグが立っている位置を特定し、列名を取得する
                        cols_to_check = ['hot_water', 'cold_water', 'electricity']
                        fuel_row_slice = target_df.iloc[0][cols_to_check]
                        fuel_target_col = fuel_row_slice[fuel_row_slice == 1].index[0]
                        if 'default_fuel_before_fuel_conversion_persist' not in ss:
                            ss['default_fuel_before_fuel_conversion_persist'] = fuel_translation_dict_scope2[fuel_target_col]
                        if 'default_fuel_before_fuel_conversion_temp' not in ss:
                            ss['default_fuel_before_fuel_conversion_temp'] = ss['default_fuel_before_fuel_conversion_persist']

                else: # 燃料転換でない場合は空文字をデフォルトとする
                    if 'default_scope_before_fuel_conversion_persist' not in ss:
                        ss['default_scope_before_fuel_conversion_persist']= ''
                    if 'default_scope_before_fuel_conversion_temp' not in ss:
                        ss['default_scope_before_fuel_conversion_temp']= ss['default_scope_before_fuel_conversion_persist']

                    if 'default_scope_after_fuel_conversion_persist' not in ss:
                        ss['default_scope_after_fuel_conversion_persist'] = ''
                    if 'default_scope_after_fuel_conversion_temp' not in ss:
                        ss['default_scope_after_fuel_conversion_temp'] = ss['default_scope_after_fuel_conversion_persist']

            # 入力開始
            st.title("施策基本情報入力")
            scope = st.selectbox(
                "どのScopeですか？", 
                ["Scope1", "Scope2"], 
                key='default_scope_temp', 
                on_change=store_content, 
                args=('default_scope_persist', 'default_scope_temp'), 
                disabled=True
            )
            ss["user_input"]["Scope"] = scope
            
            if scope == "Scope1":
                equipment_options = [
                    "",
                    "空調(ボイラ)",
                    "空調(冷凍機)",
                    "空調(ウォータチラー空冷式)",
                    "空調(ウォータチラー水冷式)",
                    "空調(GHP)(パッケージ式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "発電",
                    "自動車",
                    "タクシー",
                    "バス",
                    "トラック",
                    "重機/建機(トラック除く)",
                    "船舶",
                    "航空機",
                    "溶解炉",
                    "焼却炉",
                    "生産用ボイラー",
                    "バーナー",
                    "生産用ヒーター",
                    "クリーンルーム用空調(ボイラ)",
                    "クリーンルーム用空調(冷凍機)",
                    "クリーンルーム用空調(ウォータチラー空冷式)",
                    "クリーンルーム用空調(ウォータチラー水冷式)",
                    "クリーンルーム用空調(GHP)(パッケージ式)",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "メッキ槽・電着塗装",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "自家用発電機",
                    "SCOPE1全体",
                    "その他(SCOPE1)"
                ]          
        
                fuel_options = ["", "軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "産業用蒸気", "産業用以外の蒸気", "その他", "全体(カーボンオフセット)"]

                # 設備種フラグが立っている位置を特定し、列名を取得する
                equipment_row_slice = filtered_df.iloc[0]['air_conditioning_boiler': 'total_SCOPE1']
                equipment_target_col = equipment_row_slice[equipment_row_slice == 1].index[0]
                default_equipment_name = equipment_translation_dict_scope1[equipment_target_col]
                # デフォルト値として使えるよう保存
                if 'default_equipment_name_persist' not in ss:
                    ss['default_equipment_name_persist'] = default_equipment_name
                if 'default_equipment_name_temp' not in ss:
                    ss['default_equipment_name_temp'] = ss['default_equipment_name_persist']

                # 燃料種フラグが立っている位置を特定し、列名を取得する
                range_cols = filtered_df.loc[:, 'light_oil': 'non-industrial_steam'].columns.tolist()
                single_cols = ['others','total_carbon_offset']
                cols_to_check = range_cols + single_cols
                fuel_row_slice = filtered_df.iloc[0][cols_to_check]
                fuel_target_col = fuel_row_slice[fuel_row_slice == 1].index[0]
                default_fuel_name = fuel_translation_dict_scope1[fuel_target_col]
                # デフォルト値として使えるよう保存
                if 'default_fuel_name_persist' not in ss:
                    ss['default_fuel_name_persist'] = default_fuel_name
                if 'default_fuel_name_temp' not in ss:
                    ss['default_fuel_name_temp'] = ss['default_fuel_name_persist']

            else:
                equipment_options = [
                    "",
                    "空調(電気)(パッケージ式)",
                    "空調(電気)(冷凍機)",
                    "空調(電気)(ウォータチラー水冷式)",
                    "空調(電気)(ウォータチラー空冷式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "照明",
                    "サーバー機器",
                    "エレベータ",
                    "コンプレッサー",
                    "ポンプ",
                    "送風機/給気・排気ファン",
                    "電気自動車",
                    "電気タクシー",
                    "電気バス",
                    "電動トラック",
                    "織機",
                    "ベルトコンベア",
                    "その他生産用モーター",
                    "溶解炉",
                    "ヒーター",
                    "自動販売機(飲料)",
                    "シャッター",
                    "錠剤印刷機",
                    "錠剤検査機",
                    "集塵機",
                    "攪拌機",
                    "充填機",
                    "包装機",
                    "クリーンルーム用空調(電気)(パッケージ式)",
                    "クリーンルーム用空調(電気)(冷凍機)",
                    "クリーンルーム用空調(電気)(ウォータチラー空冷式)",
                    "クリーンルーム用空調(電気)(ウォータチラー水冷式)",
                    "パソコン",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "旋盤・マシニングセンタ",
                    "スポット溶接",
                    "ブラスター",
                    "樹脂射出成形機",
                    "ゴム射出成形機",
                    "ダイカストマシン",
                    "プレス機",
                    "複合機/コピー機",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "樹脂圧縮成形機",
                    "ゴム圧縮成形機",
                    "樹脂押出成形機",
                    "ゴム押出成形機",
                    "ゴム加硫槽（ゴム二次加硫工程）",
                    "メッキ槽・電着塗装",
                    "生産用チラー_水冷式",
                    "生産用チラー_空冷式",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "真空ポンプ",
                    "放電加工機",
                    "Scope2温水利用先_空調",
                    "Scope2温水利用先_給湯",
                    "Scope2温水利用先_その他",
                    "Scope2冷水利用先_空調",
                    "Scope2冷水利用先_その他",
                    "現場用照明",
                    "曝気・水処理用ブロワ",
                    "その他用途のブロワ",
                    "SCOPE2全体",
                    "その他(SCOPE2)"
                ]          
        
                fuel_options = ["", "温水", "冷水", "電力"]

                # 設備種フラグが立っている位置を特定し、列名を取得する
                equipment_row_slice = filtered_df.iloc[0]['electric_air_conditioning_package_type': 'total_SCOPE2']
                equipment_target_col = equipment_row_slice[equipment_row_slice == 1].index[0]
                default_equipment_name = equipment_translation_dict_scope2[equipment_target_col]
                # デフォルト値として使えるよう保存
                if 'default_equipment_name_persist' not in ss:
                    ss['default_equipment_name_persist'] = default_equipment_name
                if 'default_equipment_name_temp' not in ss:
                    ss['default_equipment_name_temp'] = ss['default_equipment_name_persist']

                # 燃料種フラグが立っている位置を特定し、列名を取得する
                cols_to_check = ['hot_water', 'cold_water', 'electricity']
                fuel_row_slice = filtered_df.iloc[0][cols_to_check]
                fuel_target_col = fuel_row_slice[fuel_row_slice == 1].index[0]
                default_fuel_name = fuel_translation_dict_scope2[fuel_target_col]
                # デフォルト値として使えるよう保存
                if 'default_fuel_name_persist' not in ss:
                    ss['default_fuel_name_persist'] = default_fuel_name
                if 'default_fuel_name_temp' not in ss:
                    ss['default_fuel_name_temp'] = ss['default_fuel_name_persist']
        
            equipment = st.selectbox(
                "どの設備の施策ですか？", 
                equipment_options, 
                key='default_equipment_name_temp', 
                on_change=store_content, 
                args=('default_equipment_name_persist', 'default_equipment_name_temp')
            )
            ss["user_input"]["設備"] = equipment
        
            fuel = st.selectbox(
                "どの燃料ですか？", 
                fuel_options, 
                key='default_fuel_name_temp', 
                on_change=store_content, 
                args=('default_fuel_name_persist', 'default_fuel_name_temp')
            )
            ss["user_input"]["燃料"] = fuel
        
            # テンプレでは、自由入力で固定とする
            formula_template = st.selectbox(
                "式はテンプレですか？", 
                ["1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(自由入力)"], 
                index=4, 
                disabled=True
            )
            ss["user_input"]["テンプレ"] = formula_template
        
            neworold_scope = st.selectbox(
                "燃料転換前or燃料転換後はどのScopeですか？(今回入力していない方の施策について)", 
                ["","Scope1", "Scope2"], 
                key='default_scope_after_fuel_conversion_temp' if ss['default_施策名_persist'].endswith('_1') else 'default_scope_before_fuel_conversion_temp', 
                on_change=store_content, 
                args=('default_scope_after_fuel_conversion_persist', 'default_scope_after_fuel_conversion_temp') if ss['default_施策名_persist'].endswith('_1') else ('default_scope_before_fuel_conversion_persist', 'default_scope_before_fuel_conversion_temp')
            )
            ss["user_input"]["Neworoldscope"] = neworold_scope
        
            if neworold_scope == "Scope1":
                neworold_scope_equipment_options = [
                    "",
                    "空調(ボイラ)",
                    "空調(冷凍機)",
                    "空調(ウォータチラー空冷式)",
                    "空調(ウォータチラー水冷式)",
                    "空調(GHP)(パッケージ式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "発電",
                    "自動車",
                    "タクシー",
                    "バス",
                    "トラック",
                    "重機/建機(トラック除く)",
                    "船舶",
                    "航空機",
                    "溶解炉",
                    "焼却炉",
                    "生産用ボイラー",
                    "バーナー",
                    "生産用ヒーター",
                    "クリーンルーム用空調(ボイラ)",
                    "クリーンルーム用空調(冷凍機)",
                    "クリーンルーム用空調(ウォータチラー空冷式)",
                    "クリーンルーム用空調(ウォータチラー水冷式)",
                    "クリーンルーム用空調(GHP)(パッケージ式)",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "メッキ槽・電着塗装",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "自家用発電機",
                    "SCOPE1全体",
                    "その他(SCOPE1)"
                ]
                neworold_scope_fuel_options = ["","軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "産業用蒸気", "産業用以外の蒸気", "その他", "全体(カーボンオフセット)"]
            else:
                neworold_scope_equipment_options = [
                    "",
                    "空調(電気)(パッケージ式)",
                    "空調(電気)(冷凍機)",
                    "空調(電気)(ウォータチラー水冷式)",
                    "空調(電気)(ウォータチラー空冷式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "照明",
                    "サーバー機器",
                    "エレベータ",
                    "コンプレッサー",
                    "ポンプ",
                    "送風機/給気・排気ファン",
                    "電気自動車",
                    "電気タクシー",
                    "電気バス",
                    "電動トラック",
                    "織機",
                    "ベルトコンベア",
                    "その他生産用モーター",
                    "溶解炉",
                    "ヒーター",
                    "自動販売機(飲料)",
                    "シャッター",
                    "錠剤印刷機",
                    "錠剤検査機",
                    "集塵機",
                    "攪拌機",
                    "充填機",
                    "包装機",
                    "クリーンルーム用空調(電気)(パッケージ式)",
                    "クリーンルーム用空調(電気)(冷凍機)",
                    "クリーンルーム用空調(電気)(ウォータチラー空冷式)",
                    "クリーンルーム用空調(電気)(ウォータチラー水冷式)",
                    "パソコン",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "旋盤・マシニングセンタ",
                    "スポット溶接",
                    "ブラスター",
                    "樹脂射出成形機",
                    "ゴム射出成形機",
                    "ダイカストマシン",
                    "プレス機",
                    "複合機/コピー機",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "樹脂圧縮成形機",
                    "ゴム圧縮成形機",
                    "樹脂押出成形機",
                    "ゴム押出成形機",
                    "ゴム加硫槽（ゴム二次加硫工程）",
                    "メッキ槽・電着塗装",
                    "生産用チラー_水冷式",
                    "生産用チラー_空冷式",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "真空ポンプ",
                    "放電加工機",
                    "Scope2温水利用先_空調",
                    "Scope2温水利用先_給湯",
                    "Scope2温水利用先_その他",
                    "Scope2冷水利用先_空調",
                    "Scope2冷水利用先_その他",
                    "現場用照明",
                    "曝気・水処理用ブロワ",
                    "その他用途のブロワ",
                    "SCOPE2全体",
                    "その他(SCOPE2)"
                ]
                neworold_scope_fuel_options = ["","温水", "冷水", "電力"]
        
            neworold_scope_equipment = st.selectbox(
                "燃料転換前or燃料転換後はどの設備の施策ですか？(今回入力していない方の施策について)", 
                neworold_scope_equipment_options, 
                key='default_equipment_after_fuel_conversion_temp' if ss['default_施策名_persist'].endswith('_1') else 'default_equipment_before_fuel_conversion_temp',
                on_change=store_content, 
                args=('default_equipment_after_fuel_conversion_persist', 'default_equipment_after_fuel_conversion_temp') if ss['default_施策名_persist'].endswith('_1') else ('default_equipment_before_fuel_conversion_persist', 'default_equipment_before_fuel_conversion_temp')
            )
            ss["user_input"]["neworold_scope_設備"] = neworold_scope_equipment
        
            neworold_scope_fuel = st.selectbox(
                "燃料転換前or燃料転換後はどの燃料ですか？(今回入力していない方の施策について)", 
                neworold_scope_fuel_options, 
                key='default_fuel_after_fuel_conversion_temp' if ss['default_施策名_persist'].endswith('_1') else 'default_fuel_before_fuel_conversion_temp', 
                on_change=store_content, 
                args=('default_fuel_after_fuel_conversion_persist', 'default_fuel_after_fuel_conversion_temp') if ss['default_施策名_persist'].endswith('_1') else ('default_fuel_before_fuel_conversion_persist', 'default_fuel_before_fuel_conversion_temp')
            )
            ss["user_input"]["neworold_scope_燃料"] = neworold_scope_fuel
        
            measure_type = st.selectbox(
                "施策の種類はどれですか？(自由入力の場合のみ入力)", 
                ["","1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(緑施策)"], 
                key='default_measure_type_temp', 
                on_change=store_content, 
                args=('default_measure_type_persist', 'default_measure_type_temp')
            )
            ss["user_input"]["施策の種類"] = measure_type
        
            measures = st.text_input(
                "施策名はなんですか？", 
                key='default_施策名_temp', 
                on_change=store_content, 
                args=('default_施策名_persist', 'default_施策名_temp')
            )
            ss["user_input"]["施策名"] = measures
        
            if st.button("次へ"):
                if formula_template.startswith("1"):
                    next_page("page2A")
                elif formula_template.startswith("2"):
                    next_page("page2B")
                elif formula_template.startswith("3"):
                    next_page("page2C")
                elif formula_template.startswith("4"):
                    next_page("page2D")
                elif formula_template.startswith("5") and measure_type == "5(緑施策)":
                    next_page("page2F")
                else:
                    next_page("page2E")

        elif strategy_number == '' :
            st.write('施策ユニークNoを入力してください')
        else:
            st.write('施策ユニークNoが正しくありません')

    elif selected_option == 'jsonファイルを読み込む':
        json_path = Path('saved_inputs.json')
        if json_path.exists():
            with json_path.open(encoding='utf-8') as f:
                data = json.load(f)
        else:
            st.error('saved_inputs.json が見つかりません')
            st.stop() 

        # all_keys = list(data.keys()) 
        # query = st.text_input('施策を検索')
        # candidates = [k for k in all_keys if query.lower() in k.lower()] if query else all_keys

        # # 検索結果をselectboxで選択
        # selected_key = st.selectbox(
        #     '検索結果から施策を選択してください',
        #     options=candidates,
        #     index=0 if candidates else None,
        #     placeholder='該当キーなし'
        # )

        all_keys = list(data.keys()) 
        query = st.text_input('施策を検索')
        candidates = [k for k in all_keys if query.lower() in k.lower()] if query else all_keys

        # 検索結果をselectboxで選択
        selected_key = st.selectbox(
            '施策を選択してください',
            options=candidates if query else all_keys,
            index=None
        )

        if selected_key:
            st.write(f'{selected_key}をテンプレートとして使用します')
            with st.expander("テンプレートの詳細を見る", expanded=False):
                st.write(data[selected_key])
                default_data = data[selected_key]
                ss['default_data'] = default_data
            
            # 読み込んだデータからデフォルト値を設定
            if 'default_施策名_persist' not in ss:
                ss['default_施策名_persist'] = default_data['施策名']
            if 'default_施策名_temp' not in ss:
                ss['default_施策名_temp'] = ss['default_施策名_persist']

            if 'default_scope_persist' not in ss:
                ss['default_scope_persist'] = default_data['Scope']
            if 'default_scope_temp' not in ss:
                ss['default_scope_temp'] = ss['default_scope_persist']

            if 'default_equipment_name_persist' not in ss:
                ss['default_equipment_name_persist'] = default_data['設備']
            if 'default_equipment_name_temp' not in ss:
                ss['default_equipment_name_temp'] = ss['default_equipment_name_persist']
            if 'default_fuel_name_persist' not in ss:
                ss['default_fuel_name_persist'] = default_data['燃料']
            if 'default_fuel_name_temp' not in ss:
                ss['default_fuel_name_temp'] = ss['default_fuel_name_persist']

            # if 'default_一般/専門フラグ_persist' not in ss:
            #     ss['default_一般/専門フラグ_persist'] = 0
            # if 'default_一般/専門フラグ_temp' not in ss:
            #     ss['default_一般/専門フラグ_temp'] = ss['default_一般/専門フラグ_persist']

            # if 'default_施策分類フラグ_persist' not in ss:
            #     ss['default_施策分類フラグ_persist'] = filtered_df['施策分類フラグ'].iloc[0]
            # if 'default_施策分類フラグ_temp' not in ss:
            #     ss['default_施策分類フラグ_temp'] = ss['default_施策分類フラグ_persist']
            
            if 'default_measure_type_persist' not in ss:
                    ss['default_measure_type_persist'] = default_data['施策の種類']
            if 'default_measure_type_temp' not in ss:
                ss['default_measure_type_temp'] = ss['default_measure_type_persist']

            # if default_data['施策の種類'] == '3(燃料転換系_1)':
            #     if 'default_scope_after_fuel_conversion_persist' not in ss: 
            #         ss['default_scope_after_fuel_conversion_persist'] = default_data['Neworoldscope']
            #     if 'default_scope_after_fuel_conversion_temp' not in ss: 
            #         ss['default_scope_after_fuel_conversion_temp'] = ss['default_scope_after_fuel_conversion_persist']
                    
            #     if 'default_equipment_after_fuel_conversion_persist' not in ss:
            #         ss['default_equipment_after_fuel_conversion_persist'] = default_data['neworold_scope_設備']
            #     if 'default_equipment_after_fuel_conversion_temp' not in ss:
            #         ss['default_equipment_after_fuel_conversion_temp'] = ss['default_equipment_after_fuel_conversion_persist']

            #     if 'default_fuel_after_fuel_conversion_persist' not in ss:
            #         ss['default_fuel_after_fuel_conversion_persist'] = default_data['neworold_scope_燃料']
            #     if 'default_fuel_after_fuel_conversion_temp' not in ss:
            #         ss['default_fuel_after_fuel_conversion_temp'] = ss['default_fuel_after_fuel_conversion_persist']

            # elif default_data['施策の種類'] == '4(燃料転換系_2)':
            #     if 'default_scope_before_fuel_conversion_persist' not in ss:
            #         ss['default_scope_before_fuel_conversion_persist'] = default_data['Neworoldscope']
            #     if 'default_scope_before_fuel_conversion_temp' not in ss:
            #         ss['default_scope_before_fuel_conversion_temp'] = ss['default_scope_before_fuel_conversion_persist']
                        
            #     if 'default_equipment_before_fuel_conversion_persist' not in ss:
            #         ss['default_equipment_before_fuel_conversion_persist'] = default_data['neworold_scope_設備']
            #     if 'default_equipment_before_fuel_conversion_temp' not in ss:
            #         ss['default_equipment_before_fuel_conversion_temp'] = ss['default_equipment_before_fuel_conversion_persist']

            #     if 'default_fuel_before_fuel_conversion_persist' not in ss:
            #         ss['default_fuel_before_fuel_conversion_persist'] = default_data['neworold_scope_燃料']
            #     if 'default_fuel_before_fuel_conversion_temp' not in ss:
            #         ss['default_fuel_before_fuel_conversion_temp'] = ss['default_fuel_before_fuel_conversion_persist']

            # else: 
            #     if 'default_scope_before_fuel_conversion_persist' not in ss:
            #         ss['default_scope_before_fuel_conversion_persist']= default_data['Neworoldscope']
            #     if 'default_scope_before_fuel_conversion_temp' not in ss:
            #         ss['default_scope_before_fuel_conversion_temp']= ss['default_scope_before_fuel_conversion_persist']
            #     if 'default_scope_after_fuel_conversion_persist' not in ss:
            #         ss['default_scope_after_fuel_conversion_persist'] = default_data['Neworoldscope']
            #     if 'default_scope_after_fuel_conversion_temp' not in ss:
            #         ss['default_scope_after_fuel_conversion_temp'] = ss['default_scope_after_fuel_conversion_persist']

            if 'default_scope_fuel_conversion_persist' not in ss:
                ss['default_scope_fuel_conversion_persist'] = default_data['Neworoldscope']
            if 'default_scope_fuel_conversion_temp' not in ss:
                ss['default_scope_fuel_conversion_temp'] = ss['default_scope_fuel_conversion_persist']
            
            if 'default_equipment_fuel_conversion_persist' not in ss:
                ss['default_equipment_fuel_conversion_persist'] = default_data['neworold_scope_設備']
            if 'default_equipment_fuel_conversion_temp' not in ss:
                ss['default_equipment_fuel_conversion_temp'] = ss['default_equipment_fuel_conversion_persist']
            
            if 'default_fuel_fuel_conversion_persist' not in ss:
                ss['default_fuel_fuel_conversion_persist'] = default_data['neworold_scope_燃料']
            if 'default_fuel_fuel_conversion_temp' not in ss:
                ss['default_fuel_fuel_conversion_temp'] = ss['default_fuel_fuel_conversion_persist']

            # 入力開始
            st.title("施策基本情報入力")
            scope = st.selectbox(
                "どのScopeですか？", 
                ["Scope1", "Scope2"], 
                key='default_scope_temp', 
                on_change=store_content, 
                args=('default_scope_persist', 'default_scope_temp'), 
                # disabled=True
            )
            ss["user_input"]["Scope"] = scope
            
            if scope == "Scope1":
                equipment_options = [
                    "空調(ボイラ)",
                    "空調(冷凍機)",
                    "空調(ウォータチラー空冷式)",
                    "空調(ウォータチラー水冷式)",
                    "空調(GHP)(パッケージ式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "発電",
                    "自動車",
                    "タクシー",
                    "バス",
                    "トラック",
                    "重機/建機(トラック除く)",
                    "船舶",
                    "航空機",
                    "溶解炉",
                    "焼却炉",
                    "生産用ボイラー",
                    "バーナー",
                    "生産用ヒーター",
                    "クリーンルーム用空調(ボイラ)",
                    "クリーンルーム用空調(冷凍機)",
                    "クリーンルーム用空調(ウォータチラー空冷式)",
                    "クリーンルーム用空調(ウォータチラー水冷式)",
                    "クリーンルーム用空調(GHP)(パッケージ式)",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "メッキ槽・電着塗装",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "自家用発電機",
                    "SCOPE1全体",
                    "その他(SCOPE1)"
                ]          
        
                fuel_options = ["軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "産業用蒸気", "産業用以外の蒸気", "その他", "全体(カーボンオフセット)"]

            else:
                equipment_options = [
                    "空調(電気)(パッケージ式)",
                    "空調(電気)(冷凍機)",
                    "空調(電気)(ウォータチラー水冷式)",
                    "空調(電気)(ウォータチラー空冷式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "照明",
                    "サーバー機器",
                    "エレベータ",
                    "コンプレッサー",
                    "ポンプ",
                    "送風機/給気・排気ファン",
                    "電気自動車",
                    "電気タクシー",
                    "電気バス",
                    "電動トラック",
                    "織機",
                    "ベルトコンベア",
                    "その他生産用モーター",
                    "溶解炉",
                    "ヒーター",
                    "自動販売機(飲料)",
                    "シャッター",
                    "錠剤印刷機",
                    "錠剤検査機",
                    "集塵機",
                    "攪拌機",
                    "充填機",
                    "包装機",
                    "クリーンルーム用空調(電気)(パッケージ式)",
                    "クリーンルーム用空調(電気)(冷凍機)",
                    "クリーンルーム用空調(電気)(ウォータチラー空冷式)",
                    "クリーンルーム用空調(電気)(ウォータチラー水冷式)",
                    "パソコン",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "旋盤・マシニングセンタ",
                    "スポット溶接",
                    "ブラスター",
                    "樹脂射出成形機",
                    "ゴム射出成形機",
                    "ダイカストマシン",
                    "プレス機",
                    "複合機/コピー機",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "樹脂圧縮成形機",
                    "ゴム圧縮成形機",
                    "樹脂押出成形機",
                    "ゴム押出成形機",
                    "ゴム加硫槽（ゴム二次加硫工程）",
                    "メッキ槽・電着塗装",
                    "生産用チラー_水冷式",
                    "生産用チラー_空冷式",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "真空ポンプ",
                    "放電加工機",
                    "Scope2温水利用先_空調",
                    "Scope2温水利用先_給湯",
                    "Scope2温水利用先_その他",
                    "Scope2冷水利用先_空調",
                    "Scope2冷水利用先_その他",
                    "現場用照明",
                    "曝気・水処理用ブロワ",
                    "その他用途のブロワ",
                    "SCOPE2全体",
                    "その他(SCOPE2)"
                ]          
        
                fuel_options = ["温水", "冷水", "電力"]
        
            equipment = st.selectbox(
                "どの設備の施策ですか？", 
                equipment_options, 
                key='default_equipment_name_temp',
                on_change=store_content, 
                args=('default_equipment_name_persist', 'default_equipment_name_temp')
            )
            ss["user_input"]["設備"] = equipment
        
            fuel = st.selectbox(
                "どの燃料ですか？",
                fuel_options, 
                key='default_fuel_name_temp', 
                on_change=store_content, 
                args=('default_fuel_name_persist', 'default_fuel_name_temp')
            )
            ss["user_input"]["燃料"] = fuel
        
            # テンプレでは、自由入力で固定とする
            formula_template = st.selectbox(
                "式はテンプレですか？", 
                ["1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(自由入力)"], 
                index=4, 
                disabled=True
            )
            ss["user_input"]["テンプレ"] = formula_template
        
            neworold_scope = st.selectbox(
                "燃料転換前or燃料転換後はどのScopeですか？(今回入力していない方の施策について)", 
                ["","Scope1", "Scope2"], 
                key='default_scope_fuel_conversion_temp', 
                on_change=store_content, 
                args=('default_scope_fuel_conversion_persist', 'default_scope_fuel_conversion_temp')
            )
            ss["user_input"]["Neworoldscope"] = neworold_scope
        
            if neworold_scope == "Scope1":
                neworold_scope_equipment_options = [
                    "",
                    "空調(ボイラ)",
                    "空調(冷凍機)",
                    "空調(ウォータチラー空冷式)",
                    "空調(ウォータチラー水冷式)",
                    "空調(GHP)(パッケージ式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "発電",
                    "自動車",
                    "タクシー",
                    "バス",
                    "トラック",
                    "重機/建機(トラック除く)",
                    "船舶",
                    "航空機",
                    "溶解炉",
                    "焼却炉",
                    "生産用ボイラー",
                    "バーナー",
                    "生産用ヒーター",
                    "クリーンルーム用空調(ボイラ)",
                    "クリーンルーム用空調(冷凍機)",
                    "クリーンルーム用空調(ウォータチラー空冷式)",
                    "クリーンルーム用空調(ウォータチラー水冷式)",
                    "クリーンルーム用空調(GHP)(パッケージ式)",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "メッキ槽・電着塗装",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "自家用発電機",
                    "SCOPE1全体",
                    "その他(SCOPE1)"
                ]
                neworold_scope_fuel_options = ["","軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "産業用蒸気", "産業用以外の蒸気", "その他", "全体(カーボンオフセット)"]
            else:
                neworold_scope_equipment_options = [
                    "",
                    "空調(電気)(パッケージ式)",
                    "空調(電気)(冷凍機)",
                    "空調(電気)(ウォータチラー水冷式)",
                    "空調(電気)(ウォータチラー空冷式)",
                    "冷蔵/冷凍",
                    "給湯",
                    "照明",
                    "サーバー機器",
                    "エレベータ",
                    "コンプレッサー",
                    "ポンプ",
                    "送風機/給気・排気ファン",
                    "電気自動車",
                    "電気タクシー",
                    "電気バス",
                    "電動トラック",
                    "織機",
                    "ベルトコンベア",
                    "その他生産用モーター",
                    "溶解炉",
                    "ヒーター",
                    "自動販売機(飲料)",
                    "シャッター",
                    "錠剤印刷機",
                    "錠剤検査機",
                    "集塵機",
                    "攪拌機",
                    "充填機",
                    "包装機",
                    "クリーンルーム用空調(電気)(パッケージ式)",
                    "クリーンルーム用空調(電気)(冷凍機)",
                    "クリーンルーム用空調(電気)(ウォータチラー空冷式)",
                    "クリーンルーム用空調(電気)(ウォータチラー水冷式)",
                    "パソコン",
                    "焼鈍炉",
                    "乾燥炉",
                    "焼結炉/焼成炉",
                    "旋盤・マシニングセンタ",
                    "スポット溶接",
                    "ブラスター",
                    "樹脂射出成形機",
                    "ゴム射出成形機",
                    "ダイカストマシン",
                    "プレス機",
                    "複合機/コピー機",
                    "焼入れ炉",
                    "鍛造炉・鍛造加熱炉",
                    "樹脂圧縮成形機",
                    "ゴム圧縮成形機",
                    "樹脂押出成形機",
                    "ゴム押出成形機",
                    "ゴム加硫槽（ゴム二次加硫工程）",
                    "メッキ槽・電着塗装",
                    "生産用チラー_水冷式",
                    "生産用チラー_空冷式",
                    "焼戻し炉",
                    "衣類用乾燥機",
                    "工業用乾燥機",
                    "真空ポンプ",
                    "放電加工機",
                    "Scope2温水利用先_空調",
                    "Scope2温水利用先_給湯",
                    "Scope2温水利用先_その他",
                    "Scope2冷水利用先_空調",
                    "Scope2冷水利用先_その他",
                    "現場用照明",
                    "曝気・水処理用ブロワ",
                    "その他用途のブロワ",
                    "SCOPE2全体",
                    "その他(SCOPE2)"
                ]
                neworold_scope_fuel_options = ["","温水", "冷水", "電力"]
        
            neworold_scope_equipment = st.selectbox(
                "燃料転換前or燃料転換後はどの設備の施策ですか？(今回入力していない方の施策について)", 
                neworold_scope_equipment_options, 
                key='default_equipment_fuel_conversion_temp', 
                on_change=store_content, 
                args=('default_equipment_fuel_conversion_persist', 'default_equipment_fuel_conversion_temp')
            )
            ss["user_input"]["neworold_scope_設備"] = neworold_scope_equipment
        
            neworold_scope_fuel = st.selectbox(
                "燃料転換前or燃料転換後はどの燃料ですか？(今回入力していない方の施策について)", 
                neworold_scope_fuel_options, 
                key='default_fuel_fuel_conversion_temp', 
                on_change=store_content, 
                args=('default_fuel_fuel_conversion_persist', 'default_fuel_fuel_conversion_temp')
            )
            ss["user_input"]["neworold_scope_燃料"] = neworold_scope_fuel
        
            measure_type = st.selectbox(
                "施策の種類はどれですか？(自由入力の場合のみ入力)", 
                ["","1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(緑施策)"], 
                key='default_measure_type_temp', 
                on_change=store_content, 
                args=('default_measure_type_persist', 'default_measure_type_temp')
            )
            ss["user_input"]["施策の種類"] = measure_type
        
            measures = st.text_input(
                "施策名はなんですか？", 
                key='default_施策名_temp', 
                on_change=store_content, 
                args=('default_施策名_persist', 'default_施策名_temp')
            )
            ss["user_input"]["施策名"] = measures
        
            if st.button("次へ"):
                if formula_template.startswith("1"):
                    next_page("page2A")
                elif formula_template.startswith("2"):
                    next_page("page2B")
                elif formula_template.startswith("3"):
                    next_page("page2C")
                elif formula_template.startswith("4"):
                    next_page("page2D")
                elif formula_template.startswith("5") and measure_type == "5(緑施策)":
                    next_page("page2F")
                else:
                    next_page("page2E")
                

# ** 2ページ目A (運用改善系) **
elif ss["page"] == "page2A":
    st.title("運用改善系施策式入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
        "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
        "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }

    # **GHG削減量計算式**
    default_ghg_formula = f"CO2削減量<t-CO2/年>={ss['user_input'].get('設備', '')}{{{ss['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
    ss["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)

    if 'default_GHG削減量（ton-CO2）_persist' not in ss:
        ss['default_GHG削減量（ton-CO2）_persist'] = default_ghg_formula
    if 'default_GHG削減量（ton-CO2）_temp' not in ss:
        ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']

    ghg_reduction_formula = st.text_area(
        "GHG削減量計算式",
        key='default_GHG削減量（ton-CO2）_temp',
        on_change=store_content,
        args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
    )
    ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
            st.success('GHG削減量計算式の<>はきちんと閉じられています')
        else:
            st.error('GHG削減量計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if '\n' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **コスト削減額計算式**
    fuel = ss["user_input"].get("燃料", "")
    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"

    default_cost_formula = f"コスト削減額<円/年>={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
    ss["user_input"].setdefault("コスト削減額計算式", default_cost_formula)

    if 'default_コスト削減額（円/年）_persist' not in ss:
        ss['default_コスト削減額（円/年）_persist'] = default_cost_formula
    if 'default_コスト削減額（円/年）_temp' not in ss:
        ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']

    cost_reduction_formula = st.text_area(
        "コスト削減額計算式",
        key='default_コスト削減額（円/年）_temp',
        on_change=store_content,
        args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
    )
    ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
            st.success('コスト削減額計算式の<>はきちんと閉じられています')
        else:
            st.error('コスト削減額計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if '\n' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **投資額計算式**
    ss["user_input"].setdefault("投資額計算式", "なし")

    if 'default_投資額（円）_persist' not in ss:
        ss['default_投資額（円）_persist'] = 'なし'
    if 'default_投資額（円）_temp' not in ss:
        ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']

    investment_formula = st.text_area(
        "投資額計算式",
        key='default_投資額（円）_temp',
        on_change=store_content,
        args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
    )
    ss["user_input"]["投資額計算式"] = investment_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
            st.success('投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if '\n' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **追加投資額計算式**
    ss["user_input"].setdefault("追加投資額計算式", "なし")

    if 'default_追加投資額（円）_persist' not in ss:
        ss['default_追加投資額（円）_persist'] = 'なし'
    if 'default_追加投資額（円）_temp' not in ss:
        ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

    additional_investment_formula = st.text_area(
        "追加投資額計算式",
        key='default_追加投資額（円）_temp',
        on_change=store_content,
        args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
    )
    ss["user_input"]["追加投資額計算式"] = additional_investment_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
            st.success('追加投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('追加投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if '\n' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    st.subheader("取得済みインプット")
    default_input_name = f"{ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
    ss["user_input"].setdefault("取得済みインプットの名前", default_input_name)
    if 'default_acquired_input_1_persist' not in ss:
        ss['default_acquired_input_1_persist'] = default_input_name
    if 'default_acquired_input_1_temp' not in ss:
        ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']

    acquired_input_1_name = st.text_input(
        "インプットの名前",
        key='default_acquired_input_1_temp',
        on_change=store_content,
        args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
    )
    ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

    ss["user_input"].setdefault("取得済みインプットの数字", 200.0)
    if 'default_acquired_input_1_value_persist' not in ss:
        ss['default_acquired_input_1_value_persist'] = 200.0
    if 'default_acquired_input_1_value_temp' not in ss:
        ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']
    
    acquired_input_1_value = st.number_input(
        "数字",
        min_value=0.0,
        step=1.0,
        key='default_acquired_input_1_value_temp',
        on_change=store_content,
        args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
    )
    ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

    ss["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
    if 'default_acquired_input_1_unit_persist' not in ss:
        ss['default_acquired_input_1_unit_persist'] = 't-CO2'
    if 'default_acquired_input_1_unit_temp' not in ss:
        ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']

    acquired_input_1_unit = st.text_input(
        "単位",
        key='default_acquired_input_1_unit_temp',
        on_change=store_content,
        args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
    )
    ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

    # **追加インプット 6個**
    for i in range(6):
        st.subheader(f"追加インプット {i+1}")

        name_key = f"追加インプット{i+1}の名前"
        num_key = f"追加インプット{i+1}の数字"
        unit_key = f"追加インプット{i+1}の単位"
        
        if f'default_additional_input_{i+1}_persist' not in ss:
            ss[f'default_additional_input_{i+1}_persist'] = "対象設備の中で施策を実施する設備の割合" if i == 0 else ""
        if f'default_additional_input_{i+1}_temp' not in ss:
            ss[f'default_additional_input_{i+1}_temp'] = ss[f'default_additional_input_{i+1}_persist']

        if f'default_additional_input_{i+1}_value_persist' not in ss:
            ss[f'default_additional_input_{i+1}_value_persist'] = 50.0 if i == 0 else 0.0
        if f'default_additional_input_{i+1}_value_temp' not in ss:
            ss[f'default_additional_input_{i+1}_value_temp'] = ss[f'default_additional_input_{i+1}_value_persist']

        if f'default_additional_input_{i+1}_unit_persist' not in ss:
            ss[f'default_additional_input_{i+1}_unit_persist'] = "%" if i == 0 else ""
        if f'default_additional_input_{i+1}_unit_temp' not in ss:
            ss[f'default_additional_input_{i+1}_unit_temp'] = ss[f'default_additional_input_{i+1}_unit_persist']

        key_name_temp = f'default_additional_input_{i+1}_temp'
        key_name_persist = f'default_additional_input_{i+1}_persist'
        key_value_temp = f'default_additional_input_{i+1}_value_temp'
        key_value_persist = f'default_additional_input_{i+1}_value_persist'
        key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
        key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

        ss["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
        additional_input_name = st.text_input(
            name_key,
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][name_key] = additional_input_name

        ss["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
        additional_input_val = st.number_input(
            num_key,
            min_value=0.0,
            step=1.0,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][num_key] = additional_input_val

        ss["user_input"].setdefault(unit_key, "%" if i == 0 else "")
        additional_input_unit = st.text_input(
            unit_key,
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][unit_key] = additional_input_unit

    # 燃料取得
    fuel = ss["user_input"].get("燃料", "")

    # **事前定義された値**
    if fuel == '電力':
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数' 
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = 0.000434
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = 't-CO2/kWh'
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = '電気料金'
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = 22.97
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = '円/kWh'
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    else:
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数'
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = '電気料金'
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = np.nan
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = ''
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = ''
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    predefined_values = [
        ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
        ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
        ("想定稼働年数", 10, "年", "")
    ]

    for name, value, unit, description in predefined_values:
        st.subheader(f"規定値: {name}")
        
        # name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
        # value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

        # # セッションステートにデフォルト値をセット
        # ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
        # ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
        # ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
        # ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

        if name == '電気の排出係数':
            key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
            key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
            key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
            key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
            key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
            key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
        elif name == '電気料金':
            key_name_temp = 'default_individual_value(electric_bill)_temp'
            key_name_persist = 'default_individual_value(electric_bill)_persist'
            key_value_temp = 'default_individual_value(electric_bill)_value_temp'
            key_value_persist = 'default_individual_value(electric_bill)_value_persist'
            key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
            key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
        elif name == "想定稼働年数":
            key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
            key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
            key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
            key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
            key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
            key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
            key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
            key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

        # ユーザー入力欄
        ind_val_name = st.text_input(
            f"規定値({name})の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値({name})の名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値({name})の数字",
            min_value=0.0,
            step=float(0.000001 if name == "電気の排出係数" else 0.01),
            format="%.6f" if name == "電気の排出係数" else "%.2f",
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値({name})の数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値({name})の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値({name})の単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値({name})の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値({name})の説明"] = ind_val_description
    
    # **追加の規定値 13個**
    for i in range(13):
        st.subheader(f"規定値 {i+1}")
        fuel = ss["user_input"].get("燃料", "")
        value_format = "%.2f"
    
        if i == 0:
            name, unit = "省エネ率", "%"
            value = None
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 1:
            name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
            value_format = "%.6f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 2:
            name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
            
        elif i == 5:
            # `fuel_heat` から燃料の熱量を取得
            name, value, unit, description = fuel_heat.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        else:
            name, value, unit, description = "", None, "", ""
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
            
        value = 0.0 if value is None else float(value)

        ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"規定値{i+1}_説明", description)

        key_name_temp = f'default_individual_value_{i+1}_temp'
        key_name_persist = f'default_individual_value_{i+1}_persist'
        key_value_temp = f'default_individual_value_{i+1}_value_temp'
        key_value_persist = f'default_individual_value_{i+1}_value_persist'
        key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
        key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
        key_description_temp = f'default_individual_value_{i+1}_description_temp'
        key_description_persist = f'default_individual_value_{i+1}_description_persist'
        
        ind_val_name = st.text_input(
            f"規定値 {i+1} の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値{i+1}_名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値 {i+1} の数字",
            min_value=0.0,
            step=0.000001 if i == 1 else 0.01,
            format=value_format,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値{i+1}_数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値 {i+1} の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値{i+1}_単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値 {i+1} の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値{i+1}_説明"] = ind_val_description

    # **推測値テンプレートの選択**
    if 'default_prediction_template_persist' not in ss:
        ss['default_prediction_template_persist'] = None
    if 'default_prediction_template_temp' not in ss:
        ss['default_prediction_template_temp'] = ss['default_prediction_template_persist']
    
    prediction_template = st.selectbox(
        "推測値のテンプレはどれを使用しますか？", 
        ["1(容量推測)", "2(台数推測)", "3(自由入力)"],
        key='default_prediction_template_temp',
        on_change=store_content,
        args=('default_prediction_template_persist', 'default_prediction_template_temp')
    )
    ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
    ss["user_input"]["推測値のテンプレ"] = prediction_template

    col1, col2 = st.columns(2)
    with col1:
        if st.button("入力を確定", key="submit"):
            prediction_template = ss["user_input"].get("推測値のテンプレ", "")
            ss["previous_page"] = ss["page"]
            if prediction_template.startswith("1"):
                next_page("page3A")
            elif prediction_template.startswith("2"):
                next_page("page3B")
            else:
                next_page("page3C")

    with col2:
        if st.button("エラーチェック", key="check"):
            # チェックする計算式の辞書
            target_formula_dict = {
                "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                "投資額計算式": ss["user_input"]["投資額計算式"],
                "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
            }
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")
    
    if st.button("戻る"):
        next_page("page1")


elif ss["page"] == "page2B":
    st.title("設備投資系式入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
    "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
    "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }

    # **GHG削減量計算式**
    default_ghg_formula = f"CO2削減量<t-CO2/年>={ss['user_input'].get('設備', '')}{{{ss['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
    ss["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)

    if 'default_GHG削減量（ton-CO2）_persist' not in ss:
        ss['default_GHG削減量（ton-CO2）_persist'] = default_ghg_formula
    if 'default_GHG削減量（ton-CO2）_temp' not in ss:
        ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']
    
    ghg_reduction_formula = st.text_area(
        "GHG削減量計算式",
        key='default_GHG削減量（ton-CO2）_temp',
        on_change= store_content,
        args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
    )
    ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
            st.success('GHG削減量計算式の<>はきちんと閉じられています')
        else:
            st.error('GHG削減量計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if '\n' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **コスト削減額計算式**
    fuel = ss["user_input"].get("燃料", "")
    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"
    default_cost_formula = f"コスト削減額<円/年>={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"

    if 'default_コスト削減額（円/年）_persist' not in ss:
        ss['default_コスト削減額（円/年）_persist'] = default_cost_formula
    if 'default_コスト削減額（円/年）_temp' not in ss:
        ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']
    
    ss["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
    cost_reduction_formula = st.text_area(
        "コスト削減額計算式",
        key='default_コスト削減額（円/年）_temp',
        on_change=store_content,
        args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
    )
    ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
            st.success('コスト削減額計算式の<>はきちんと閉じられています')
        else:
            st.error('コスト削減額計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if '\n' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **投資額計算式**
    ss["user_input"].setdefault("投資額計算式", "投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値投資額原単位<円/単位>")

    if 'default_投資額（円）_persist' not in ss:
        ss['default_投資額（円）_persist'] = '投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値投資額原単位<円/単位>'
    if 'default_投資額（円）_temp' not in ss:
        ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']
    
    investment_amount_formula = st.text_area(
        "投資額計算式",
        key='default_投資額（円）_temp',
        on_change=store_content,
        args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
    )
    ss["user_input"]["投資額計算式"] = investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
            st.success('投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if '\n' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **追加投資額計算式**
    ss["user_input"].setdefault("追加投資額計算式", "追加投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値追加投資額原単位<円/単位>")

    if 'default_追加投資額（円）_persist' not in ss:
        ss['default_追加投資額（円）_persist'] = '追加投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値追加投資額原単位<円/単位>'
    if 'default_追加投資額（円）_temp' not in ss:
        ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']
    
    additional_investment_amount_formula = st.text_area(
        "追加投資額計算式",
        key='default_追加投資額（円）_temp',
        on_change=store_content,
        args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
    )
    ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
            st.success('追加投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('追加投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if '\n' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    st.subheader("取得済みインプット")
    default_input_name = f"{ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
    ss["user_input"].setdefault("取得済みインプットの名前", default_input_name)
    if 'default_acquired_input_1_persist' not in ss:
        ss['default_acquired_input_1_persist'] = default_input_name
    if 'default_acquired_input_1_temp' not in ss:
        ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']

    acquired_input_1_name = st.text_input(
        "インプットの名前",
        key='default_acquired_input_1_temp',
        on_change=store_content,
        args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
    )
    ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

    ss["user_input"].setdefault("取得済みインプットの数字", 200.0)
    if 'default_acquired_input_1_value_persist' not in ss:
        ss['default_acquired_input_1_value_persist'] = 200.0
    if 'default_acquired_input_1_value_temp' not in ss:
        ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']
    
    acquired_input_1_value = st.number_input(
        "数字",
        min_value=0.0,
        step=1.0,
        key='default_acquired_input_1_value_temp',
        on_change=store_content,
        args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
    )
    ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

    ss["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
    if 'default_acquired_input_1_unit_persist' not in ss:
        ss['default_acquired_input_1_unit_persist'] = 't-CO2'
    if 'default_acquired_input_1_unit_temp' not in ss:
        ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']
    
    acquired_input_1_unit = st.text_input(
        "単位",
        key='default_acquired_input_1_unit_temp',
        on_change=store_content,
        args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
    )
    ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

    # **追加インプット 6個**
    for i in range(6):
        st.subheader(f"追加インプット {i+1}")

        name_key = f"追加インプット{i+1}の名前"
        num_key = f"追加インプット{i+1}の数字"
        unit_key = f"追加インプット{i+1}の単位"

        if f'default_additional_input_{i+1}_persist' not in ss:
            ss[f'default_additional_input_{i+1}_persist'] = '対象設備の中で施策を実施する設備の割合' if i == 0 else '必要な代表値' if i == 1 else ''
        if f'default_additional_input_{i+1}_temp' not in ss:
            ss[f'default_additional_input_{i+1}_temp'] = ss[f'default_additional_input_{i+1}_persist']

        if f'default_additional_input_{i+1}_value_persist' not in ss:
            ss[f'default_additional_input_{i+1}_value_persist'] = 50.0 if i == 0 else 0.0
        if f'default_additional_input_{i+1}_value_temp' not in ss:
            ss[f'default_additional_input_{i+1}_value_temp'] = ss[f'default_additional_input_{i+1}_value_persist']

        if f'default_additional_input_{i+1}_unit_persist' not in ss:
            ss[f'default_additional_input_{i+1}_unit_persist'] = '%' if i == 0 else '単位' if i == 1 else ''
        if f'default_additional_input_{i+1}_unit_temp' not in ss:
            ss[f'default_additional_input_{i+1}_unit_temp'] = ss[f'default_additional_input_{i+1}_unit_persist']
        
        key_name_temp = f'default_additional_input_{i+1}_temp'
        key_name_persist = f'default_additional_input_{i+1}_persist'
        key_value_temp = f'default_additional_input_{i+1}_value_temp'
        key_value_persist = f'default_additional_input_{i+1}_value_persist'
        key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
        key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

        # 入力フォーム
        additional_input_name = st.text_input(
            name_key,
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][name_key] = additional_input_name

        additional_input_val = st.number_input(
            num_key,
            min_value=0.0,
            step=1.0,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][num_key] = additional_input_val

        additional_input_unit = st.text_input(
            unit_key,
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][unit_key] = additional_input_unit
    
    # 燃料取得
    fuel = ss["user_input"].get("燃料", "")

    # **事前定義された値**
    if fuel == '電力':
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数' 
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = 0.000434
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = 't-CO2/kWh'
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = '電気料金'
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = 22.97
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = '円/kWh'
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    else:
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = ''
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = np.nan
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = ''
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = ''
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    predefined_values = [
        ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
        ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
        ("想定稼働年数", 10, "年", "")
    ]

    for name, value, unit, description in predefined_values:
        st.subheader(f"規定値: {name}")
        
        name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
        value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

        # セッションステートにデフォルト値をセット
        ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
        ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
        ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
        ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

        if name == '電気の排出係数':
            key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
            key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
            key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
            key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
            key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
            key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
        elif name == '電気料金':
            key_name_temp = 'default_individual_value(electric_bill)_temp'
            key_name_persist = 'default_individual_value(electric_bill)_persist'
            key_value_temp = 'default_individual_value(electric_bill)_value_temp'
            key_value_persist = 'default_individual_value(electric_bill)_value_persist'
            key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
            key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
        elif name == "想定稼働年数":
            key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
            key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
            key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
            key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
            key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
            key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
            key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
            key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

        # ユーザー入力欄
        ind_val_name = st.text_input(
            f"規定値({name})の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値({name})の名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値({name})の数字",
            min_value=0.0,
            step=float(0.000001 if name == "電気の排出係数" else 0.01),
            format="%.6f" if name == "電気の排出係数" else "%.2f",
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値({name})の数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値({name})の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値({name})の単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値({name})の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値({name})の説明"] = ind_val_description
    
    # **追加の規定値 13個**
    for i in range(13):
        st.subheader(f"規定値 {i+1}")
        fuel = ss["user_input"].get("燃料", "")
        value_format = "%.2f"

        if i == 0:
            name, unit = "省エネ率", "%"
            value = None
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 1:
            name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
            value_format = "%.6f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 2:
            name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 3:
            name, unit = "代表値投資額原単位", "円/単位"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 4:
            name, unit = "代表値追加投資額原単位", "円/単位"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 5:
            # `fuel_heat` から燃料の熱量を取得
            name, value, unit, description = fuel_heat.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        else:
            name, value, unit, description = "", None, "", ""
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        value = 0.0 if value is None else float(value)
        
        ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"規定値{i+1}_説明", description)

        key_name_temp = f'default_individual_value_{i+1}_temp'
        key_name_persist = f'default_individual_value_{i+1}_persist'
        key_value_temp = f'default_individual_value_{i+1}_value_temp'
        key_value_persist = f'default_individual_value_{i+1}_value_persist'
        key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
        key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
        key_description_temp = f'default_individual_value_{i+1}_description_temp'
        key_description_persist = f'default_individual_value_{i+1}_description_persist'
        
        ind_val_name = st.text_input(
            f"規定値 {i+1} の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値{i+1}_名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値 {i+1} の数字",
            min_value=0.0,
            step=0.000001 if i == 1 else 0.01,
            format=value_format,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値{i+1}_数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値 {i+1} の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値{i+1}_単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値 {i+1} の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値{i+1}_説明"] = ind_val_description

    # **推測値テンプレートの選択**
    if 'default_prediction_template_persist' not in ss:
        ss['default_prediction_template_persist'] = None
    if 'default_prediction_template_temp' not in ss:
        ss['default_prediction_template_temp'] = ss['default_prediction_template_persist']

    prediction_template = st.selectbox(
        "推測値のテンプレはどれを使用しますか？", 
        ["1(容量推測)", "2(台数推測)", "3(自由入力)"],
        key='default_prediction_template_temp',
        on_change=store_content,
        args=('default_prediction_template_persist', 'default_prediction_template_temp')
    )
    ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
    ss["user_input"]["推測値のテンプレ"] = prediction_template

    col1, col2 = st.columns(2)
    with col1:
        if st.button("入力を確定", key="submit"):
            prediction_template = ss["user_input"].get("推測値のテンプレ", "")
            ss["previous_page"] = ss["page"]
            if prediction_template.startswith("1"):
                next_page("page3A")
            elif prediction_template.startswith("2"):
                next_page("page3B")
            else:
                next_page("page3C")
    with col2:
        if st.button("エラーチェック", key="check"):
            # チェックする計算式の辞書
            target_formula_dict = {
                "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                "投資額計算式": ss["user_input"]["投資額計算式"],
                "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
            }
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")
    
    if st.button("戻る"):
        next_page("page1")


elif ss["page"] == "page2C":
    st.title("燃料転換系_1式入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
    "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
    "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }

    # **GHG削減量計算式**
    default_ghg_formula = f"CO2削減量<t-CO2/年>={ss['user_input'].get('設備', '')}{{{ss['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>"
    ss["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)

    if 'default_GHG削減量（ton-CO2）_persist' not in ss:
        ss['default_GHG削減量（ton-CO2）_persist'] = default_ghg_formula
    if 'default_GHG削減量（ton-CO2）_temp' not in ss:
        ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']

    ghg_reduction_formula = st.text_area(
        "GHG削減量計算式",
        key='default_GHG削減量（ton-CO2）_temp',
        on_change= store_content,
        args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
    )
    ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
            st.success('GHG削減量計算式の<>はきちんと閉じられています')
        else:
            st.error('GHG削減量計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if '\n' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **コスト削減額計算式**
    fuel = ss["user_input"].get("燃料", "")
    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"

    default_cost_formula = f"コスト削減額<円/年>={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>÷{emission_factor_str}×{fuel_price_str}"
    ss["user_input"].setdefault("コスト削減額計算式", default_cost_formula)

    if 'default_コスト削減額（円/年）_persist' not in ss:
        ss['default_コスト削減額（円/年）_persist'] = default_cost_formula
    if 'default_コスト削減額（円/年）_temp' not in ss:
        ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']

    cost_reduction_formula = st.text_area(
        "コスト削減額計算式",
        key='default_コスト削減額（円/年）_temp',
        on_change=store_content,
        args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
    )
    ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
            st.success('コスト削減額計算式の<>はきちんと閉じられています')
        else:
            st.error('コスト削減額計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if '\n' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **投資額計算式**
    ss["user_input"].setdefault("投資額計算式", "投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値投資額原単位<円/単位>")

    if 'default_投資額（円）_persist' not in ss:
        ss['default_投資額（円）_persist'] = '投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値投資額原単位<円/単位>'
    if 'default_投資額（円）_temp' not in ss:
        ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']
    
    investment_amount_formula = st.text_area(
        "投資額計算式",
        key='default_投資額（円）_temp',
        on_change=store_content,
        args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
    )
    ss["user_input"]["投資額計算式"] = investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
            st.success('投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if '\n' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **追加投資額計算式**
    ss["user_input"].setdefault("追加投資額計算式", "追加投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値追加投資額原単位<円/単位>")
    
    if 'default_追加投資額（円）_persist' not in ss:
        ss['default_追加投資額（円）_persist'] = '追加投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値追加投資額原単位<円/単位>'
    if 'default_追加投資額（円）_temp' not in ss:
        ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

    additional_investment_amount_formula = st.text_area(
        "追加投資額計算式",
        key='default_追加投資額（円）_temp',
        on_change=store_content,
        args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
    )
    ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
            st.success('追加投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('追加投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if '\n' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    st.subheader("取得済みインプット")
    default_input_name = f"{ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
    ss["user_input"].setdefault("取得済みインプットの名前", default_input_name)
    if 'default_acquired_input_1_persist' not in ss:
        ss['default_acquired_input_1_persist'] = default_input_name
    if 'default_acquired_input_1_temp' not in ss:
        ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']

    acquired_input_1_name = st.text_input(
        "インプットの名前",
        key='default_acquired_input_1_temp',
        on_change=store_content,
        args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
    )
    ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

    ss["user_input"].setdefault("取得済みインプットの数字", 200.0)
    if 'default_acquired_input_1_value_persist' not in ss:
        ss['default_acquired_input_1_value_persist'] = 200.0
    if 'default_acquired_input_1_value_temp' not in ss:
        ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']

    acquired_input_1_value = st.number_input(
        "数字",
        min_value=0.0,
        step=1.0,
        key='default_acquired_input_1_value_temp',
        on_change=store_content,
        args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
    )
    ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

    ss["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
    if 'default_acquired_input_1_unit_persist' not in ss:
        ss['default_acquired_input_1_unit_persist'] = 't-CO2'
    if 'default_acquired_input_1_unit_temp' not in ss:
        ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']
    
    acquired_input_1_unit = st.text_input(
        "単位",
        key='default_acquired_input_1_unit_temp',
        on_change=store_content,
        args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
    )
    ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

    # **追加インプット 6個**
    for i in range(6):
        st.subheader(f"追加インプット {i+1}")

        name_key = f"追加インプット{i+1}の名前"
        num_key = f"追加インプット{i+1}の数字"
        unit_key = f"追加インプット{i+1}の単位"

        if f'default_additional_input_{i+1}_persist' not in ss:
            ss[f'default_additional_input_{i+1}_persist'] = '対象設備の中で施策を実施する設備の割合' if i == 0 else '必要な代表値' if i == 1 else ''
        if f'default_additional_input_{i+1}_temp' not in ss:
            ss[f'default_additional_input_{i+1}_temp'] = ss[f'default_additional_input_{i+1}_persist']

        if f'default_additional_input_{i+1}_value_persist' not in ss:
            ss[f'default_additional_input_{i+1}_value_persist'] = 50.0 if i == 0 else 0.0
        if f'default_additional_input_{i+1}_value_temp' not in ss:
            ss[f'default_additional_input_{i+1}_value_temp'] = ss[f'default_additional_input_{i+1}_value_persist']

        if f'default_additional_input_{i+1}_unit_persist' not in ss:
            ss[f'default_additional_input_{i+1}_unit_persist'] = '%' if i == 0 else '単位' if i == 1 else ''
        if f'default_additional_input_{i+1}_unit_temp' not in ss:
            ss[f'default_additional_input_{i+1}_unit_temp'] = ss[f'default_additional_input_{i+1}_unit_persist']
        
        key_name_temp = f'default_additional_input_{i+1}_temp'
        key_name_persist = f'default_additional_input_{i+1}_persist'
        key_value_temp = f'default_additional_input_{i+1}_value_temp'
        key_value_persist = f'default_additional_input_{i+1}_value_persist'
        key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
        key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

        # 入力フォーム
        additional_input_name = st.text_input(
            name_key,
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][name_key] = additional_input_name

        additional_input_val = st.number_input(
            num_key,
            min_value=0.0,
            step=1.0,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][num_key] = additional_input_val

        additional_input_unit = st.text_input(
            unit_key,
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][unit_key] = additional_input_unit

    # 燃料取得
    fuel = ss["user_input"].get("燃料", "")

    # **事前定義された値**
    if fuel == '電力':
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数' 
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = 0.000434
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = 't-CO2/kWh'
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = '電気料金'
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = 22.97
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = '円/kWh'
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    else:
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = ''
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = np.nan
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = ''
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = ''
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']
    
    predefined_values = [
        ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
        ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
        ("想定稼働年数", 10, "年", "")
    ]

    for name, value, unit, description in predefined_values:
        st.subheader(f"規定値: {name}")
        
        name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
        value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

        # セッションステートにデフォルト値をセット
        ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
        ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
        ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
        ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

        if name == '電気の排出係数':
            key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
            key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
            key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
            key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
            key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
            key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
        elif name == '電気料金':
            key_name_temp = 'default_individual_value(electric_bill)_temp'
            key_name_persist = 'default_individual_value(electric_bill)_persist'
            key_value_temp = 'default_individual_value(electric_bill)_value_temp'
            key_value_persist = 'default_individual_value(electric_bill)_value_persist'
            key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
            key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
        elif name == "想定稼働年数":
            key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
            key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
            key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
            key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
            key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
            key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
            key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
            key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

        # ユーザー入力欄
        ind_val_name = st.text_input(
            f"規定値({name})の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値({name})の名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値({name})の数字",
            min_value=0.0,
            step=float(0.000001 if name == "電気の排出係数" else 0.01),
            format="%.6f" if name == "電気の排出係数" else "%.2f",
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値({name})の数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値({name})の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値({name})の単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値({name})の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値({name})の説明"] = ind_val_description

    # **追加の規定値 13個**
    for i in range(13):
        st.subheader(f"規定値 {i+1}")
        fuel = ss["user_input"].get("燃料", "")
        equipment = ss["user_input"].get("設備", "")
        neworold_scope_fuel = ss["user_input"].get("neworold_scope_燃料", "")
        neworold_scope_equipment = ss["user_input"].get("neworold_scope_設備", "")
        value_format = "%.2f"
        
        if i == 1:
            name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
            value_format = "%.6f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 2:
            name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 3:
            name, unit = "代表値投資額原単位", "円/単位"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 4:
            name, unit = "代表値追加投資額原単位", "円/単位"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 5:
            # `fuel_heat` から燃料の熱量を取得
            name, value, unit, description = fuel_heat.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 6:
            name, unit = f"旧{equipment}効率", "%"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 7:
            name, unit = f"新{neworold_scope_equipment}効率", "%"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 8:
            name, value, unit, description = emission_factors.get(neworold_scope_fuel, ("", None, "", ""))
            value_format = "%.6f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 9:
            name, value, unit, description = fuel_prices.get(neworold_scope_fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 10:
            name, value, unit, description = fuel_heat.get(neworold_scope_fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        else:
            name, value, unit, description = "", None, "", ""
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        value = 0.0 if value is None else float(value)
        
        ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"規定値{i+1}_説明", description)

        key_name_temp = f'default_individual_value_{i+1}_temp'
        key_name_persist = f'default_individual_value_{i+1}_persist'
        key_value_temp = f'default_individual_value_{i+1}_value_temp'
        key_value_persist = f'default_individual_value_{i+1}_value_persist'
        key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
        key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
        key_description_temp = f'default_individual_value_{i+1}_description_temp'
        key_description_persist = f'default_individual_value_{i+1}_description_persist'
        
        ind_val_name = st.text_input(
            f"規定値 {i+1} の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値{i+1}_名前"] = ind_val_name

        # val_key = f"規定値{i+1}_数字"
        # # セッションステートの値を取得し、型をチェック
        # current_value = ss["user_input"].get(val_key, 0.0)
        # # 値が `None` なら 0.0 を設定
        # if current_value is None:
        #     current_value = 0.0
        # # 文字列の場合は float に変換（空文字 `""` の場合は 0.0 にする）
        # elif isinstance(current_value, str):
        #     try:
        #         current_value = float(current_value) if current_value.strip() else 0.0
        #     except ValueError:
        #         current_value = 0.0  # 数値に変換できなければ 0.0 にする
        
        # セッションステートの値を取得し、型をチェック
        current_value = ss[key_value_temp]
        # 値が `None` なら 0.0 を設定
        if current_value is None:
            current_value = 0.0
        # 文字列の場合は float に変換（空文字 `""` の場合は 0.0 にする）
        elif isinstance(current_value, str):
            try:
                current_value = float(current_value) if current_value.strip() else 0.0
            except ValueError:
                current_value = 0.0  # 数値に変換できなければ 0.0 にする
        
        # Streamlit の number_input に渡す
        ind_val_val = st.number_input(
            f"規定値{i+1}_数字",
            min_value=0.0,
            step=1.0 if value_format == "%.2f" else 0.000001,
            format=value_format,  # 小数点以下6桁を強制適用
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値{i+1}_数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値 {i+1} の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値{i+1}_単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値 {i+1} の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値{i+1}_説明"] = ind_val_description
    
    # **推測値テンプレートの選択**
    if 'default_prediction_template_persist' not in ss:
        ss['default_prediction_template_persist'] = None
    if 'default_prediction_template_temp' not in ss:
        ss['default_prediction_template_temp'] = ss['default_prediction_template_persist']
    
    prediction_template = st.selectbox(
        "推測値のテンプレはどれを使用しますか？", 
        ["1(容量推測)", "2(台数推測)", "3(自由入力)"],
        key='default_prediction_template_temp',
        on_change=store_content,
        args=('default_prediction_template_persist', 'default_prediction_template_temp')
    )

    ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
    ss["user_input"]["推測値のテンプレ"] = prediction_template

    col1, col2 = st.columns(2)
    with col1:
        if st.button("入力を確定", key="submit"):
            prediction_template = ss["user_input"].get("推測値のテンプレ", "")
            ss["previous_page"] = ss["page"]
            if prediction_template.startswith("1"):
                next_page("page3A")
            elif prediction_template.startswith("2"):
                next_page("page3B")
            else:
                next_page("page3C")
    with col2:
        if st.button("エラーチェック", key="check"):
            # チェックする計算式の辞書
            target_formula_dict = {
                "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                "投資額計算式": ss["user_input"]["投資額計算式"],
                "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
            }
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")
    
    if st.button("戻る"):
        next_page("page1")


elif ss["page"] == "page2D":
    st.title("燃料転換系_2式入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
    "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
    "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }


    fuel = ss["user_input"].get("燃料", "")
    equipment = ss["user_input"].get("設備", "")
    neworold_scope_equipment = ss["user_input"].get("neworold_scope_設備", "")
    neworold_fuel = ss["user_input"].get("neworold_scope_燃料", "")
    
    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
        heat_str = "3.6<MJ/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        heat_str = "都市ガス{13A}の熱量<MJ/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        heat_name, _, heat_unit, _ = fuel_heat.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"
        heat_str = f"{heat_name}<{heat_unit}>"
    if neworold_fuel == "電力":
        neworold_fuel_emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        neworold_fuel_fuel_price_str = "電気料金<円/kWh>"
        neworold_heat_str = "3.6<MJ/kWh>"
    elif neworold_fuel == "都市ガス":
        neworold_fuel_emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        neworold_fuel_fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        neworold_heat_str = "都市ガス{13A}の熱量<MJ/㎥>"
    else:
        neworold_fuel_emission_name, _, neworold_fuel_emission_unit, _ = emission_factors.get(neworold_fuel, ("", 0, "", ""))
        neworold_fuel_price_name, _, neworold_fuel_price_unit, _ = fuel_prices.get(neworold_fuel, ("", 0, "", ""))
        neworold_fuel_heat_name, _, neworold_fuel_heat_unit, _ = fuel_heat.get(neworold_fuel, ("", 0, "", ""))
        neworold_fuel_emission_factor_str = f"{neworold_fuel}の排出係数<{neworold_fuel_emission_unit}>"
        neworold_fuel_fuel_price_str = f"{neworold_fuel_price_name}<{neworold_fuel_price_unit}>"
        neworold_heat_str = f"{neworold_fuel_heat_name}<{neworold_fuel_heat_unit}>"
    
    # **GHG削減量計算式**
    default_ghg_formula = f"CO2削減量<t-CO2/年>=(-1)×{neworold_scope_equipment}{{{neworold_fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>÷{neworold_fuel_emission_factor_str}×{neworold_heat_str}×旧{neworold_scope_equipment}効率÷新{equipment}効率×{heat_str}×{emission_factor_str}"
    ss["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)

    if 'default_GHG削減量（ton-CO2）_persist' not in ss:
        ss['default_GHG削減量（ton-CO2）_persist'] = default_ghg_formula
    if 'default_GHG削減量（ton-CO2）_temp' not in ss:
        ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']
    
    ghg_reduction_formula = st.text_area(
        "GHG削減量計算式",
        key='default_GHG削減量（ton-CO2）_temp',
        on_change= store_content,
        args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
    )
    ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
            st.success('GHG削減量計算式の<>はきちんと閉じられています')
        else:
            st.error('GHG削減量計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if '\n' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **コスト削減額計算式**
    default_cost_formula = f"コスト削減額<円/年>=(-1)×{neworold_scope_equipment}{{{neworold_fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>÷{neworold_fuel_emission_factor_str}×{neworold_heat_str}×旧{neworold_scope_equipment}効率÷新{equipment}効率×{heat_str}×{fuel_price_str}"
    ss["user_input"].setdefault("コスト削減額計算式", default_cost_formula)

    if 'default_コスト削減額（円/年）_persist' not in ss:
        ss['default_コスト削減額（円/年）_persist'] = default_cost_formula
    if 'default_コスト削減額（円/年）_temp' not in ss:
        ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']

    cost_reduction_formula = st.text_area(
        "コスト削減額計算式",
        key='default_コスト削減額（円/年）_temp',
        on_change=store_content,
        args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
    )
    ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
            st.success('コスト削減額計算式の<>はきちんと閉じられています')
        else:
            st.error('コスト削減額計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if '\n' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **投資額計算式**
    ss["user_input"].setdefault("投資額計算式", "投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値投資額原単位<円/単位>")

    if 'default_投資額（円）_persist' not in ss:
        ss['default_投資額（円）_persist'] = '投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値投資額原単位<円/単位>'
    if 'default_投資額（円）_temp' not in ss:
        ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']

    investment_amount_formula = st.text_area(
        "投資額計算式",
        key='default_投資額（円）_temp',
        on_change=store_content,
        args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
    )
    ss["user_input"]["投資額計算式"] = investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
            st.success('投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if '\n' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **追加投資額計算式**
    ss["user_input"].setdefault("追加投資額計算式", "追加投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値追加投資額原単位<円/単位>")

    if 'default_追加投資額（円）_persist' not in ss:
        ss['default_追加投資額（円）_persist'] = '追加投資額<円>=必要な代表値<単位>×対象設備の中で施策を実施する設備の割合<%>×代表値追加投資額原単位<円/単位>'
    if 'default_追加投資額（円）_temp' not in ss:
        ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

    additional_investment_amount_formula = st.text_area(
        "追加投資額計算式",
        key='default_追加投資額（円）_temp',
        on_change=store_content,
        args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
    )
    ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
            st.success('追加投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('追加投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if '\n' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    st.subheader("取得済みインプット")
    default_input_name = f"{neworold_scope_equipment}{{{neworold_fuel}}}のCO2排出量"
    ss["user_input"].setdefault("取得済みインプットの名前", default_input_name)
    if 'default_acquired_input_1_persist' not in ss:
        ss['default_acquired_input_1_persist'] = default_input_name
    if 'default_acquired_input_1_temp' not in ss:
        ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']

    acquired_input_1_name = st.text_input(
        "インプットの名前",
        key='default_acquired_input_1_temp',
        on_change=store_content,
        args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
    )
    ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

    ss["user_input"].setdefault("取得済みインプットの数字", 200.0)
    if 'default_acquired_input_1_value_persist' not in ss:
        ss['default_acquired_input_1_value_persist'] = 200.0
    if 'default_acquired_input_1_value_temp' not in ss:
        ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']
    
    acquired_input_1_value = st.number_input(
        "数字",
        min_value=0.0,
        step=1.0,
        key='default_acquired_input_1_value_temp',
        on_change=store_content,
        args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
    )
    ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

    ss["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
    if 'default_acquired_input_1_unit_persist' not in ss:
        ss['default_acquired_input_1_unit_persist'] = 't-CO2'
    if 'default_acquired_input_1_unit_temp' not in ss:
        ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']
    
    acquired_input_1_unit = st.text_input(
        "単位",
        key='default_acquired_input_1_unit_temp',
        on_change=store_content,
        args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
    )
    ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

    # **追加インプット 6個**
    for i in range(6):
        st.subheader(f"追加インプット {i+1}")

        name_key = f"追加インプット{i+1}の名前"
        num_key = f"追加インプット{i+1}の数字"
        unit_key = f"追加インプット{i+1}の単位"

        if f'default_additional_input_{i+1}_persist' not in ss:
            ss[f'default_additional_input_{i+1}_persist'] = '対象設備の中で施策を実施する設備の割合' if i == 0 else '必要な代表値' if i == 1 else ''
        if f'default_additional_input_{i+1}_temp' not in ss:
            ss[f'default_additional_input_{i+1}_temp'] = ss[f'default_additional_input_{i+1}_persist']

        if f'default_additional_input_{i+1}_value_persist' not in ss:
            ss[f'default_additional_input_{i+1}_value_persist'] = 50.0 if i == 0 else 0.0
        if f'default_additional_input_{i+1}_value_temp' not in ss:
            ss[f'default_additional_input_{i+1}_value_temp'] = ss[f'default_additional_input_{i+1}_value_persist']

        if f'default_additional_input_{i+1}_unit_persist' not in ss:
            ss[f'default_additional_input_{i+1}_unit_persist'] = '%' if i == 0 else '単位' if i == 1 else ''
        if f'default_additional_input_{i+1}_unit_temp' not in ss:
            ss[f'default_additional_input_{i+1}_unit_temp'] = ss[f'default_additional_input_{i+1}_unit_persist']
        
        key_name_temp = f'default_additional_input_{i+1}_temp'
        key_name_persist = f'default_additional_input_{i+1}_persist'
        key_value_temp = f'default_additional_input_{i+1}_value_temp'
        key_value_persist = f'default_additional_input_{i+1}_value_persist'
        key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
        key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

        # 入力フォーム
        additional_input_name = st.text_input(
            name_key,
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][name_key] = additional_input_name

        additional_input_val = st.number_input(
            num_key,
            min_value=0.0,
            step=1.0,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][num_key] = additional_input_val

        additional_input_unit = st.text_input(
            unit_key,
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][unit_key] = additional_input_unit
    
    # 燃料取得
    fuel = ss["user_input"].get("燃料", "")
    
    # **事前定義された値**
    if fuel == '電力':
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数' 
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = 0.000434
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = 't-CO2/kWh'
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = '電気料金'
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = 22.97
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = '円/kWh'
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    else:
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = ''
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = np.nan
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = ''
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = ''
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']
    
    predefined_values = [
        ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
        ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
        ("想定稼働年数", 10, "年", "")
    ]
    for name, value, unit, description in predefined_values:
        st.subheader(f"規定値: {name}")
        
        name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
        value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

        # セッションステートにデフォルト値をセット
        ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
        ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
        ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
        ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

        if name == '電気の排出係数':
            key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
            key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
            key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
            key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
            key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
            key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
        elif name == '電気料金':
            key_name_temp = 'default_individual_value(electric_bill)_temp'
            key_name_persist = 'default_individual_value(electric_bill)_persist'
            key_value_temp = 'default_individual_value(electric_bill)_value_temp'
            key_value_persist = 'default_individual_value(electric_bill)_value_persist'
            key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
            key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
        elif name == "想定稼働年数":
            key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
            key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
            key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
            key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
            key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
            key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
            key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
            key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'
        
        # ユーザー入力欄
        ind_val_name = st.text_input(
            f"規定値({name})の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値({name})の名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値({name})の数字",
            min_value=0.0,
            step=float(0.000001 if name == "電気の排出係数" else 0.01),
            format="%.6f" if name == "電気の排出係数" else "%.2f",
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値({name})の数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値({name})の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値({name})の単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値({name})の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値({name})の説明"] = ind_val_description
    
    # **追加の規定値 13個**
    for i in range(13):
        st.subheader(f"規定値 {i+1}")

        fuel = ss["user_input"].get("燃料", "")
        equipment = ss["user_input"].get("設備", "")
        neworold_scope_fuel = ss["user_input"].get("neworold_scope_燃料", "")
        neworold_scope_equipment = ss["user_input"].get("neworold_scope_設備", "")
        value_format = "%.2f"

        if i == 1:
            name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
            value_format = "%.6f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 2:
            name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 3:
            name, unit = "代表値投資額原単位", "円/単位"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 4:
            name, unit = "代表値追加投資額原単位", "円/単位"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 5:
            # `fuel_heat` から燃料の熱量を取得
            name, value, unit, description = fuel_heat.get(fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 6:
            name, unit = f"旧{equipment}効率", "%"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        elif i == 7:
            name, unit = f"新{neworold_scope_equipment}効率", "%"
            value = 0.0
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = ''
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 8:
            name, value, unit, description = emission_factors.get(neworold_scope_fuel, ("", None, "", ""))
            value_format = "%.6f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 9:
            name, value, unit, description = fuel_prices.get(neworold_scope_fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        elif i == 10:
            name, value, unit, description = fuel_heat.get(neworold_scope_fuel, ("", None, "", ""))
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']

        else:
            name, value, unit, description = "", None, "", ""
            value_format = "%.2f"
            if f'default_individual_value_{i+1}_persist' not in ss:
                ss[f'default_individual_value_{i+1}_persist'] = name
            if f'default_individual_value_{i+1}_temp' not in ss:
                ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
            if f'default_individual_value_{i+1}_value_persist' not in ss:
                ss[f'default_individual_value_{i+1}_value_persist'] = value
            if f'default_individual_value_{i+1}_value_temp' not in ss:
                ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
            if f'default_individual_value_{i+1}_unit_persist' not in ss:
                ss[f'default_individual_value_{i+1}_unit_persist'] = unit
            if f'default_individual_value_{i+1}_unit_temp' not in ss:
                ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
            if f'default_individual_value_{i+1}_description_persist' not in ss:
                ss[f'default_individual_value_{i+1}_description_persist'] = description
            if f'default_individual_value_{i+1}_description_temp' not in ss:
                ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
    
        value = 0.0 if value is None else float(value)
        
        ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"規定値{i+1}_説明", description)

        key_name_temp = f'default_individual_value_{i+1}_temp'
        key_name_persist = f'default_individual_value_{i+1}_persist'
        key_value_temp = f'default_individual_value_{i+1}_value_temp'
        key_value_persist = f'default_individual_value_{i+1}_value_persist'
        key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
        key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
        key_description_temp = f'default_individual_value_{i+1}_description_temp'
        key_description_persist = f'default_individual_value_{i+1}_description_persist'
        
        ind_val_name = st.text_input(
            f"規定値 {i+1} の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値{i+1}_名前"] = ind_val_name

        # key = f"規定値{i+1}_数字"
        # # セッションステートの値を取得し、型をチェック
        # current_value = st.session_state["user_input"].get(key, 0.0)
        # # 値が `None` なら 0.0 を設定
        # if current_value is None:
        #     current_value = 0.0
        # # 文字列の場合は float に変換（空文字 `""` の場合は 0.0 にする）
        # elif isinstance(current_value, str):
        #     try:
        #         current_value = float(current_value) if current_value.strip() else 0.0
        #     except ValueError:
        #         current_value = 0.0  # 数値に変換できなければ 0.0 にする
        
        # セッションステートの値を取得し、型をチェック
        current_value = ss[key_value_temp]
        # 値が `None` なら 0.0 を設定
        if current_value is None:
            current_value = 0.0
        # 文字列の場合は float に変換（空文字 `""` の場合は 0.0 にする）
        elif isinstance(current_value, str):
            try:
                current_value = float(current_value) if current_value.strip() else 0.0
            except ValueError:
                current_value = 0.0  # 数値に変換できなければ 0.0 にする
        
        # Streamlit の number_input に渡す
        ind_val_val = st.number_input(
            f"規定値{i+1}_数字",
            min_value=0.0,
            step=1.0 if value_format == "%.2f" else 0.000001,
            format=value_format,  # 小数点以下6桁を強制適用
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値{i+1}_数字"] = ind_val_val

        ss["user_input"][f"規定値{i+1}_単位"] = st.text_input(
            f"規定値 {i+1} の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値{i+1}_単位"] = ind_val_unit

        ind_val_description = st.text_area(
            f"規定値 {i+1} の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値{i+1}_説明"] = ind_val_description

    # **推測値テンプレートの選択**
    if 'default_prediction_template_persist' not in ss:
        ss['default_prediction_template_persist'] = None
    if 'default_prediction_template_temp' not in ss:
        ss['default_prediction_template_temp'] = ss['default_prediction_template_persist']

    prediction_template = st.selectbox(
        "推測値のテンプレはどれを使用しますか？", 
        ["1(容量推測)", "2(台数推測)", "3(自由入力)"],
        key='default_prediction_template_temp',
        on_change=store_content,
        args=('default_prediction_template_persist', 'default_prediction_template_temp')
    )

    ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
    ss["user_input"]["推測値のテンプレ"] = prediction_template

    col1, col2 = st.columns(2)
    with col1:
        if st.button("入力を確定", key="submit"):
            prediction_template = ss["user_input"].get("推測値のテンプレ", "")
            ss["previous_page"] = ss["page"]
            if prediction_template.startswith("1"):
                next_page("page3A")
            elif prediction_template.startswith("2"):
                next_page("page3B")
            else:
                next_page("page3C")
    with col2:
        if st.button("エラーチェック", key="check"):
            # チェックする計算式の辞書
            target_formula_dict = {
                "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                "投資額計算式": ss["user_input"]["投資額計算式"],
                "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
            }
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")
    
    if st.button("戻る"):
        next_page("page1")


elif ss["page"] == "page2E":
    if ss['selected_option_persist'] == '使用しない':
        st.title("自由入力式入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")
    
        # 燃料ごとの排出係数データ
        emission_factors = {
            "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
            "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
            "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
            "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
            "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        }
    
        # 燃料ごとの価格データ
        fuel_prices = {
            "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
            "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
            "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
            "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
            "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
            "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
            "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
            "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
            "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
            "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
            "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
        }
    
        fuel_heat = {
        "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
        "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
        }
    
        # **GHG削減量計算式**
        ss["user_input"].setdefault("GHG削減量計算式", "")

        if 'default_GHG削減量（ton-CO2）_persist' not in ss:
            ss['default_GHG削減量（ton-CO2）_persist'] = ''
        if 'default_GHG削減量（ton-CO2）_temp' not in ss:
            ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']

        ghg_reduction_formula = st.text_area(
            "GHG削減量計算式",
            key='default_GHG削減量（ton-CO2）_temp',
            on_change= store_content,
            args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
        )
        ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
                st.success('GHG削減量計算式の<>はきちんと閉じられています')
            else:
                st.error('GHG削減量計算式の<>がきちんと閉じられていません')
        
        # 改行が含まれていないかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if '\n' in ss["user_input"]["GHG削減量計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **コスト削減額計算式**
        fuel = ss["user_input"].get("燃料", "")
        if fuel == "電力":
            emission_factor_str = "電気の排出係数<t-CO2/kWh>"
            fuel_price_str = "電気料金<円/kWh>"
        elif fuel == "都市ガス":
            emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
            fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        else:
            emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
            price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
            emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
            fuel_price_str = f"{price_name}<{price_unit}>"

        ss["user_input"].setdefault("コスト削減額計算式", "")

        if 'default_コスト削減額（円/年）_persist' not in ss:
            ss['default_コスト削減額（円/年）_persist'] = ''
        if 'default_コスト削減額（円/年）_temp' not in ss:
            ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']

        cost_reduction_formula = st.text_area(
            "コスト削減額計算式",
            key='default_コスト削減額（円/年）_temp',
            on_change=store_content,
            args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
        )
        ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
                st.success('コスト削減額計算式の<>はきちんと閉じられています')
            else:
                st.error('コスト削減額計算式の<>がきちんと閉じられていません')
        
        # 改行が含まれていないかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if '\n' in ss["user_input"]["コスト削減額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **投資額計算式**
        ss["user_input"].setdefault("投資額計算式", "")

        if 'default_投資額（円）_persist' not in ss:
            ss['default_投資額（円）_persist'] = ''
        if 'default_投資額（円）_temp' not in ss:
            ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']

        investment_amount_formula = st.text_area(
            "投資額計算式",
            key='default_投資額（円）_temp',
            on_change=store_content,
            args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
        )
        ss["user_input"]["投資額計算式"] = investment_amount_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
                st.success('投資額計算式の<>はきちんと閉じられています')
            else:
                st.error('投資額計算式の<>がきちんと閉じられていません')
        # 改行が含まれていないかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if '\n' in ss["user_input"]["投資額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **追加投資額計算式**
        ss["user_input"].setdefault("追加投資額計算式", "")

        if 'default_追加投資額（円）_persist' not in ss:
            ss['default_追加投資額（円）_persist'] = ''
        if 'default_追加投資額（円）_temp' not in ss:
            ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

        additional_investment_amount_formula = st.text_area(
            "追加投資額計算式",
            key='default_追加投資額（円）_temp',
            on_change=store_content,
            args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
        )
        ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
                st.success('追加投資額計算式の<>はきちんと閉じられています')
            else:
                st.error('追加投資額計算式の<>がきちんと閉じられていません')
        # 改行が含まれていないかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if '\n' in ss["user_input"]["追加投資額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
                st.error('計算式中にスペースが含まれています')

        st.subheader("取得済みインプット")
        default_input_name = f"{ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        ss["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        if 'default_acquired_input_1_persist' not in ss:
            ss['default_acquired_input_1_persist'] = default_input_name
        if 'default_acquired_input_1_temp' not in ss:
            ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']

        acquired_input_1_name = st.text_input(
            "インプットの名前",
            key='default_acquired_input_1_temp',
            on_change=store_content,
            args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
        )
        ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

        ss["user_input"].setdefault("取得済みインプットの数字", 200.0)
        if 'default_acquired_input_1_value_persist' not in ss:
            ss['default_acquired_input_1_value_persist'] = 200.0
        if 'default_acquired_input_1_value_temp' not in ss:
            ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']

        acquired_input_1_value = st.number_input(
            "数字",
            min_value=0.0,
            step=1.0,
            key='default_acquired_input_1_value_temp',
            on_change=store_content,
            args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
        )
        ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

        ss["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        if 'default_acquired_input_1_unit_persist' not in ss:
            ss['default_acquired_input_1_unit_persist'] = 't-CO2'
        if 'default_acquired_input_1_unit_temp' not in ss:
            ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']
        
        acquired_input_1_unit = st.text_input(
            "単位",
            key='default_acquired_input_1_unit_temp',
            on_change=store_content,
            args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
        )
        ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit
        
        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")

            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            if f'default_additional_input_{i+1}_persist' not in ss:
                ss[f'default_additional_input_{i+1}_persist'] = '対象設備の中で施策を実施する設備の割合' if i == 0 else ''
            if f'default_additional_input_{i+1}_temp' not in ss:
                ss[f'default_additional_input_{i+1}_temp'] = ss[f'default_additional_input_{i+1}_persist']
    
            if f'default_additional_input_{i+1}_value_persist' not in ss:
                ss[f'default_additional_input_{i+1}_value_persist'] = 50.0 if i == 0 else 0.0
            if f'default_additional_input_{i+1}_value_temp' not in ss:
                ss[f'default_additional_input_{i+1}_value_temp'] = ss[f'default_additional_input_{i+1}_value_persist']
    
            if f'default_additional_input_{i+1}_unit_persist' not in ss:
                ss[f'default_additional_input_{i+1}_unit_persist'] = '%' if i == 0 else ''
            if f'default_additional_input_{i+1}_unit_temp' not in ss:
                ss[f'default_additional_input_{i+1}_unit_temp'] = ss[f'default_additional_input_{i+1}_unit_persist']
            
            key_name_temp = f'default_additional_input_{i+1}_temp'
            key_name_persist = f'default_additional_input_{i+1}_persist'
            key_value_temp = f'default_additional_input_{i+1}_value_temp'
            key_value_persist = f'default_additional_input_{i+1}_value_persist'
            key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
            key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

            additional_input_name = st.text_input(
                name_key,
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][name_key] = additional_input_name

            additional_input_val = st.number_input(
                num_key,
                min_value=0.0,
                step=1.0,
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][num_key] = additional_input_val

            additional_input_unit = st.text_input(
                unit_key,
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][unit_key] = additional_input_unit

        # 燃料取得
        fuel = ss["user_input"].get("燃料", "")

        # **事前定義された値**
        if fuel == '電力':
            if 'default_individual_value(electric_emission_factor)_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数' 
            if 'default_individual_value(electric_emission_factor)_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
            if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_value_persist'] = 0.000434
            if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
            if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_unit_persist'] = 't-CO2/kWh'
            if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
            if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_description_persist'] = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
            if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
        
            if 'default_individual_value(electric_bill)_persist' not in ss:
                ss['default_individual_value(electric_bill)_persist'] = '電気料金'
            if 'default_individual_value(electric_bill)_temp' not in ss:
                ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
            if 'default_individual_value(electric_bill)_value_persist' not in ss:
                ss['default_individual_value(electric_bill)_value_persist'] = 22.97
            if 'default_individual_value(electric_bill)_value_temp' not in ss:
                ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
            if 'default_individual_value(electric_bill)_unit_persist' not in ss:
                ss['default_individual_value(electric_bill)_unit_persist'] = '円/kWh'
            if 'default_individual_value(electric_bill)_unit_temp' not in ss:
                ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
            if 'default_individual_value(electric_bill)__description_persist' not in ss:
                ss['default_individual_value(electric_bill)__description_persist'] = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
            if 'default_individual_value(electric_bill)__description_temp' not in ss:
                ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
        
            if 'default_individual_value(estimated_lifetime)_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
            if 'default_individual_value(estimated_lifetime)_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
            if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
            if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
            if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
            if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
            if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
            if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']
    
        else:
            if 'default_individual_value(electric_emission_factor)_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_persist'] = ''
            if 'default_individual_value(electric_emission_factor)_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
            if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan
            if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
            if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_unit_persist'] = ''
            if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
            if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
                ss['default_individual_value(electric_emission_factor)_description_persist'] = ''
            if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
                ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
        
            if 'default_individual_value(electric_bill)_persist' not in ss:
                ss['default_individual_value(electric_bill)_persist'] = ''
            if 'default_individual_value(electric_bill)_temp' not in ss:
                ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
            if 'default_individual_value(electric_bill)_value_persist' not in ss:
                ss['default_individual_value(electric_bill)_value_persist'] = np.nan
            if 'default_individual_value(electric_bill)_value_temp' not in ss:
                ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
            if 'default_individual_value(electric_bill)_unit_persist' not in ss:
                ss['default_individual_value(electric_bill)_unit_persist'] = ''
            if 'default_individual_value(electric_bill)_unit_temp' not in ss:
                ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
            if 'default_individual_value(electric_bill)__description_persist' not in ss:
                ss['default_individual_value(electric_bill)__description_persist'] = ''
            if 'default_individual_value(electric_bill)__description_temp' not in ss:
                ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
        
            if 'default_individual_value(estimated_lifetime)_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
            if 'default_individual_value(estimated_lifetime)_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
            if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
            if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
            if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
            if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
            if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
                ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
            if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
                ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']
        
        predefined_values = [
            ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
            ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
            ("想定稼働年数", 10, "年", "")
        ]

        for name, value, unit, description in predefined_values:
            st.subheader(f"規定値: {name}")
            
            name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
            value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

            # セッションステートにデフォルト値をセット
            ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
            ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            if name == '電気の排出係数':
                key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
                key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
                key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
                key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
                key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
                key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
                key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
                key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
            elif name == '電気料金':
                key_name_temp = 'default_individual_value(electric_bill)_temp'
                key_name_persist = 'default_individual_value(electric_bill)_persist'
                key_value_temp = 'default_individual_value(electric_bill)_value_temp'
                key_value_persist = 'default_individual_value(electric_bill)_value_persist'
                key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
                key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
                key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
                key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
            elif name == "想定稼働年数":
                key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
                key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
                key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
                key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
                key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
                key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
                key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
                key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

            # ユーザー入力欄
            ind_val_name = st.text_input(
                f"規定値({name})の名前", 
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][f"規定値({name})の名前"] = ind_val_name

            ind_val_val = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][f"規定値({name})の数字"] = ind_val_val

            ind_val_unit = st.text_input(
                f"規定値({name})の単位", 
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][f"規定値({name})の単位"] = ind_val_unit

            ind_val_description = st.text_area(
                f"規定値({name})の説明", 
                key=key_description_temp,
                on_change=store_content,
                args=(key_description_persist, key_description_temp)
            )
            ss["user_input"][f"規定値({name})の説明"] = ind_val_description
        
        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")

            fuel = ss["user_input"].get("燃料", "")
            value_format = "%.2f"

            if i == 0:
                name, unit = "省エネ率", "%"
                value = None
                if f'default_individual_value_{i+1}_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_persist'] = name
                if f'default_individual_value_{i+1}_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
                if f'default_individual_value_{i+1}_value_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_value_persist'] = value
                if f'default_individual_value_{i+1}_value_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
                if f'default_individual_value_{i+1}_unit_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_persist'] = unit
                if f'default_individual_value_{i+1}_unit_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
                if f'default_individual_value_{i+1}_description_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_description_persist'] = ''
                if f'default_individual_value_{i+1}_description_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
    
            elif i == 1:
                name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
                value_format = "%.6f"
                if f'default_individual_value_{i+1}_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_persist'] = name
                if f'default_individual_value_{i+1}_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
                if f'default_individual_value_{i+1}_value_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_value_persist'] = value
                if f'default_individual_value_{i+1}_value_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
                if f'default_individual_value_{i+1}_unit_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_persist'] = unit
                if f'default_individual_value_{i+1}_unit_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
                if f'default_individual_value_{i+1}_description_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_description_persist'] = description
                if f'default_individual_value_{i+1}_description_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
    
            elif i == 2:
                name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
                value_format = "%.2f"
                if f'default_individual_value_{i+1}_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_persist'] = name
                if f'default_individual_value_{i+1}_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
                if f'default_individual_value_{i+1}_value_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_value_persist'] = value
                if f'default_individual_value_{i+1}_value_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
                if f'default_individual_value_{i+1}_unit_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_persist'] = unit
                if f'default_individual_value_{i+1}_unit_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
                if f'default_individual_value_{i+1}_description_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_description_persist'] = description
                if f'default_individual_value_{i+1}_description_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
            
            else:
                name, value, unit, description = "", None, "", ""
                value_format = "%.2f"
                if f'default_individual_value_{i+1}_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_persist'] = name
                if f'default_individual_value_{i+1}_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
                if f'default_individual_value_{i+1}_value_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_value_persist'] = value
                if f'default_individual_value_{i+1}_value_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
                if f'default_individual_value_{i+1}_unit_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_persist'] = unit
                if f'default_individual_value_{i+1}_unit_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
                if f'default_individual_value_{i+1}_description_persist' not in ss:
                    ss[f'default_individual_value_{i+1}_description_persist'] = ''
                if f'default_individual_value_{i+1}_description_temp' not in ss:
                    ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
            value = 0.0 if value is None else float(value)
            
            ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
            ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
            ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            ss["user_input"].setdefault(f"規定値{i+1}_説明", description)

            key_name_temp = f'default_individual_value_{i+1}_temp'
            key_name_persist = f'default_individual_value_{i+1}_persist'
            key_value_temp = f'default_individual_value_{i+1}_value_temp'
            key_value_persist = f'default_individual_value_{i+1}_value_persist'
            key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
            key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
            key_description_temp = f'default_individual_value_{i+1}_description_temp'
            key_description_persist = f'default_individual_value_{i+1}_description_persist'
            
            ind_val_name = st.text_input(
                f"規定値 {i+1} の名前", 
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][f"規定値{i+1}_名前"] = ind_val_name

            ind_val_val = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][f"規定値{i+1}_数字"] = ind_val_val

            ind_val_unit = st.text_input(
                f"規定値 {i+1} の単位", 
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][f"規定値{i+1}_単位"] = ind_val_unit

            ind_val_description = st.text_area(
                f"規定値 {i+1} の説明", 
                key=key_description_temp,
                on_change=store_content,
                args=(key_description_persist, key_description_temp)
            )
            ss["user_input"][f"規定値{i+1}_説明"] = ind_val_description

        # **推測値テンプレートの選択**
        if 'default_prediction_template_persist' not in ss:
            ss['default_prediction_template_persist'] = None
        if 'default_prediction_template_temp' not in ss:
            ss['default_prediction_template_temp'] = ss['default_prediction_template_persist']

        prediction_template = st.selectbox(
            "推測値のテンプレはどれを使用しますか？", 
            ["1(容量推測)", "2(台数推測)", "3(自由入力)"],
            key='default_prediction_template_temp',
            on_change=store_content,
            args=('default_prediction_template_persist', 'default_prediction_template_temp')
        )

        ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
        ss["user_input"]["推測値のテンプレ"] = prediction_template

        col1, col2 = st.columns(2)
        with col1:
            if st.button("入力を確定", key="submit"):
                prediction_template = ss["user_input"].get("推測値のテンプレ", "")
                ss["previous_page"] = ss["page"]
                if prediction_template.startswith("1"):
                    next_page("page3A")
                elif prediction_template.startswith("2"):
                    next_page("page3B")
                else:
                    next_page("page3C")
        with col2:
            if st.button("エラーチェック", key="check"):
                # チェックする計算式の辞書
                target_formula_dict = {
                    "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                    "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                    "投資額計算式": ss["user_input"]["投資額計算式"],
                    "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
                }
                # チェックする因数
                target_factors = [
                    ss["user_input"]["取得済みインプットの名前"],
                    ss["user_input"]["追加インプット1の名前"],
                    ss["user_input"]["追加インプット2の名前"],
                    ss["user_input"]["追加インプット3の名前"],
                    ss["user_input"]["追加インプット4の名前"],
                    ss["user_input"]["規定値(電気の排出係数)の名前"],
                    ss["user_input"]["規定値(電気料金)の名前"],
                    ss["user_input"]["規定値(想定稼働年数)の名前"],
                    ss["user_input"]["規定値1_名前"],
                    ss["user_input"]["規定値2_名前"],
                    ss["user_input"]["規定値3_名前"],
                    ss["user_input"]["規定値4_名前"],
                    ss["user_input"]["規定値5_名前"],
                    ss["user_input"]["規定値6_名前"],
                    ss["user_input"]["規定値7_名前"],
                    ss["user_input"]["規定値8_名前"],
                    ss["user_input"]["規定値9_名前"],
                    ss["user_input"]["規定値10_名前"],
                    ss["user_input"]["規定値11_名前"],
                    ss["user_input"]["規定値12_名前"],
                    ss["user_input"]["規定値13_名前"]
                ]
                for formula_name, formula in target_formula_dict.items():
                    parsed_list = split_formula(formula)
                    # 存在しなかった要素を保持するためのリスト
                    not_found_items = []
                    # リスト内の要素を1つずつ確認
                    for item in parsed_list:
                        found_in_any = False
                        # target_factorsに含まれる各因数についてチェック
                        for factor in target_factors:
                            if item == factor:
                                found_in_any = True
                                break
                        if not found_in_any:
                            not_found_items.append(item)
                    if not_found_items:
                        st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                        for i in not_found_items:
                            st.markdown(f"- {i}")
                    else:
                        st.success(f"✅ {formula_name}の因数に問題はありません")
        
        if st.button("戻る"):
            next_page("page1")

    elif ss['selected_option_persist'] == 'csvファイルを読み込む':
        filtered_df = df[df['施策ユニークNo'] == ss['strategy_number_persist']]
        st.write(f'「{filtered_df['施策名'].iloc[0]}」をテンプレートとして使用しています')

        if 'default_GHG削減量（ton-CO2）_persist' not in ss:
            raw_content = filtered_df['GHG削減量（ton-CO2）'].iloc[0]
            ss['default_GHG削減量（ton-CO2）_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_GHG削減量（ton-CO2）_temp' not in ss:
            ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']

        # if 'default_GHG削減量（ton-CO2）（CO2フリー計算用）_persist' not in ss:
        #     raw_content = filtered_df['GHG削減量（ton-CO2）（CO2フリー計算用）'].iloc[0]
        #     ss['default_GHG削減量（ton-CO2）（CO2フリー計算用）_persist'] = '' if pd.isna(raw_content) else raw_content
        # if 'default_GHG削減量（ton-CO2）（CO2フリー計算用）_temp' not in ss:
        #     ss['default_GHG削減量（ton-CO2）（CO2フリー計算用）_temp'] = ss['default_GHG削減量（ton-CO2）（CO2フリー計算用）_persist']

        if 'default_コスト削減額（円/年）_persist' not in ss:
            raw_content = filtered_df['コスト削減額（円/年）'].iloc[0]
            ss['default_コスト削減額（円/年）_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_コスト削減額（円/年）_temp' not in ss:
            ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']

        # if 'default_コスト削減額（円/年）（CO2フリー計算用)_persist' not in ss:
        #     raw_content = filtered_df['コスト削減額（円/年）（CO2フリー計算用）'].iloc[0]
        #     ss['default_コスト削減額（円/年）（CO2フリー計算用)_persist'] = '' if pd.isna(raw_content) else raw_content
        # if 'default_コスト削減額（円/年）（CO2フリー計算用)_temp' not in ss:
        #     ss['default_コスト削減額（円/年）（CO2フリー計算用)_temp'] = ss['default_コスト削減額（円/年）（CO2フリー計算用)_persist']

        if 'default_投資額（円）_persist' not in ss:
            raw_content = filtered_df['投資額（円）'].iloc[0]
            ss['default_投資額（円）_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_投資額（円）_temp' not in ss:
            ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']

        if 'default_追加投資額（円）_persist' not in ss:
            raw_content = filtered_df['追加投資額（円）'].iloc[0]
            ss['default_追加投資額（円）_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_追加投資額（円）_temp' not in ss:
            ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

        if 'default_acquired_input_1_persist' not in ss:
            raw_content = filtered_df['acquired_input_1'].iloc[0]
            ss['default_acquired_input_1_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_acquired_input_1_temp' not in ss:
            ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']
        pos = filtered_df.columns.get_loc('acquired_input_1')
        val = filtered_df.iloc[0, pos+1]
        if 'default_acquired_input_1_value_persist' not in ss:
            ss['default_acquired_input_1_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_acquired_input_1_value_temp' not in ss:
            ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']
        if 'default_acquired_input_1_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_acquired_input_1_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_acquired_input_1_unit_temp' not in ss:
            ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']

        if 'default_additional_input_1_persist' not in ss:
            raw_content = filtered_df['additional_input_1'].iloc[0]
            ss['default_additional_input_1_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_1_temp' not in ss:
            ss['default_additional_input_1_temp'] = ss['default_additional_input_1_persist']
        pos = filtered_df.columns.get_loc('additional_input_1')
        val = filtered_df.iloc[0, pos+1]
        if 'default_additional_input_1_value_persist' not in ss:
            ss['default_additional_input_1_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_additional_input_1_value_temp' not in ss:
            ss['default_additional_input_1_value_temp'] = ss['default_additional_input_1_value_persist']
        if 'default_additional_input_1_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_additional_input_1_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_1_unit_temp' not in ss:
            ss['default_additional_input_1_unit_temp'] = ss['default_additional_input_1_unit_persist']

        if 'default_additional_input_2_persist' not in ss:
            raw_content = filtered_df['additional_input_2'].iloc[0]
            ss['default_additional_input_2_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_2_temp' not in ss:
            ss['default_additional_input_2_temp'] = ss['default_additional_input_2_persist']
        pos = filtered_df.columns.get_loc('additional_input_2')
        val = filtered_df.iloc[0, pos+1]
        if 'default_additional_input_2_value_persist' not in ss:
            ss['default_additional_input_2_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_additional_input_2_value_temp' not in ss:
            ss['default_additional_input_2_value_temp'] = ss['default_additional_input_2_value_persist']
        if 'default_additional_input_2_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_additional_input_2_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_2_unit_temp' not in ss:
            ss['default_additional_input_2_unit_temp'] = ss['default_additional_input_2_unit_persist']

        if 'default_additional_input_3_persist' not in ss:
            raw_content = filtered_df['additional_input_3'].iloc[0]
            ss['default_additional_input_3_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_3_temp' not in ss:
            ss['default_additional_input_3_temp'] = ss['default_additional_input_3_persist']
        pos = filtered_df.columns.get_loc('additional_input_3')
        val = filtered_df.iloc[0, pos+1]
        if 'default_additional_input_3_value_persist' not in ss:
            ss['default_additional_input_3_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_additional_input_3_value_temp' not in ss:
            ss['default_additional_input_3_value_temp'] = ss['default_additional_input_3_value_persist']
        if 'default_additional_input_3_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_additional_input_3_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_3_unit_temp' not in ss:
            ss['default_additional_input_3_unit_temp'] = ss['default_additional_input_3_unit_persist']

        if 'default_additional_input_4_persist' not in ss:
            raw_content = filtered_df['additional_input_4'].iloc[0]
            ss['default_additional_input_4_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_4_temp' not in ss:
            ss['default_additional_input_4_temp'] = ss['default_additional_input_4_persist']
        pos = filtered_df.columns.get_loc('additional_input_4')
        val = filtered_df.iloc[0, pos+1]
        if 'default_additional_input_4_value_persist' not in ss:
            ss['default_additional_input_4_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_additional_input_4_value_temp' not in ss:
            ss['default_additional_input_4_value_temp'] = ss['default_additional_input_4_value_persist']
        if 'default_additional_input_4_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_additional_input_4_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_additional_input_4_unit_temp' not in ss:
            ss['default_additional_input_4_unit_temp'] = ss['default_additional_input_4_unit_persist']

        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            raw_content = filtered_df['individual_value(electric_emission_factor)'].iloc[0]
            ss['default_individual_value(electric_emission_factor)_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        pos = filtered_df.columns.get_loc('individual_value(electric_emission_factor)')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            raw_content = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
            ss['default_individual_value(electric_emission_factor)_description_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']

        if 'default_individual_value(electric_bill)_persist' not in ss:
            raw_content = filtered_df['individual_value(electric_bill)'].iloc[0]
            ss['default_individual_value(electric_bill)_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        pos = filtered_df.columns.get_loc('individual_value(electric_bill)')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value(electric_bill)_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            raw_content = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
            ss['default_individual_value(electric_bill)__description_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']

        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            raw_content = filtered_df['individual_value(estimated_lifetime)'].iloc[0]
            ss['default_individual_value(estimated_lifetime)_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        pos = filtered_df.columns.get_loc('individual_value(estimated_lifetime)')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

        if 'default_individual_value_1_persist' not in ss:
            raw_content = filtered_df['individual_value_1'].iloc[0]
            ss['default_individual_value_1_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_1_temp' not in ss:
            ss['default_individual_value_1_temp'] = ss['default_individual_value_1_persist']
        pos = filtered_df.columns.get_loc('individual_value_1')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_1_value_persist' not in ss:
            ss['default_individual_value_1_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_1_value_temp' not in ss:
            ss['default_individual_value_1_value_temp'] = ss['default_individual_value_1_value_persist']
        if 'default_individual_value_1_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_1_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_1_unit_temp' not in ss:
            ss['default_individual_value_1_unit_temp'] = ss['default_individual_value_1_unit_persist']
        if 'default_individual_value_1_description_persist' not in ss:
            ss['default_individual_value_1_description_persist'] = ''
        if 'default_individual_value_1_description_temp' not in ss:
            ss['default_individual_value_1_descriptiont_temp'] = ss['default_individual_value_1_description_persist']

        if 'default_individual_value_2_persist' not in ss:
            raw_content = filtered_df['individual_value_2'].iloc[0]
            ss['default_individual_value_2_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_2_temp' not in ss:
            ss['default_individual_value_2_temp'] = ss['default_individual_value_2_persist']
        pos = filtered_df.columns.get_loc('individual_value_2')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_2_value_persist' not in ss:
            ss['default_individual_value_2_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_2_value_temp' not in ss:
            ss['default_individual_value_2_value_temp'] = ss['default_individual_value_2_value_persist']
        if 'default_individual_value_2_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_2_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_2_unit_temp' not in ss:
            ss['default_individual_value_2_unit_temp'] = ss['default_individual_value_2_unit_persist']
        if 'default_individual_value_2_description_persist' not in ss:
            ss['default_individual_value_2_description_persist'] = ''
        if 'default_individual_value_2_description_temp' not in ss:
            ss['default_individual_value_2_descriptiont_temp'] = ss['default_individual_value_2_description_persist']

        if 'default_individual_value_3_persist' not in ss:
            raw_content = filtered_df['individual_value_3'].iloc[0]
            ss['default_individual_value_3_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_3_temp' not in ss:
            ss['default_individual_value_3_temp'] = ss['default_individual_value_3_persist']
        pos = filtered_df.columns.get_loc('individual_value_3')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_3_value_persist' not in ss:
            ss['default_individual_value_3_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_3_value_temp' not in ss:
            ss['default_individual_value_3_value_temp'] = ss['default_individual_value_3_value_persist']
        if 'default_individual_value_3_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_3_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_3_unit_temp' not in ss:
            ss['default_individual_value_3_unit_temp'] = ss['default_individual_value_3_unit_persist']
        if 'default_individual_value_3_description_persist' not in ss:
            ss['default_individual_value_3_description_persist'] = ''
        if 'default_individual_value_3_description_temp' not in ss:
            ss['default_individual_value_3_descriptiont_temp'] = ss['default_individual_value_3_description_persist']

        if 'default_individual_value_4_persist' not in ss:
            raw_content = filtered_df['individual_value_4'].iloc[0]
            ss['default_individual_value_4_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_4_temp' not in ss:
            ss['default_individual_value_4_temp'] = ss['default_individual_value_4_persist']
        pos = filtered_df.columns.get_loc('individual_value_4')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_4_value_persist' not in ss:
            ss['default_individual_value_4_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_4_value_temp' not in ss:
            ss['default_individual_value_4_value_temp'] = ss['default_individual_value_4_value_persist']
        if 'default_individual_value_4_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_4_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_4_unit_temp' not in ss:
            ss['default_individual_value_4_unit_temp'] = ss['default_individual_value_4_unit_persist']
        if 'default_individual_value_4_description_persist' not in ss:
            ss['default_individual_value_4_description_persist'] = ''
        if 'default_individual_value_4_description_temp' not in ss:
            ss['default_individual_value_4_descriptiont_temp'] = ss['default_individual_value_4_description_persist']

        if 'default_individual_value_5_persist' not in ss:
            raw_content = filtered_df['individual_value_5'].iloc[0]
            ss['default_individual_value_5_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_5_temp' not in ss:
            ss['default_individual_value_5_temp'] = ss['default_individual_value_5_persist']
        pos = filtered_df.columns.get_loc('individual_value_5')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_5_value_persist' not in ss:
            ss['default_individual_value_5_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_5_value_temp' not in ss:
            ss['default_individual_value_5_value_temp'] = ss['default_individual_value_5_value_persist']
        if 'default_individual_value_5_unit_persist' not in ss:
            raw_content =  filtered_df.iloc[0, pos+2]
            ss['default_individual_value_5_unit_persist'] =  '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_5_unit_temp' not in ss:
            ss['default_individual_value_5_unit_temp'] = ss['default_individual_value_5_unit_persist']
        if 'default_individual_value_5_description_persist' not in ss:
            ss['default_individual_value_5_description_persist'] = ''
        if 'default_individual_value_5_description_temp' not in ss:
            ss['default_individual_value_5_descriptiont_temp'] = ss['default_individual_value_5_description_persist']

        if 'default_individual_value_6_persist' not in ss:
            raw_content = filtered_df['individual_value_6'].iloc[0]
            ss['default_individual_value_6_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_6_temp' not in ss:
            ss['default_individual_value_6_temp'] = ss['default_individual_value_6_persist']
        pos = filtered_df.columns.get_loc('individual_value_6')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_6_value_persist' not in ss:
            ss['default_individual_value_6_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_6_value_temp' not in ss:
            ss['default_individual_value_6_value_temp'] = ss['default_individual_value_6_value_persist']
        if 'default_individual_value_6_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_6_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_6_unit_temp' not in ss:
            ss['default_individual_value_6_unit_temp'] = ss['default_individual_value_6_unit_persist']
        if 'default_individual_value_6_description_persist' not in ss:
            ss['default_individual_value_6_description_persist'] = ''
        if 'default_individual_value_6_description_temp' not in ss:
            ss['default_individual_value_6_descriptiont_temp'] = ss['default_individual_value_6_description_persist']

        if 'default_individual_value_7_persist' not in ss:
            raw_content = filtered_df['individual_value_7'].iloc[0]
            ss['default_individual_value_7_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_7_temp' not in ss:
            ss['default_individual_value_7_temp'] = ss['default_individual_value_7_persist']
        pos = filtered_df.columns.get_loc('individual_value_7')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_7_value_persist' not in ss:
            ss['default_individual_value_7_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_7_value_temp' not in ss:
            ss['default_individual_value_7_value_temp'] = ss['default_individual_value_7_value_persist']
        if 'default_individual_value_7_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_7_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_7_unit_temp' not in ss:
            ss['default_individual_value_7_unit_temp'] = ss['default_individual_value_7_unit_persist']
        if 'default_individual_value_7_description_persist' not in ss:
            ss['default_individual_value_7_description_persist'] = ''
        if 'default_individual_value_7_description_temp' not in ss:
            ss['default_individual_value_7_descriptiont_temp'] = ss['default_individual_value_7_description_persist']

        if 'default_individual_value_8_persist' not in ss:
            raw_content = filtered_df['individual_value_8'].iloc[0]
            ss['default_individual_value_8_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_8_temp' not in ss:
            ss['default_individual_value_8_temp'] = ss['default_individual_value_8_persist']
        pos = filtered_df.columns.get_loc('individual_value_8')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_8_value_persist' not in ss:
            ss['default_individual_value_8_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_8_value_temp' not in ss:
            ss['default_individual_value_8_value_temp'] = ss['default_individual_value_8_value_persist']
        if 'default_individual_value_8_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_8_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_8_unit_temp' not in ss:
            ss['default_individual_value_8_unit_temp'] = ss['default_individual_value_8_unit_persist']
        if 'default_individual_value_8_description_persist' not in ss:
            ss['default_individual_value_8_description_persist'] = ''
        if 'default_individual_value_8_description_temp' not in ss:
            ss['default_individual_value_8_descriptiont_temp'] = ss['default_individual_value_8_description_persist']

        if 'default_individual_value_9_persist' not in ss:
            raw_content = filtered_df['individual_value_9'].iloc[0]
            ss['default_individual_value_9_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_9_temp' not in ss:
            ss['default_individual_value_9_temp'] = ss['default_individual_value_9_persist']
        pos = filtered_df.columns.get_loc('individual_value_9')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_9_value_persist' not in ss:
            ss['default_individual_value_9_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_9_value_temp' not in ss:
            ss['default_individual_value_9_value_temp'] = ss['default_individual_value_9_value_persist']
        if 'default_individual_value_9_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_9_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_9_unit_temp' not in ss:
            ss['default_individual_value_9_unit_temp'] = ss['default_individual_value_9_unit_persist']
        if 'default_individual_value_9_description_persist' not in ss:
            ss['default_individual_value_9_description_persist'] = ''
        if 'default_individual_value_9_description_temp' not in ss:
            ss['default_individual_value_9_descriptiont_temp'] = ss['default_individual_value_9_description_persist']

        if 'default_individual_value_10_persist' not in ss:
            raw_content = filtered_df['individual_value_10'].iloc[0]
            ss['default_individual_value_10_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_10_temp' not in ss:
            ss['default_individual_value_10_temp'] = ss['default_individual_value_10_persist']
        pos = filtered_df.columns.get_loc('individual_value_10')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_10_value_persist' not in ss:
            ss['default_individual_value_10_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_10_value_temp' not in ss:
            ss['default_individual_value_10_value_temp'] = ss['default_individual_value_10_value_persist']
        if 'default_individual_value_10_unit_persist' not in ss: 
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_10_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_10_unit_temp' not in ss: 
            ss['default_individual_value_10_unit_temp'] = ss['default_individual_value_10_unit_persist']
        if 'default_individual_value_10_description_persist' not in ss:
            ss['default_individual_value_10_description_persist'] = ''
        if 'default_individual_value_10_description_temp' not in ss:
            ss['default_individual_value_10_descriptiont_temp'] = ss['default_individual_value_10_description_persist']

        if 'default_individual_value_11_persist' not in ss:
            raw_content = filtered_df['individual_value_11'].iloc[0]
            ss['default_individual_value_11_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_11_temp' not in ss:
            ss['default_individual_value_11_temp'] = ss['default_individual_value_11_persist']
        pos = filtered_df.columns.get_loc('individual_value_11')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_11_value_persist' not in ss:
            ss['default_individual_value_11_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_11_value_temp' not in ss:
            ss['default_individual_value_11_value_temp'] = ss['default_individual_value_11_value_persist']
        if 'default_individual_value_11_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_11_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_11_unit_temp' not in ss:
            ss['default_individual_value_11_unit_temp'] = ss['default_individual_value_11_unit_persist']
        if 'default_individual_value_11_description_persist' not in ss:
            ss['default_individual_value_11_description_persist'] = ''
        if 'default_individual_value_11_description_temp' not in ss:
            ss['default_individual_value_11_descriptiont_temp'] = ss['default_individual_value_11_description_persist']

        if 'default_individual_value_12_persist' not in ss:
            raw_content = filtered_df['individual_value_12'].iloc[0]
            ss['default_individual_value_12_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_12_temp' not in ss:
            ss['default_individual_value_12_temp'] = ss['default_individual_value_12_persist']
        pos = filtered_df.columns.get_loc('individual_value_12')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_12_value_persist' not in ss:
            ss['default_individual_value_12_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_12_value_temp' not in ss:
            ss['default_individual_value_12_value_temp'] = ss['default_individual_value_12_value_persist']
        if 'default_individual_value_12_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_12_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_12_unit_temp' not in ss:
            ss['default_individual_value_12_unit_temp'] = ss['default_individual_value_12_unit_persist']
        if 'default_individual_value_12_description_persist' not in ss:
            ss['default_individual_value_12_description_persist'] = ''
        if 'default_individual_value_12_description_temp' not in ss:
            ss['default_individual_value_12_descriptiont_temp'] = ss['default_individual_value_12_description_persist']

        if 'default_individual_value_13_persist' not in ss:
            raw_content = filtered_df['individual_value_13'].iloc[0]
            ss['default_individual_value_13_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_13_temp' not in ss:
            ss['default_individual_value_13_temp'] = ss['default_individual_value_13_persist']
        pos = filtered_df.columns.get_loc('individual_value_13')
        val = filtered_df.iloc[0, pos+1]
        if 'default_individual_value_13_value_persist' not in ss:
            ss['default_individual_value_13_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_individual_value_13_value_temp' not in ss:
            ss['default_individual_value_13_value_temp'] = ss['default_individual_value_13_value_persist']
        if 'default_individual_value_13_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_individual_value_13_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_individual_value_13_unit_temp' not in ss:
            ss['default_individual_value_13_unit_temp'] = ss['default_individual_value_13_unit_persist']
        if 'default_individual_value_13_description_persist' not in ss:
            ss['default_individual_value_13_description_persist'] = ''
        if 'default_individual_value_13_description_temp' not in ss:
            ss['default_individual_value_13_descriptiont_temp'] = ss['default_individual_value_13_description_persist']

        # st.write("DEBUG:", ss)
        st.title("自由入力式入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")
    
        # 燃料ごとの排出係数データ
        emission_factors = {
            "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
            "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
            "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
            "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
            "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        }
    
        # 燃料ごとの価格データ
        fuel_prices = {
            "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
            "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
            "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
            "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
            "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
            "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
            "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
            "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
            "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
            "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
            "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
        }
    
        fuel_heat = {
        "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
        "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
        }

        # **GHG削減量計算式**
        ghg_reduction_formula = st.text_area(
            "GHG削減量計算式",
            key='default_GHG削減量（ton-CO2）_temp',
            on_change=store_content,
            args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
        )
        ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
                st.success('GHG削減量計算式の<>はきちんと閉じられています')
            else:
                st.error('GHG削減量計算式の<>がきちんと閉じられていません')
        
        # 改行が含まれていないかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if '\n' in ss["user_input"]["GHG削減量計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **コスト削減額計算式**
        fuel = ss["user_input"].get("燃料", "")
        if fuel == "電力":
            emission_factor_str = "電気の排出係数<t-CO2/kWh>"
            fuel_price_str = "電気料金<円/kWh>"
        elif fuel == "都市ガス":
            emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
            fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        else:
            emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
            price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
            emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
            fuel_price_str = f"{price_name}<{price_unit}>"

        cost_reduction_formula = st.text_area(
            "コスト削減額計算式",
            key='default_コスト削減額（円/年）_temp',
            on_change=store_content,
            args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
        )
        ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
                st.success('コスト削減額計算式の<>はきちんと閉じられています')
            else:
                st.error('コスト削減額計算式の<>がきちんと閉じられていません')
        
        # 改行が含まれていないかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if '\n' in ss["user_input"]["コスト削減額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **投資額計算式**
        investment_amount_formula = st.text_area(
            "投資額計算式",
            key='default_投資額（円）_temp',
            on_change=store_content,
            args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
        )
        ss["user_input"]["投資額計算式"] = investment_amount_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
                st.success('投資額計算式の<>はきちんと閉じられています')
            else:
                st.error('投資額計算式の<>がきちんと閉じられていません')

        # 改行が含まれていないかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if '\n' in ss["user_input"]["投資額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **追加投資額計算式**
        additional_investment_amount_formula = st.text_area(
            "追加投資額計算式",
            key='default_追加投資額（円）_temp',
            on_change=store_content,
            args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
        )
        ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
                st.success('追加投資額計算式の<>はきちんと閉じられています')
            else:
                st.error('追加投資額計算式の<>がきちんと閉じられていません')

        # 改行が含まれていないかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if '\n' in ss["user_input"]["追加投資額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
                st.error('計算式中にスペースが含まれています')

        st.subheader("取得済みインプット")
        acquired_input_1_name = st.text_input(
            "インプットの名前",
            key='default_acquired_input_1_temp',
            on_change=store_content,
            args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
        )
        ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

        acquired_input_1_value = st.number_input(
            "数字",
            min_value=0.0,
            step=1.0,
            key='default_acquired_input_1_value_temp',
            on_change=store_content,
            args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
        )
        ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

        acquired_input_1_unit = st.text_input(
            "単位",
            key='default_acquired_input_1_unit_temp',
            on_change=store_content,
            args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
        )
        ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

        # **追加インプット 4個**
        for i in range(4):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            key_name_temp = f'default_additional_input_{i+1}_temp'
            key_name_persist = f'default_additional_input_{i+1}_persist'
            key_value_temp = f'default_additional_input_{i+1}_value_temp'
            key_value_persist = f'default_additional_input_{i+1}_value_persist'
            key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
            key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

            acquired_input_name = st.text_input(
                name_key,
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][name_key] = acquired_input_name

            acquired_input_value = st.number_input(
                num_key,
                min_value=0.0,
                step=1.0,
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][num_key] = acquired_input_value

            acquired_input_unit = st.text_input(
                unit_key,
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][unit_key] = acquired_input_unit
        
        # 追加インプット5,6(本来は不要(？)だと思われるため、デフォルトは空 or NaNにしておく)
        for i in range(5, 6+1):
            st.subheader(f"追加インプット {i}")
            name_key = f"追加インプット{i}の名前"
            num_key = f"追加インプット{i}の数字"
            unit_key = f"追加インプット{i}の単位"

            acquired_input_name = st.text_input(
                name_key,
                value=''
            )
            ss["user_input"][name_key] = acquired_input_name

            acquired_input_value = st.number_input(
                num_key,
                min_value=0.0,
                step=1.0,
                value=np.nan
            )
            ss["user_input"][num_key] = acquired_input_value

            acquired_input_unit = st.text_input(
                unit_key,
                value=''
            )
            ss["user_input"][unit_key] = acquired_input_unit

        # 燃料取得
        fuel = ss["user_input"].get("燃料", "")

        # **事前定義された値**
        predefined_values = [
            ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
            ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
            ("想定稼働年数", 10, "年", "")
        ]

        for name, value, unit, description in predefined_values:
            st.subheader(f"規定値: {name}")
            
            name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
            value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

            # セッションステートにデフォルト値をセット
            ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
            ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")
            if name == '電気の排出係数':
                key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
                key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
                key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
                key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
                key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
                key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
                key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
                key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
            elif name == '電気料金':
                key_name_temp = 'default_individual_value(electric_bill)_temp'
                key_name_persist = 'default_individual_value(electric_bill)_persist'
                key_value_temp = 'default_individual_value(electric_bill)_value_temp'
                key_value_persist = 'default_individual_value(electric_bill)_value_persist'
                key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
                key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
                key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
                key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
            elif name == "想定稼働年数":
                key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
                key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
                key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
                key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
                key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
                key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
                key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
                key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

            # ユーザー入力欄
            individual_value_name = st.text_input(
                f"規定値({name})の名前", 
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][f"規定値({name})の名前"] = individual_value_name

            individual_value_value = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][f"規定値({name})の数字"] = individual_value_value

            individual_value_unit = st.text_input(
                f"規定値({name})の単位",
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][f"規定値({name})の単位"] = individual_value_unit

            individual_value_description = st.text_area(
                f"規定値({name})の説明",
                key=key_description_temp,
                on_change=store_content,
                args=(key_description_persist, key_description_temp)
            )
            ss["user_input"][f"規定値({name})の説明"] = individual_value_description
        

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = ss["user_input"].get("燃料", "")
            value_format = "%.2f"
        
            if i == 0:
                name, unit = "省エネ率", "%"
                value = None
            elif i == 1:
                name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
                value_format = "%.6f"
            elif i == 2:
                name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
                value_format = "%.2f"
            else:
                name, value, unit, description = "", None, "", ""
                value_format = "%.2f"
            
            ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
            ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
            ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            ss["user_input"].setdefault(f"規定値{i+1}_説明", description)
            key_name_temp = f'default_individual_value_{i+1}_temp'
            key_name_persist = f'default_individual_value_{i+1}_persist'
            key_value_temp = f'default_individual_value_{i+1}_value_temp'
            key_value_persist = f'default_individual_value_{i+1}_value_persist'
            key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
            key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
            key_description_temp = f'default_individual_value_{i+1}_description_temp'
            key_description_persist = f'default_individual_value_{i+1}_description_persist'

            individual_value_name = st.text_input(
                f"規定値 {i+1} の名前",
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][f"規定値{i+1}_名前"] = individual_value_name

            individual_value_value = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][f"規定値{i+1}_数字"] = individual_value_value

            individual_value_unit = st.text_input(
                f"規定値 {i+1} の単位",
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][f"規定値{i+1}_単位"] = individual_value_unit

            individual_value_description = st.text_area(
                f"規定値 {i+1} の説明",
                key=key_description_temp,
                on_change=store_content,
                args=(key_description_persist, key_description_temp)
            )
            ss["user_input"][f"規定値{i+1}_説明"] =individual_value_description

        # **推測値テンプレートの選択**
        # 自由入力で固定
        prediction_template = st.selectbox(
            "推測値のテンプレはどれを使用しますか？", 
            ["1(容量推測)", "2(台数推測)", "3(自由入力)"], 
            index=2, 
            disabled=True
        )
        ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
        ss["user_input"]["推測値のテンプレ"] = prediction_template
        col1, col2 = st.columns(2)
        with col1:
            if st.button("入力を確定", key="submit"):
                prediction_template = ss["user_input"].get("推測値のテンプレ", "")
                ss["previous_page"] = ss["page"]
                if prediction_template.startswith("1"):
                    next_page("page3A")
                elif prediction_template.startswith("2"):
                    next_page("page3B")
                else:
                    next_page("page3C")
        with col2:
            if st.button("エラーチェック", key="check"):
                # チェックする計算式の辞書
                target_formula_dict = {
                    "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                    "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                    "投資額計算式": ss["user_input"]["投資額計算式"],
                    "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
                }
                # チェックする因数
                target_factors = [
                    ss["user_input"]["取得済みインプットの名前"],
                    ss["user_input"]["追加インプット1の名前"],
                    ss["user_input"]["追加インプット2の名前"],
                    ss["user_input"]["追加インプット3の名前"],
                    ss["user_input"]["追加インプット4の名前"],
                    ss["user_input"]["規定値(電気の排出係数)の名前"],
                    ss["user_input"]["規定値(電気料金)の名前"],
                    ss["user_input"]["規定値(想定稼働年数)の名前"],
                    ss["user_input"]["規定値1_名前"],
                    ss["user_input"]["規定値2_名前"],
                    ss["user_input"]["規定値3_名前"],
                    ss["user_input"]["規定値4_名前"],
                    ss["user_input"]["規定値5_名前"],
                    ss["user_input"]["規定値6_名前"],
                    ss["user_input"]["規定値7_名前"],
                    ss["user_input"]["規定値8_名前"],
                    ss["user_input"]["規定値9_名前"],
                    ss["user_input"]["規定値10_名前"],
                    ss["user_input"]["規定値11_名前"],
                    ss["user_input"]["規定値12_名前"],
                    ss["user_input"]["規定値13_名前"]
                ]

                for formula_name, formula in target_formula_dict.items():
                    parsed_list = split_formula(formula)

                    # 存在しなかった要素を保持するためのリスト
                    not_found_items = []

                    # リスト内の要素を1つずつ確認
                    for item in parsed_list:
                        found_in_any = False
                        # target_factorsに含まれる各因数についてチェック
                        for factor in target_factors:
                            if item == factor:
                                found_in_any = True
                                break
                        if not found_in_any:
                            not_found_items.append(item)
                    if not_found_items:
                        st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                        for i in not_found_items:
                            st.markdown(f"- {i}")
                    else:
                        st.success(f"✅ {formula_name}の因数に問題はありません")
    
        if st.button("戻る"):
            next_page("page1")

    elif ss['selected_option_persist'] == 'jsonファイルを読み込む':
        st.write(f'「{ss['default_data']['設備']}_{ss['default_data']['施策名']}_{ss['default_data']['燃料']}」をテンプレートとして使用しています')

        if 'default_GHG削減量（ton-CO2）_persist' not in ss:
            ss['default_GHG削減量（ton-CO2）_persist'] = ss['default_data']['GHG削減量計算式']
        if 'default_GHG削減量（ton-CO2）_temp' not in ss:
            ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']

        if 'default_コスト削減額（円/年）_persist' not in ss:
            ss['default_コスト削減額（円/年）_persist'] = ss['default_data']['コスト削減額計算式']
        if 'default_コスト削減額（円/年）_temp' not in ss:
            ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']

        if 'default_投資額（円）_persist' not in ss:
            ss['default_投資額（円）_persist'] = ss['default_data']['投資額計算式']
        if 'default_投資額（円）_temp' not in ss:
            ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']

        if 'default_追加投資額（円）_persist' not in ss:
            ss['default_追加投資額（円）_persist'] = ss['default_data']['追加投資額計算式']
        if 'default_追加投資額（円）_temp' not in ss:
            ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

        if 'default_acquired_input_1_persist' not in ss:
            ss['default_acquired_input_1_persist'] = ss['default_data']['取得済みインプットの名前']
        if 'default_acquired_input_1_temp' not in ss:
            ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']
        if 'default_acquired_input_1_value_persist' not in ss:
            raw_content = ss['default_data']['取得済みインプットの数字']
            ss['default_acquired_input_1_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_acquired_input_1_value_temp' not in ss:
            ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']
        if 'default_acquired_input_1_unit_persist' not in ss:
            ss['default_acquired_input_1_unit_persist'] = ss['default_data']['取得済みインプットの単位']
        if 'default_acquired_input_1_unit_temp' not in ss:
            ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']

        if 'default_additional_input_1_persist' not in ss:
            ss['default_additional_input_1_persist'] = ss['default_data']['追加インプット1の名前']
        if 'default_additional_input_1_temp' not in ss:
            ss['default_additional_input_1_temp'] = ss['default_additional_input_1_persist']
        if 'default_additional_input_1_value_persist' not in ss:
            raw_content = ss['default_data']['追加インプット1の数字']
            ss['default_additional_input_1_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_additional_input_1_value_temp' not in ss:
            ss['default_additional_input_1_value_temp'] = ss['default_additional_input_1_value_persist']
        if 'default_additional_input_1_unit_persist' not in ss:
            ss['default_additional_input_1_unit_persist'] = ss['default_data']['追加インプット1の単位']
        if 'default_additional_input_1_unit_temp' not in ss:
            ss['default_additional_input_1_unit_temp'] = ss['default_additional_input_1_unit_persist']

        if 'default_additional_input_2_persist' not in ss:
            ss['default_additional_input_2_persist'] = ss['default_data']['追加インプット2の名前']
        if 'default_additional_input_2_temp' not in ss:
            ss['default_additional_input_2_temp'] = ss['default_additional_input_2_persist']
        if 'default_additional_input_2_value_persist' not in ss:
            raw_content = ss['default_data']['追加インプット2の数字']
            ss['default_additional_input_2_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_additional_input_2_value_temp' not in ss:
            ss['default_additional_input_2_value_temp'] = ss['default_additional_input_2_value_persist']
        if 'default_additional_input_2_unit_persist' not in ss:
            ss['default_additional_input_2_unit_persist'] = ss['default_data']['追加インプット2の単位']
        if 'default_additional_input_2_unit_temp' not in ss:
            ss['default_additional_input_2_unit_temp'] = ss['default_additional_input_2_unit_persist']

        if 'default_additional_input_3_persist' not in ss:
            ss['default_additional_input_3_persist'] = ss['default_data']['追加インプット3の名前']
        if 'default_additional_input_3_temp' not in ss:
            ss['default_additional_input_3_temp'] = ss['default_additional_input_3_persist']
        if 'default_additional_input_3_value_persist' not in ss:
            raw_content = ss['default_data']['追加インプット3の数字']
            ss['default_additional_input_3_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_additional_input_3_value_temp' not in ss:
            ss['default_additional_input_3_value_temp'] = ss['default_additional_input_3_value_persist']
        if 'default_additional_input_3_unit_persist' not in ss:
            ss['default_additional_input_3_unit_persist'] = ss['default_data']['追加インプット3の単位']
        if 'default_additional_input_3_unit_temp' not in ss:
            ss['default_additional_input_3_unit_temp'] = ss['default_additional_input_3_unit_persist']

        if 'default_additional_input_4_persist' not in ss:
            ss['default_additional_input_4_persist'] = ss['default_data']['追加インプット4の名前']
        if 'default_additional_input_4_temp' not in ss:
            ss['default_additional_input_4_temp'] = ss['default_additional_input_4_persist']
        if 'default_additional_input_4_value_persist' not in ss:
            raw_contentn = ss['default_data']['追加インプット4の数字']
            ss['default_additional_input_4_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_additional_input_4_value_temp' not in ss:
            ss['default_additional_input_4_value_temp'] = ss['default_additional_input_4_value_persist']
        if 'default_additional_input_4_unit_persist' not in ss:
            ss['default_additional_input_4_unit_persist'] = ss['default_data']['追加インプット4の単位']
        if 'default_additional_input_4_unit_temp' not in ss:
            ss['default_additional_input_4_unit_temp'] = ss['default_additional_input_4_unit_persist']

        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = ss['default_data']['規定値(電気の排出係数)の名前']
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            raw_content = ss['default_data']['規定値(電気の排出係数)の数字']
            ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = ss['default_data']['規定値(電気の排出係数)の単位']
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = ss['default_data']['規定値(電気の排出係数)の説明']
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']

        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = ss['default_data']['規定値(電気料金)の名前']
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            raw_content = ss['default_data']['規定値(電気料金)の数字']
            ss['default_individual_value(electric_bill)_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = ss['default_data']['規定値(電気料金)の単位']
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = ss['default_data']['規定値(電気料金)の説明']
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']

        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = ss['default_data']['規定値(想定稼働年数)の名前']
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            raw_content = ss['default_data']['規定値(想定稼働年数)の数字']
            ss['default_individual_value(estimated_lifetime)_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = ss['default_data']['規定値(想定稼働年数)の単位']
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ss['default_data']['規定値(想定稼働年数)の説明']
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

        if 'default_individual_value_1_persist' not in ss:
            ss['default_individual_value_1_persist'] = ss['default_data']['規定値1_名前']
        if 'default_individual_value_1_temp' not in ss:
            ss['default_individual_value_1_temp'] = ss['default_individual_value_1_persist']
        if 'default_individual_value_1_value_persist' not in ss:
            raw_content = ss['default_data']['規定値1_数字']
            ss['default_individual_value_1_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_1_value_temp' not in ss:
            ss['default_individual_value_1_value_temp'] = ss['default_individual_value_1_value_persist']
        if 'default_individual_value_1_unit_persist' not in ss:
            ss['default_individual_value_1_unit_persist'] = ss['default_data']['規定値1_単位']
        if 'default_individual_value_1_unit_temp' not in ss:
            ss['default_individual_value_1_unit_temp'] = ss['default_individual_value_1_unit_persist']
        if 'default_individual_value_1_description_persist' not in ss:
            ss['default_individual_value_1_description_persist'] = ss['default_data']['規定値1_説明']
        if 'default_individual_value_1_description_temp' not in ss:
            ss['default_individual_value_1_descriptiont_temp'] = ss['default_individual_value_1_description_persist']

        if 'default_individual_value_2_persist' not in ss:
            ss['default_individual_value_2_persist'] = ss['default_data']['規定値2_名前']
        if 'default_individual_value_2_temp' not in ss:
            ss['default_individual_value_2_temp'] = ss['default_individual_value_2_persist']
        if 'default_individual_value_2_value_persist' not in ss:
            raw_content = ss['default_data']['規定値2_数字']
            ss['default_individual_value_2_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_2_value_temp' not in ss:
            ss['default_individual_value_2_value_temp'] = ss['default_individual_value_2_value_persist']
        if 'default_individual_value_2_unit_persist' not in ss:
            ss['default_individual_value_2_unit_persist'] = ss['default_data']['規定値2_単位']
        if 'default_individual_value_2_unit_temp' not in ss:
            ss['default_individual_value_2_unit_temp'] = ss['default_individual_value_2_unit_persist']
        if 'default_individual_value_2_description_persist' not in ss:
            ss['default_individual_value_2_description_persist'] = ss['default_data']['規定値2_説明']
        if 'default_individual_value_2_description_temp' not in ss:
            ss['default_individual_value_2_descriptiont_temp'] = ss['default_individual_value_2_description_persist']

        if 'default_individual_value_3_persist' not in ss:
            ss['default_individual_value_3_persist'] = ss['default_data']['規定値3_名前']
        if 'default_individual_value_3_temp' not in ss:
            ss['default_individual_value_3_temp'] = ss['default_individual_value_3_persist']
        if 'default_individual_value_3_value_persist' not in ss:
            raw_content = ss['default_data']['規定値3_数字']
            ss['default_individual_value_3_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_3_value_temp' not in ss:
            ss['default_individual_value_3_value_temp'] = ss['default_individual_value_3_value_persist']
        if 'default_individual_value_3_unit_persist' not in ss:
            ss['default_individual_value_3_unit_persist'] = ss['default_data']['規定値3_単位']
        if 'default_individual_value_3_unit_temp' not in ss:
            ss['default_individual_value_3_unit_temp'] = ss['default_individual_value_3_unit_persist']
        if 'default_individual_value_3_description_persist' not in ss:
            ss['default_individual_value_3_description_persist'] = ss['default_data']['規定値3_説明']
        if 'default_individual_value_3_description_temp' not in ss:
            ss['default_individual_value_3_descriptiont_temp'] = ss['default_individual_value_3_description_persist']

        if 'default_individual_value_4_persist' not in ss:
            ss['default_individual_value_4_persist'] = ss['default_data']['規定値4_名前']
        if 'default_individual_value_4_temp' not in ss:
            ss['default_individual_value_4_temp'] = ss['default_individual_value_4_persist']
        if 'default_individual_value_4_value_persist' not in ss:
            raw_content = ss['default_data']['規定値4_数字']
            ss['default_individual_value_4_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_4_value_temp' not in ss:
            ss['default_individual_value_4_value_temp'] = ss['default_individual_value_4_value_persist']
        if 'default_individual_value_4_unit_persist' not in ss:
            ss['default_individual_value_4_unit_persist'] = ss['default_data']['規定値4_単位']
        if 'default_individual_value_4_unit_temp' not in ss:
            ss['default_individual_value_4_unit_temp'] = ss['default_individual_value_4_unit_persist']
        if 'default_individual_value_4_description_persist' not in ss:
            ss['default_individual_value_4_description_persist'] = ss['default_data']['規定値4_説明']
        if 'default_individual_value_4_description_temp' not in ss:
            ss['default_individual_value_4_descriptiont_temp'] = ss['default_individual_value_4_description_persist']

        if 'default_individual_value_5_persist' not in ss:
            ss['default_individual_value_5_persist'] = ss['default_data']['規定値5_名前']
        if 'default_individual_value_5_temp' not in ss:
            ss['default_individual_value_5_temp'] = ss['default_individual_value_5_persist']
        if 'default_individual_value_5_value_persist' not in ss:
            raw_content = ss['default_data']['規定値5_数字']
            ss['default_individual_value_5_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_5_value_temp' not in ss:
            ss['default_individual_value_5_value_temp'] = ss['default_individual_value_5_value_persist']
        if 'default_individual_value_5_unit_persist' not in ss:
            ss['default_individual_value_5_unit_persist'] =  ss['default_data']['規定値5_単位']
        if 'default_individual_value_5_unit_temp' not in ss:
            ss['default_individual_value_5_unit_temp'] = ss['default_individual_value_5_unit_persist']
        if 'default_individual_value_5_description_persist' not in ss:
            ss['default_individual_value_5_description_persist'] = ss['default_data']['規定値5_説明']
        if 'default_individual_value_5_description_temp' not in ss:
            ss['default_individual_value_5_descriptiont_temp'] = ss['default_individual_value_5_description_persist']

        if 'default_individual_value_6_persist' not in ss:
            ss['default_individual_value_6_persist'] = ss['default_data']['規定値6_名前']
        if 'default_individual_value_6_temp' not in ss:
            ss['default_individual_value_6_temp'] = ss['default_individual_value_6_persist']
        if 'default_individual_value_6_value_persist' not in ss:
            raw_content = ss['default_data']['規定値6_数字']
            ss['default_individual_value_6_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_6_value_temp' not in ss:
            ss['default_individual_value_6_value_temp'] = ss['default_individual_value_6_value_persist']
        if 'default_individual_value_6_unit_persist' not in ss:
            ss['default_individual_value_6_unit_persist'] = ss['default_data']['規定値6_単位']
        if 'default_individual_value_6_unit_temp' not in ss:
            ss['default_individual_value_6_unit_temp'] = ss['default_individual_value_6_unit_persist']
        if 'default_individual_value_6_description_persist' not in ss:
            ss['default_individual_value_6_description_persist'] = ss['default_data']['規定値6_説明']
        if 'default_individual_value_6_description_temp' not in ss:
            ss['default_individual_value_6_descriptiont_temp'] = ss['default_individual_value_6_description_persist']

        if 'default_individual_value_7_persist' not in ss:
            ss['default_individual_value_7_persist'] = ss['default_data']['規定値7_名前']
        if 'default_individual_value_7_temp' not in ss:
            ss['default_individual_value_7_temp'] = ss['default_individual_value_7_persist']
        if 'default_individual_value_7_value_persist' not in ss:
            raw_content = ss['default_data']['規定値7_数字']
            ss['default_individual_value_7_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_7_value_temp' not in ss:
            ss['default_individual_value_7_value_temp'] = ss['default_individual_value_7_value_persist']
        if 'default_individual_value_7_unit_persist' not in ss:
            ss['default_individual_value_7_unit_persist'] = ss['default_data']['規定値7_単位']
        if 'default_individual_value_7_unit_temp' not in ss:
            ss['default_individual_value_7_unit_temp'] = ss['default_individual_value_7_unit_persist']
        if 'default_individual_value_7_description_persist' not in ss:
            ss['default_individual_value_7_description_persist'] = ss['default_data']['規定値7_説明']
        if 'default_individual_value_7_description_temp' not in ss:
            ss['default_individual_value_7_descriptiont_temp'] = ss['default_individual_value_7_description_persist']

        if 'default_individual_value_8_persist' not in ss:
            ss['default_individual_value_8_persist'] = ss['default_data']['規定値8_名前']
        if 'default_individual_value_8_temp' not in ss:
            ss['default_individual_value_8_temp'] = ss['default_individual_value_8_persist']
        if 'default_individual_value_8_value_persist' not in ss:
            raw_content = ss['default_data']['規定値8_数字']
            ss['default_individual_value_8_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_8_value_temp' not in ss:
            ss['default_individual_value_8_value_temp'] = ss['default_individual_value_8_value_persist']
        if 'default_individual_value_8_unit_persist' not in ss:
            ss['default_individual_value_8_unit_persist'] = ss['default_data']['規定値8_単位']
        if 'default_individual_value_8_unit_temp' not in ss:
            ss['default_individual_value_8_unit_temp'] = ss['default_individual_value_8_unit_persist']
        if 'default_individual_value_8_description_persist' not in ss:
            ss['default_individual_value_8_description_persist'] = ss['default_data']['規定値8_説明']
        if 'default_individual_value_8_description_temp' not in ss:
            ss['default_individual_value_8_descriptiont_temp'] = ss['default_individual_value_8_description_persist']

        if 'default_individual_value_9_persist' not in ss:
            ss['default_individual_value_9_persist'] = ss['default_data']['規定値9_名前']
        if 'default_individual_value_9_temp' not in ss:
            ss['default_individual_value_9_temp'] = ss['default_individual_value_9_persist']
        if 'default_individual_value_9_value_persist' not in ss:
            raw_content = ss['default_data']['規定値9_数字']
            ss['default_individual_value_9_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_9_value_temp' not in ss:
            ss['default_individual_value_9_value_temp'] = ss['default_individual_value_9_value_persist']
        if 'default_individual_value_9_unit_persist' not in ss:
            ss['default_individual_value_9_unit_persist'] = ss['default_data']['規定値9_単位']
        if 'default_individual_value_9_unit_temp' not in ss:
            ss['default_individual_value_9_unit_temp'] = ss['default_individual_value_9_unit_persist']
        if 'default_individual_value_9_description_persist' not in ss:
            ss['default_individual_value_9_description_persist'] = ss['default_data']['規定値9_説明']
        if 'default_individual_value_9_description_temp' not in ss:
            ss['default_individual_value_9_descriptiont_temp'] = ss['default_individual_value_9_description_persist']

        if 'default_individual_value_10_persist' not in ss:
            ss['default_individual_value_10_persist'] = ss['default_data']['規定値10_名前']
        if 'default_individual_value_10_temp' not in ss:
            ss['default_individual_value_10_temp'] = ss['default_individual_value_10_persist']
        if 'default_individual_value_10_value_persist' not in ss:
            raw_content = ss['default_data']['規定値10_数字']
            ss['default_individual_value_10_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_10_value_temp' not in ss:
            ss['default_individual_value_10_value_temp'] = ss['default_individual_value_10_value_persist']
        if 'default_individual_value_10_unit_persist' not in ss: 
            ss['default_individual_value_10_unit_persist'] = ss['default_data']['規定値10_単位']
        if 'default_individual_value_10_unit_temp' not in ss: 
            ss['default_individual_value_10_unit_temp'] = ss['default_individual_value_10_unit_persist']
        if 'default_individual_value_10_description_persist' not in ss:
            ss['default_individual_value_10_description_persist'] = ss['default_data']['規定値10_説明']
        if 'default_individual_value_10_description_temp' not in ss:
            ss['default_individual_value_10_descriptiont_temp'] = ss['default_individual_value_10_description_persist']

        if 'default_individual_value_11_persist' not in ss:
            ss['default_individual_value_11_persist'] = ss['default_data']['規定値11_名前']
        if 'default_individual_value_11_temp' not in ss:
            ss['default_individual_value_11_temp'] = ss['default_individual_value_11_persist']
        if 'default_individual_value_11_value_persist' not in ss:
            raw_content = ss['default_data']['規定値11_数字']
            ss['default_individual_value_11_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_11_value_temp' not in ss:
            ss['default_individual_value_11_value_temp'] = ss['default_individual_value_11_value_persist']
        if 'default_individual_value_11_unit_persist' not in ss:
            ss['default_individual_value_11_unit_persist'] = ss['default_data']['規定値11_単位']
        if 'default_individual_value_11_unit_temp' not in ss:
            ss['default_individual_value_11_unit_temp'] = ss['default_individual_value_11_unit_persist']
        if 'default_individual_value_11_description_persist' not in ss:
            ss['default_individual_value_11_description_persist'] = ss['default_data']['規定値11_説明']
        if 'default_individual_value_11_description_temp' not in ss:
            ss['default_individual_value_11_descriptiont_temp'] = ss['default_individual_value_11_description_persist']

        if 'default_individual_value_12_persist' not in ss:
            ss['default_individual_value_12_persist'] = ss['default_data']['規定値12_名前']
        if 'default_individual_value_12_temp' not in ss:
            ss['default_individual_value_12_temp'] = ss['default_individual_value_12_persist']
        if 'default_individual_value_12_value_persist' not in ss:
            raw_content = ss['default_data']['規定値12_数字']
            ss['default_individual_value_12_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_12_value_temp' not in ss:
            ss['default_individual_value_12_value_temp'] = ss['default_individual_value_12_value_persist']
        if 'default_individual_value_12_unit_persist' not in ss:
            ss['default_individual_value_12_unit_persist'] = ss['default_data']['規定値12_単位']
        if 'default_individual_value_12_unit_temp' not in ss:
            ss['default_individual_value_12_unit_temp'] = ss['default_individual_value_12_unit_persist']
        if 'default_individual_value_12_description_persist' not in ss:
            ss['default_individual_value_12_description_persist'] = ss['default_data']['規定値12_説明']
        if 'default_individual_value_12_description_temp' not in ss:
            ss['default_individual_value_12_descriptiont_temp'] = ss['default_individual_value_12_description_persist']

        if 'default_individual_value_13_persist' not in ss:
            ss['default_individual_value_13_persist'] = ss['default_data']['規定値13_名前']
        if 'default_individual_value_13_temp' not in ss:
            ss['default_individual_value_13_temp'] = ss['default_individual_value_13_persist']
        if 'default_individual_value_13_value_persist' not in ss:
            raw_content = ss['default_data']['規定値13_数字']
            ss['default_individual_value_13_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_individual_value_13_value_temp' not in ss:
            ss['default_individual_value_13_value_temp'] = ss['default_individual_value_13_value_persist']
        if 'default_individual_value_13_unit_persist' not in ss:
            ss['default_individual_value_13_unit_persist'] = ss['default_data']['規定値13_単位']
        if 'default_individual_value_13_unit_temp' not in ss:
            ss['default_individual_value_13_unit_temp'] = ss['default_individual_value_13_unit_persist']
        if 'default_individual_value_13_description_persist' not in ss:
            ss['default_individual_value_13_description_persist'] = ss['default_data']['規定値13_説明']
        if 'default_individual_value_13_description_temp' not in ss:
            ss['default_individual_value_13_descriptiont_temp'] = ss['default_individual_value_13_description_persist']

        # st.write("DEBUG:", ss)
        st.title("自由入力式入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")
    
        # 燃料ごとの排出係数データ
        emission_factors = {
            "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
            "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
            "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
            "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
            "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
            "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
            "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        }
    
        # 燃料ごとの価格データ
        fuel_prices = {
            "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
            "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
            "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
            "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
            "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
            "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
            "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
            "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
            "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
            "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
            "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
        }
    
        fuel_heat = {
        "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
        "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
        "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
        "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
        }

        # **GHG削減量計算式**
        ghg_reduction_formula = st.text_area(
            "GHG削減量計算式",
            key='default_GHG削減量（ton-CO2）_temp',
            on_change=store_content,
            args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
        )
        ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
                st.success('GHG削減量計算式の<>はきちんと閉じられています')
            else:
                st.error('GHG削減量計算式の<>がきちんと閉じられていません')
        
        # 改行が含まれていないかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if '\n' in ss["user_input"]["GHG削減量計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["GHG削減量計算式"] != '':
            if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **コスト削減額計算式**
        fuel = ss["user_input"].get("燃料", "")
        if fuel == "電力":
            emission_factor_str = "電気の排出係数<t-CO2/kWh>"
            fuel_price_str = "電気料金<円/kWh>"
        elif fuel == "都市ガス":
            emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
            fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        else:
            emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
            price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
            emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
            fuel_price_str = f"{price_name}<{price_unit}>"

        cost_reduction_formula = st.text_area(
            "コスト削減額計算式",
            key='default_コスト削減額（円/年）_temp',
            on_change=store_content,
            args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
        )
        ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
                st.success('コスト削減額計算式の<>はきちんと閉じられています')
            else:
                st.error('コスト削減額計算式の<>がきちんと閉じられていません')
        
        # 改行が含まれていないかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if '\n' in ss["user_input"]["コスト削減額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["コスト削減額計算式"] != '':
            if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **投資額計算式**
        investment_amount_formula = st.text_area(
            "投資額計算式",
            key='default_投資額（円）_temp',
            on_change=store_content,
            args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
        )
        ss["user_input"]["投資額計算式"] = investment_amount_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
                st.success('投資額計算式の<>はきちんと閉じられています')
            else:
                st.error('投資額計算式の<>がきちんと閉じられていません')

        # 改行が含まれていないかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if '\n' in ss["user_input"]["投資額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["投資額計算式"] != '':
            if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
                st.error('計算式中にスペースが含まれています')

        # **追加投資額計算式**
        additional_investment_amount_formula = st.text_area(
            "追加投資額計算式",
            key='default_追加投資額（円）_temp',
            on_change=store_content,
            args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
        )
        ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

        # <>がきちんと閉じられているかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
                st.success('追加投資額計算式の<>はきちんと閉じられています')
            else:
                st.error('追加投資額計算式の<>がきちんと閉じられていません')

        # 改行が含まれていないかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if '\n' in ss["user_input"]["追加投資額計算式"]:
                st.error('計算式中に改行が含まれています')
        
        # 半角スペース・全角スペース・タブが含まれていないかチェック
        if ss["user_input"]["追加投資額計算式"] != '':
            if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
                st.error('計算式中にスペースが含まれています')

        st.subheader("取得済みインプット")
        acquired_input_1_name = st.text_input(
            "インプットの名前",
            key='default_acquired_input_1_temp',
            on_change=store_content,
            args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
        )
        ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

        acquired_input_1_value = st.number_input(
            "数字",
            min_value=0.0,
            step=1.0,
            key='default_acquired_input_1_value_temp',
            on_change=store_content,
            args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
        )
        ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

        acquired_input_1_unit = st.text_input(
            "単位",
            key='default_acquired_input_1_unit_temp',
            on_change=store_content,
            args=('default_acquired_input_1_unit_persist', 'default_acquired_input_1_unit_temp')
        )
        ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

        # **追加インプット 4個**
        for i in range(4):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            key_name_temp = f'default_additional_input_{i+1}_temp'
            key_name_persist = f'default_additional_input_{i+1}_persist'
            key_value_temp = f'default_additional_input_{i+1}_value_temp'
            key_value_persist = f'default_additional_input_{i+1}_value_persist'
            key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
            key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

            acquired_input_name = st.text_input(
                name_key,
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][name_key] = acquired_input_name

            acquired_input_value = st.number_input(
                num_key,
                min_value=0.0,
                step=1.0,
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][num_key] = acquired_input_value

            acquired_input_unit = st.text_input(
                unit_key,
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][unit_key] = acquired_input_unit
        
        # 追加インプット5,6(本来は不要(？)だと思われるため、デフォルトは空 or NaNにしておく)
        for i in range(5, 6+1):
            st.subheader(f"追加インプット {i}")
            name_key = f"追加インプット{i}の名前"
            num_key = f"追加インプット{i}の数字"
            unit_key = f"追加インプット{i}の単位"

            acquired_input_name = st.text_input(
                name_key,
                value=''
            )
            ss["user_input"][name_key] = acquired_input_name

            acquired_input_value = st.number_input(
                num_key,
                min_value=0.0,
                step=1.0,
                value=np.nan
            )
            ss["user_input"][num_key] = acquired_input_value

            acquired_input_unit = st.text_input(
                unit_key,
                value=''
            )
            ss["user_input"][unit_key] = acquired_input_unit

        # 燃料取得
        fuel = ss["user_input"].get("燃料", "")

        # **事前定義された値**
        predefined_values = [
            ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
            ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
            ("想定稼働年数", 10, "年", "")
        ]

        for name, value, unit, description in predefined_values:
            st.subheader(f"規定値: {name}")
            
            name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
            value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

            # セッションステートにデフォルト値をセット
            ss["user_input"].setdefault(f"規定値({name})の名前", name_display)
            ss["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            ss["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            ss["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")
            if name == '電気の排出係数':
                key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
                key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
                key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
                key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
                key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
                key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
                key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
                key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
            elif name == '電気料金':
                key_name_temp = 'default_individual_value(electric_bill)_temp'
                key_name_persist = 'default_individual_value(electric_bill)_persist'
                key_value_temp = 'default_individual_value(electric_bill)_value_temp'
                key_value_persist = 'default_individual_value(electric_bill)_value_persist'
                key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
                key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
                key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
                key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
            elif name == "想定稼働年数":
                key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
                key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
                key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
                key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
                key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
                key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
                key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
                key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

            # ユーザー入力欄
            individual_value_name = st.text_input(
                f"規定値({name})の名前", 
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][f"規定値({name})の名前"] = individual_value_name

            individual_value_value = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][f"規定値({name})の数字"] = individual_value_value

            individual_value_unit = st.text_input(
                f"規定値({name})の単位",
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][f"規定値({name})の単位"] = individual_value_unit

            individual_value_description = st.text_area(
                f"規定値({name})の説明",
                key=key_description_temp,
                on_change=store_content,
                args=(key_description_persist, key_description_temp)
            )
            ss["user_input"][f"規定値({name})の説明"] = individual_value_description
        

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = ss["user_input"].get("燃料", "")
            value_format = "%.2f"
        
            if i == 0:
                name, unit = "省エネ率", "%"
                value = None
            elif i == 1:
                name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
                value_format = "%.6f"
            elif i == 2:
                name, value, unit, description = fuel_prices.get(fuel, ("", None, "", ""))
                value_format = "%.2f"
            else:
                name, value, unit, description = "", None, "", ""
                value_format = "%.2f"
            
            ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
            ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
            ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            ss["user_input"].setdefault(f"規定値{i+1}_説明", description)
            key_name_temp = f'default_individual_value_{i+1}_temp'
            key_name_persist = f'default_individual_value_{i+1}_persist'
            key_value_temp = f'default_individual_value_{i+1}_value_temp'
            key_value_persist = f'default_individual_value_{i+1}_value_persist'
            key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
            key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
            key_description_temp = f'default_individual_value_{i+1}_description_temp'
            key_description_persist = f'default_individual_value_{i+1}_description_persist'

            individual_value_name = st.text_input(
                f"規定値 {i+1} の名前",
                key=key_name_temp,
                on_change=store_content,
                args=(key_name_persist, key_name_temp)
            )
            ss["user_input"][f"規定値{i+1}_名前"] = individual_value_name

            individual_value_value = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                key=key_value_temp,
                on_change=store_content,
                args=(key_value_persist, key_value_temp)
            )
            ss["user_input"][f"規定値{i+1}_数字"] = individual_value_value

            individual_value_unit = st.text_input(
                f"規定値 {i+1} の単位",
                key=key_unit_temp,
                on_change=store_content,
                args=(key_unit_persist, key_unit_temp)
            )
            ss["user_input"][f"規定値{i+1}_単位"] = individual_value_unit

            individual_value_description = st.text_area(
                f"規定値 {i+1} の説明",
                key=key_description_temp,
                on_change=store_content,
                args=(key_description_persist, key_description_temp)
            )
            ss["user_input"][f"規定値{i+1}_説明"] =individual_value_description

        # **推測値テンプレートの選択**
        # 自由入力で固定
        prediction_template = st.selectbox(
            "推測値のテンプレはどれを使用しますか？", 
            ["1(容量推測)", "2(台数推測)", "3(自由入力)"], 
            index=2, 
            disabled=True
        )
        ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
        ss["user_input"]["推測値のテンプレ"] = prediction_template
        col1, col2 = st.columns(2)
        with col1:
            if st.button("入力を確定", key="submit"):
                prediction_template = ss["user_input"].get("推測値のテンプレ", "")
                ss["previous_page"] = ss["page"]
                if prediction_template.startswith("1"):
                    next_page("page3A")
                elif prediction_template.startswith("2"):
                    next_page("page3B")
                else:
                    next_page("page3C")
        with col2:
            if st.button("エラーチェック", key="check"):
                # チェックする計算式の辞書
                target_formula_dict = {
                    "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                    "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                    "投資額計算式": ss["user_input"]["投資額計算式"],
                    "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
                }
                # チェックする因数
                target_factors = [
                    ss["user_input"]["取得済みインプットの名前"],
                    ss["user_input"]["追加インプット1の名前"],
                    ss["user_input"]["追加インプット2の名前"],
                    ss["user_input"]["追加インプット3の名前"],
                    ss["user_input"]["追加インプット4の名前"],
                    ss["user_input"]["規定値(電気の排出係数)の名前"],
                    ss["user_input"]["規定値(電気料金)の名前"],
                    ss["user_input"]["規定値(想定稼働年数)の名前"],
                    ss["user_input"]["規定値1_名前"],
                    ss["user_input"]["規定値2_名前"],
                    ss["user_input"]["規定値3_名前"],
                    ss["user_input"]["規定値4_名前"],
                    ss["user_input"]["規定値5_名前"],
                    ss["user_input"]["規定値6_名前"],
                    ss["user_input"]["規定値7_名前"],
                    ss["user_input"]["規定値8_名前"],
                    ss["user_input"]["規定値9_名前"],
                    ss["user_input"]["規定値10_名前"],
                    ss["user_input"]["規定値11_名前"],
                    ss["user_input"]["規定値12_名前"],
                    ss["user_input"]["規定値13_名前"]
                ]

                for formula_name, formula in target_formula_dict.items():
                    parsed_list = split_formula(formula)

                    # 存在しなかった要素を保持するためのリスト
                    not_found_items = []

                    # リスト内の要素を1つずつ確認
                    for item in parsed_list:
                        found_in_any = False
                        # target_factorsに含まれる各因数についてチェック
                        for factor in target_factors:
                            if item == factor:
                                found_in_any = True
                                break
                        if not found_in_any:
                            not_found_items.append(item)
                    if not_found_items:
                        st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                        for i in not_found_items:
                            st.markdown(f"- {i}")
                    else:
                        st.success(f"✅ {formula_name}の因数に問題はありません")
    
        if st.button("戻る"):
            next_page("page1")


# ** 2ページ目F (緑施策) **
elif ss["page"] == "page2F":
    st.title("緑施策式入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
    "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
    "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }


    # **GHG削減量計算式**
    ss["user_input"].setdefault("GHG削減量計算式", "")

    if 'default_GHG削減量（ton-CO2）_persist' not in ss:
        ss['default_GHG削減量（ton-CO2）_persist'] = ''
    if 'default_GHG削減量（ton-CO2）_temp' not in ss:
        ss['default_GHG削減量（ton-CO2）_temp'] = ss['default_GHG削減量（ton-CO2）_persist']

    ghg_reduction_formula = st.text_area(
        "GHG削減量計算式",
        key='default_GHG削減量（ton-CO2）_temp',
        on_change= store_content,
        args=('default_GHG削減量（ton-CO2）_persist', 'default_GHG削減量（ton-CO2）_temp')
    )
    ss["user_input"]["GHG削減量計算式"] = ghg_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["GHG削減量計算式"]):
            st.success('GHG削減量計算式の<>はきちんと閉じられています')
        else:
            st.error('GHG削減量計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if '\n' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["GHG削減量計算式"] != '':
        if ' ' in ss["user_input"]["GHG削減量計算式"] or '\t' in ss["user_input"]["GHG削減量計算式"] or '　' in ss["user_input"]["GHG削減量計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **コスト削減額計算式**
    fuel = ss["user_input"].get("燃料", "")

    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"

    ss["user_input"].setdefault("コスト削減額計算式", "")

    if 'default_コスト削減額（円/年）_persist' not in ss:
        ss['default_コスト削減額（円/年）_persist'] = ''
    if 'default_コスト削減額（円/年）_temp' not in ss:
        ss['default_コスト削減額（円/年）_temp'] = ss['default_コスト削減額（円/年）_persist']
    
    cost_reduction_formula = st.text_area(
        "コスト削減額計算式",
        key='default_コスト削減額（円/年）_temp',
        on_change=store_content,
        args=('default_コスト削減額（円/年）_persist', 'default_コスト削減額（円/年）_temp')
    )
    ss["user_input"]["コスト削減額計算式"] = cost_reduction_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["コスト削減額計算式"]):
            st.success('コスト削減額計算式の<>はきちんと閉じられています')
        else:
            st.error('コスト削減額計算式の<>がきちんと閉じられていません')
    
    # 改行が含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if '\n' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["コスト削減額計算式"] != '':
        if ' ' in ss["user_input"]["コスト削減額計算式"] or '\t' in ss["user_input"]["コスト削減額計算式"] or '　' in ss["user_input"]["コスト削減額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **投資額計算式**
    ss["user_input"].setdefault("投資額計算式", "")

    if 'default_投資額（円）_persist' not in ss:
        ss['default_投資額（円）_persist'] = ''
    if 'default_投資額（円）_temp' not in ss:
        ss['default_投資額（円）_temp'] = ss['default_投資額（円）_persist']

    investment_amount_formula = st.text_area(
        "投資額計算式",
        key='default_投資額（円）_temp',
        on_change=store_content,
        args=('default_投資額（円）_persist', 'default_投資額（円）_temp')
    )
    ss["user_input"]["投資額計算式"] = investment_amount_formula

    # <>がきちんと閉じられているかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["投資額計算式"]):
            st.success('投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if '\n' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["投資額計算式"] != '':
        if ' ' in ss["user_input"]["投資額計算式"] or '\t' in ss["user_input"]["投資額計算式"] or '　' in ss["user_input"]["投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    # **追加投資額計算式**
    ss["user_input"].setdefault("追加投資額計算式", "")

    if 'default_追加投資額（円）_persist' not in ss:
        ss['default_追加投資額（円）_persist'] = ''
    if 'default_追加投資額（円）_temp' not in ss:
        ss['default_追加投資額（円）_temp'] = ss['default_追加投資額（円）_persist']

    additional_investment_amount_formula = st.text_area(
        "追加投資額計算式",
        key='default_追加投資額（円）_temp',
        on_change=store_content,
        args=('default_追加投資額（円）_persist', 'default_追加投資額（円）_temp')
    )
    ss["user_input"]["追加投資額計算式"] = additional_investment_amount_formula

    # <がきちんと閉じられているかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if has_unclosed_tag(ss["user_input"]["追加投資額計算式"]):
            st.success('追加投資額計算式の<>はきちんと閉じられています')
        else:
            st.error('追加投資額計算式の<>がきちんと閉じられていません')
    # 改行が含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if '\n' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中に改行が含まれています')
    
    # 半角スペース・全角スペース・タブが含まれていないかチェック
    if ss["user_input"]["追加投資額計算式"] != '':
        if ' ' in ss["user_input"]["追加投資額計算式"] or '\t' in ss["user_input"]["追加投資額計算式"] or '　' in ss["user_input"]["追加投資額計算式"]:
            st.error('計算式中にスペースが含まれています')

    st.subheader("取得済みインプット")
    default_input_name = ""
    ss["user_input"].setdefault("取得済みインプットの名前", default_input_name)
    if 'default_acquired_input_1_persist' not in ss:
        ss['default_acquired_input_1_persist'] = default_input_name
    if 'default_acquired_input_1_temp' not in ss:
        ss['default_acquired_input_1_temp'] = ss['default_acquired_input_1_persist']
    
    acquired_input_1_name = st.text_input(
        "インプットの名前",
        key='default_acquired_input_1_temp',
        on_change=store_content,
        args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
    )
    ss["user_input"]["取得済みインプットの名前"] = acquired_input_1_name

    ss["user_input"].setdefault("取得済みインプットの数字", 0.0)
    if 'default_acquired_input_1_value_persist' not in ss:
        ss['default_acquired_input_1_value_persist'] = 0.0
    if 'default_acquired_input_1_value_temp' not in ss:
        ss['default_acquired_input_1_value_temp'] = ss['default_acquired_input_1_value_persist']

    acquired_input_1_value = st.number_input(
        "数字",
        min_value=0.0,
        step=1.0,
        key='default_acquired_input_1_value_temp',
        on_change=store_content,
        args=('default_acquired_input_1_value_persist', 'default_acquired_input_1_value_temp')
    )
    ss["user_input"]["取得済みインプットの数字"] = acquired_input_1_value

    ss["user_input"].setdefault("取得済みインプットの単位", "")
    if 'default_acquired_input_1_unit_persist' not in ss:
        ss['default_acquired_input_1_unit_persist'] = ''
    if 'default_acquired_input_1_unit_temp' not in ss:
        ss['default_acquired_input_1_unit_temp'] = ss['default_acquired_input_1_unit_persist']

    acquired_input_1_unit = st.text_input(
        "単位",
        key='default_acquired_input_1_temp',
        on_change=store_content,
        args=('default_acquired_input_1_persist', 'default_acquired_input_1_temp')
    )
    ss["user_input"]["取得済みインプットの単位"] = acquired_input_1_unit

    # **追加インプット 6個**
    for i in range(6):
        st.subheader(f"追加インプット {i+1}")

        name_key = f"追加インプット{i+1}の名前"
        num_key = f"追加インプット{i+1}の数字"
        unit_key = f"追加インプット{i+1}の単位"

        if f'default_additional_input_{i+1}_persist' not in ss:
            ss[f'default_additional_input_{i+1}_persist'] = ''
        if f'default_additional_input_{i+1}_temp' not in ss:
            ss[f'default_additional_input_{i+1}_temp'] = ss[f'default_additional_input_{i+1}_persist']

        if f'default_additional_input_{i+1}_value_persist' not in ss:
            ss[f'default_additional_input_{i+1}_value_persist'] = 0.0
        if f'default_additional_input_{i+1}_value_temp' not in ss:
            ss[f'default_additional_input_{i+1}_value_temp'] = ss[f'default_additional_input_{i+1}_value_persist']

        if f'default_additional_input_{i+1}_unit_persist' not in ss:
            ss[f'default_additional_input_{i+1}_unit_persist'] = ''
        if f'default_additional_input_{i+1}_unit_temp' not in ss:
            ss[f'default_additional_input_{i+1}_unit_temp'] = ss[f'default_additional_input_{i+1}_unit_persist']
        
        key_name_temp = f'default_additional_input_{i+1}_temp'
        key_name_persist = f'default_additional_input_{i+1}_persist'
        key_value_temp = f'default_additional_input_{i+1}_value_temp'
        key_value_persist = f'default_additional_input_{i+1}_value_persist'
        key_unit_temp = f'default_additional_input_{i+1}_unit_temp'
        key_unit_persist = f'default_additional_input_{i+1}_unit_persist'

        additional_input_name = st.text_input(
            name_key,
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][name_key] = additional_input_name

        additional_input_val = st.number_input(
            num_key,
            min_value=0.0,
            step=1.0,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][num_key] = additional_input_val

        additional_input_unit = st.text_input(
            unit_key,
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][unit_key] = additional_input_unit

    # 燃料取得
    fuel = ss["user_input"].get("燃料", "")

    # **事前定義された値**
    if fuel == '電力':
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = '電気の排出係数' 
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = 0.000434
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = 't-CO2/kWh'
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf"
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = '電気料金'
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = 22.97
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = '円/kWh'
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit"
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    else:
        if 'default_individual_value(electric_emission_factor)_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_temp'] = ss['default_individual_value(electric_emission_factor)_persist']
        if 'default_individual_value(electric_emission_factor)_value_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_persist'] = np.nan
        if 'default_individual_value(electric_emission_factor)_value_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_value_temp'] = ss['default_individual_value(electric_emission_factor)_value_persist']
        if 'default_individual_value(electric_emission_factor)_unit_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_unit_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_unit_temp'] = ss['default_individual_value(electric_emission_factor)_unit_persist']
        if 'default_individual_value(electric_emission_factor)_description_persist' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_persist'] = ''
        if 'default_individual_value(electric_emission_factor)_description_temp' not in ss:
            ss['default_individual_value(electric_emission_factor)_description_temp'] = ss['default_individual_value(electric_emission_factor)_description_persist']
    
        if 'default_individual_value(electric_bill)_persist' not in ss:
            ss['default_individual_value(electric_bill)_persist'] = ''
        if 'default_individual_value(electric_bill)_temp' not in ss:
            ss['default_individual_value(electric_bill)_temp'] = ss['default_individual_value(electric_bill)_persist']
        if 'default_individual_value(electric_bill)_value_persist' not in ss:
            ss['default_individual_value(electric_bill)_value_persist'] = np.nan
        if 'default_individual_value(electric_bill)_value_temp' not in ss:
            ss['default_individual_value(electric_bill)_value_temp'] = ss['default_individual_value(electric_bill)_value_persist']
        if 'default_individual_value(electric_bill)_unit_persist' not in ss:
            ss['default_individual_value(electric_bill)_unit_persist'] = ''
        if 'default_individual_value(electric_bill)_unit_temp' not in ss:
            ss['default_individual_value(electric_bill)_unit_temp'] = ss['default_individual_value(electric_bill)_unit_persist']
        if 'default_individual_value(electric_bill)__description_persist' not in ss:
            ss['default_individual_value(electric_bill)__description_persist'] = ''
        if 'default_individual_value(electric_bill)__description_temp' not in ss:
            ss['default_individual_value(electric_bill)__description_temp'] = ss['default_individual_value(electric_bill)__description_persist']
    
        if 'default_individual_value(estimated_lifetime)_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_persist'] = '想定稼働年数'
        if 'default_individual_value(estimated_lifetime)_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_temp'] = ss['default_individual_value(estimated_lifetime)_persist']
        if 'default_individual_value(estimated_lifetime)_value_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_persist'] = 10
        if 'default_individual_value(estimated_lifetime)_value_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_value_temp'] = ss['default_individual_value(estimated_lifetime)_value_persist']
        if 'default_individual_value(estimated_lifetime)_unit_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_persist'] = '年'
        if 'default_individual_value(estimated_lifetime)_unit_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_unit_temp'] = ss['default_individual_value(estimated_lifetime)_unit_persist']
        if 'default_individual_value(estimated_lifetime)_description_persist' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_persist'] = ''
        if 'default_individual_value(estimated_lifetime)_description_temp' not in ss:
            ss['default_individual_value(estimated_lifetime)_description_temp'] = ss['default_individual_value(estimated_lifetime)_description_persist']

    predefined_values = [
        ("電気の排出係数", 0.000434 if fuel == "電力" else 0.0, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf" if fuel == "電力" else ""),
        ("電気料金", 22.97 if fuel == "電力" else 0.0, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit" if fuel == "電力" else ""),
        ("想定稼働年数", 10, "年", "")
    ]

    for name, value, unit, description in predefined_values:
        st.subheader(f"規定値: {name}")
        
        name_display = name if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else "燃料が電力ではありません"
        value_display = value if fuel == "電力" or name not in ["電気の排出係数", "電気料金"] else 0.0

        if name == '電気の排出係数':
            key_name_temp = 'default_individual_value(electric_emission_factor)_temp'
            key_name_persist = 'default_individual_value(electric_emission_factor)_persist'
            key_value_temp = 'default_individual_value(electric_emission_factor)_value_temp'
            key_value_persist = 'default_individual_value(electric_emission_factor)_value_persist'
            key_unit_temp = 'default_individual_value(electric_emission_factor)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_emission_factor)_unit_persist'
            key_description_temp = 'default_individual_value(electric_emission_factor)_description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_emission_factor)_description_persist' if fuel == '電力' else ''
        elif name == '電気料金':
            key_name_temp = 'default_individual_value(electric_bill)_temp'
            key_name_persist = 'default_individual_value(electric_bill)_persist'
            key_value_temp = 'default_individual_value(electric_bill)_value_temp'
            key_value_persist = 'default_individual_value(electric_bill)_value_persist'
            key_unit_temp = 'default_individual_value(electric_bill)_unit_temp'
            key_unit_persist = 'default_individual_value(electric_bill)_unit_persist'
            key_description_temp = 'default_individual_value(electric_bill)__description_temp' if fuel == '電力' else ''
            key_description_persist = 'default_individual_value(electric_bill)__description_persist' if fuel == '電力' else ''
        elif name == "想定稼働年数":
            key_name_temp = 'default_individual_value(estimated_lifetime)_temp'
            key_name_persist = 'default_individual_value(estimated_lifetime)_persist'
            key_value_temp = 'default_individual_value(estimated_lifetime)_value_temp'
            key_value_persist = 'default_individual_value(estimated_lifetime)_value_persist'
            key_unit_temp = 'default_individual_value(estimated_lifetime)_unit_temp'
            key_unit_persist = 'default_individual_value(estimated_lifetime)_unit_persist'
            key_description_temp = 'default_individual_value(estimated_lifetime)_description_temp'
            key_description_persist = 'default_individual_value(estimated_lifetime)_description_persist'

        # `規定値({name})の名前` の入力
        ss["user_input"].setdefault(f"規定値({name})の名前", "")
        ind_val_name = st.text_input(
            f"規定値({name})の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値({name})の名前"] = ind_val_name

        # セッションステートから値を取得し、型をチェック
        current_value = ss[key_value_temp]
        # None の場合は 0.0 を設定
        if current_value is None:
            current_value = 0.0
        # 文字列の場合は float に変換（空文字 `""` の場合は 0.0 にする）
        elif isinstance(current_value, str):
            try:
                current_value = float(current_value) if current_value.strip() else 0.0
            except ValueError:
                current_value = 0.0  # 数値に変換できなければ 0.0 にする
        
        # `value`, `min_value`, `step` を float に統一
        ind_val_val = st.number_input(
            f"規定値({name})の数字",
            min_value=0.0,
            step=0.000001 if name == "電気の排出係数" else 0.01,  # float に統一
            format="%.6f" if name == "電気の排出係数" else "%.2f",
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値({name})の数字"] = ind_val_val

        # `規定値({name})の単位` の入力
        ss["user_input"].setdefault(f"規定値({name})の単位", "")

        ind_val_unit = st.text_input(
            f"規定値({name})の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値({name})の単位"] = ind_val_unit

        # `規定値({name})の説明` の入力
        ss["user_input"].setdefault(f"規定値({name})の説明", "")
        ind_val_description = st.text_area(
            f"規定値({name})の説明", 
            key=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値({name})の説明"] = ind_val_description
        
    # **追加の規定値 13個**
    for i in range(13):
        st.subheader(f"規定値 {i+1}")
        fuel = ss["user_input"].get("燃料", "")
        value_format = "%.2f"
        name, value, unit, description = "", 0.0 , "", ""

        if f'default_individual_value_{i+1}_persist' not in ss:
            ss[f'default_individual_value_{i+1}_persist'] = name
        if f'default_individual_value_{i+1}_temp' not in ss:
            ss[f'default_individual_value_{i+1}_temp'] = ss[f'default_individual_value_{i+1}_persist']
        if f'default_individual_value_{i+1}_value_persist' not in ss:
            ss[f'default_individual_value_{i+1}_value_persist'] = value
        if f'default_individual_value_{i+1}_value_temp' not in ss:
            ss[f'default_individual_value_{i+1}_value_temp'] = ss[f'default_individual_value_{i+1}_value_persist']
        if f'default_individual_value_{i+1}_unit_persist' not in ss:
            ss[f'default_individual_value_{i+1}_unit_persist'] = unit
        if f'default_individual_value_{i+1}_unit_temp' not in ss:
            ss[f'default_individual_value_{i+1}_unit_temp'] = ss[f'default_individual_value_{i+1}_unit_persist']
        if f'default_individual_value_{i+1}_description_persist' not in ss:
            ss[f'default_individual_value_{i+1}_description_persist'] = description
        if f'default_individual_value_{i+1}_description_temp' not in ss:
            ss[f'default_individual_value_{i+1}_description_temp'] = ss[f'default_individual_value_{i+1}_description_persist']
        
        ss["user_input"].setdefault(f"規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"規定値{i+1}_説明", description)
        
        key_name_temp = f'default_individual_value_{i+1}_temp'
        key_name_persist = f'default_individual_value_{i+1}_persist'
        key_value_temp = f'default_individual_value_{i+1}_value_temp'
        key_value_persist = f'default_individual_value_{i+1}_value_persist'
        key_unit_temp = f'default_individual_value_{i+1}_unit_temp'
        key_unit_persist = f'default_individual_value_{i+1}_unit_persist'
        key_description_temp = f'default_individual_value_{i+1}_description_temp'
        key_description_persist = f'default_individual_value_{i+1}_description_persist'

        ind_val_name = st.text_input(
            f"規定値 {i+1} の名前", 
            key=key_name_temp,
            on_change=store_content,
            args=(key_name_persist, key_name_temp)
        )
        ss["user_input"][f"規定値{i+1}_名前"] = ind_val_name

        ind_val_val = st.number_input(
            f"規定値 {i+1} の数字",
            min_value=0.0,
            step=0.000001 if i == 1 else 0.01,
            key=key_value_temp,
            on_change=store_content,
            args=(key_value_persist, key_value_temp)
        )
        ss["user_input"][f"規定値{i+1}_数字"] = ind_val_val

        ind_val_unit = st.text_input(
            f"規定値 {i+1} の単位", 
            key=key_unit_temp,
            on_change=store_content,
            args=(key_unit_persist, key_unit_temp)
        )
        ss["user_input"][f"規定値{i+1}_単位"] = ind_val_unit

        ind_val_unit = st.text_area(
            f"規定値 {i+1} の説明", 
            vkey=key_description_temp,
            on_change=store_content,
            args=(key_description_persist, key_description_temp)
        )
        ss["user_input"][f"規定値{i+1}_説明"] = ind_val_unit
        
    # **推測値テンプレートの選択**
    if 'default_prediction_template_persist' not in ss:
        ss['default_prediction_template_persist'] = None
    if 'default_prediction_template_temp' not in ss:
        ss['default_prediction_template_temp'] = ss['default_prediction_template_persist']
    
    prediction_template = st.selectbox(
        "推測値のテンプレはどれを使用しますか？", 
        ["1(容量推測)", "2(台数推測)", "3(自由入力)"],
        key='default_prediction_template_temp',
        on_change=store_content,
        args=('default_prediction_template_persist', 'default_prediction_template_temp')
    )

    ss["user_input"].setdefault("推測値のテンプレ", prediction_template)
    ss["user_input"]["推測値のテンプレ"] = prediction_template

    col1, col2 = st.columns(2)
    with col1:
        if st.button("入力を確定", key="submit"):
            prediction_template = ss["user_input"].get("推測値のテンプレ", "")
            ss["previous_page"] = ss["page"]
            if prediction_template.startswith("1"):
                next_page("page3A")
            elif prediction_template.startswith("2"):
                next_page("page3B")
            else:
                next_page("page3C")
    with col2:
        if st.button("エラーチェック", key="check"):
            # チェックする計算式の辞書
            target_formula_dict = {
                "GHG削減量計算式": ss["user_input"]["GHG削減量計算式"],
                "コスト削減額計算式": ss["user_input"]["コスト削減額計算式"], 
                "投資額計算式": ss["user_input"]["投資額計算式"],
                "追加投資額計算式": ss["user_input"]["追加投資額計算式"]
            }
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")
    
    if st.button("戻る"):
        next_page("page1")


elif ss["page"] == "page3A":

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
    "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
    "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }

    # 負荷率データ
    load_factor_table = {
        "空調(電気)(パッケージ式)": 40, "空調(電気)(個別式)": 40, "冷蔵/冷凍": 45, "給湯": 75,
        "照明": 60, "OA機器(パソコン、コピー機等)": 60, "サーバー機器": 40, "エレベータ": 50,
        "コンプレッサー": 50, "ポンプ": 80, "送風機/給気・排気ファン": 50, "電気自動車": 60,
        "織機": 90, "ベルトコンベア": 50, "溶解炉": 50, "ヒーター": 70,
        "空調(電気)(冷凍機)": 40, "空調(電気)(ウォータチラー空冷式)": 40,
        "空調(電気)(ウォータチラー水冷式)": 40, "攪拌機": 60, "充填機": 40,
        "包装機": 50, "クリーンルーム用空調(電気)(パッケージ式)": 40,
        "クリーンルーム用空調(電気)(冷凍機)": 40, "クリーンルーム用空調(電気)(ウォータチラー空冷式)": 40,
        "クリーンルーム用空調(電気)(ウォータチラー水冷式)": 40, "曝気・水処理用ブロワ": 80,
        "その他用途のブロワ": 80
    }

    st.title("推測値(設備容量)入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    if 'default_value_to_estimate_persist' not in ss:
        ss['default_value_to_estimate_persist'] = ''
    if 'default_value_to_estimate_temp' not in ss:
        ss['default_value_to_estimate_temp'] = ss['default_value_to_estimate_persist']
    
    if 'default_round_flag_persist' not in ss:
        ss['default_round_flag_persist'] = ''
    if 'default_round_flag_temp' not in ss:
        ss['default_round_flag_temp'] = ss['default_round_flag_persist']
    
    select = st.selectbox(
        "推測値はどの因数ですか？", 
        ["", "additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"],
        key='default_value_to_estimate_temp',
        on_change=store_content,
        args=('default_value_to_estimate_persist', 'default_value_to_estimate_temp')
    )
    ss["user_input"]["推測対象"] = select
    
    under = st.selectbox(
        "小数点以下何桁まで推測しますか？", 
        ["", "0", "1"],
        key='default_round_flag_temp',
        on_change=store_content,
        args=('default_round_flag_persist', 'default_round_flag_temp')
    )
    ss["user_input"]["小数点以下の桁数"] = under
    
    # **推測式**
    fuel = ss["user_input"].get("燃料", "")
    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        fuel_heat_str = "都市ガス{13A}の熱量<MJ/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        heat_name, _, heat_unit, _ = fuel_heat.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"
        fuel_heat_str = f"{heat_name}<{heat_unit}>"
    
    if fuel == "電力":
        default_suppose_formula = f"推測値={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
    else:
        default_suppose_formula = f"推測値={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}×{fuel_heat_str}÷3.6÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
    
    if 'default_estimate_formula_persist' not in ss:
        ss['default_estimate_formula_persist'] =default_suppose_formula
    if 'default_estimate_formula_temp' not in ss:
        ss['default_estimate_formula_temp'] = ss['default_estimate_formula_persist']
    
    ss["user_input"].setdefault("推測式", default_suppose_formula)
    estimation_formula = st.text_area(
        "推測式", 
        key='default_estimate_formula_temp',
        on_change=store_content,
        args=('default_estimate_formula_persist', 'default_estimate_formula_temp')
    )
    ss["user_input"]["推測式"] = estimation_formula

    # **推測式用の規定値 4個**
    for i in range(4):
        st.subheader(f"推測規定値 {i+1}")

        value_format = "%.2f"
        description = ""

        if i == 0:
            name, unit, value = "稼働時間", "時間/日", 8.0
        elif i == 1:
            name, unit, value = "稼働日数", "日/年", 200.0
        elif i == 2:
            name, unit = "負荷率", "%"
            equipment = ss["user_input"].get("設備", "")
            value = float(load_factor_table.get(equipment, 0.0)) # デフォルト値を0.0に設定
        else:
            name, unit, value = "", "", 0.0  # 初期値を1.0に設定

        if f'default_estimation_value_{i+1}_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_persist'] = name
        if f'default_estimation_value_{i+1}_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_temp'] = ss[f'default_estimation_value_{i+1}_persist']
        if f'default_estimation_value_{i+1}_value_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_value_persist'] = value
        if f'default_estimation_value_{i+1}_value_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_value_temp'] = ss[f'default_estimation_value_{i+1}_value_persist']
        if f'default_estimation_value_{i+1}_unit_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_unit_persist'] = unit
        if f'default_estimation_value_{i+1}_unit_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_unit_temp'] = ss[f'default_estimation_value_{i+1}_unit_persist']
        if f'default_estimation_value_{i+1}_description_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_description_persist'] = description
        if f'default_estimation_value_{i+1}_description_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_description_temp'] = ss[f'default_estimation_value_{i+1}_description_persist']
        
        ss["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
        
        estimation_value_name = st.text_input(
            f"推測規定値{i+1}_名前",
            key=f'default_estimation_value_{i+1}_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_persist', f'default_estimation_value_{i+1}_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_名前"] = estimation_value_name

        estimation_value_value = st.number_input(
            f"推測規定値{i+1}_数字",
            min_value=0.0,
            step=0.01,
            format=value_format,
            key=f'default_estimation_value_{i+1}_value_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_value_persist', f'default_estimation_value_{i+1}_value_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_数字"] = estimation_value_value
        
        estimation_value_unit = st.text_input(
            f"推測規定値{i+1}_単位",
            key=f'default_estimation_value_{i+1}_unit_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_unit_persist', f'default_estimation_value_{i+1}_unit_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_単位"] = estimation_value_unit
        
        estimation_value_description = st.text_area(
            f"推測規定値{i+1}_説明",
            key=f'default_estimation_value_{i+1}_description_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_description_persist', f'default_estimation_value_{i+1}_description_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_説明"] = estimation_value_description

    col1, col2 = st.columns(2)
    with col1:
        if st.button("推測値(容量)を確定", key="submitted_3A"):
            ss['previous_page_of_description'] = ss['page'] 
            next_page("description")
    with col2:
        if st.button("エラーチェック", "error_check_3A"):
            # チェックする計算式の辞書
            target_formula_dict = {"推測式": ss["user_input"]["推測式"]}
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"],
                ss["user_input"]["推測規定値1_名前"],
                ss["user_input"]["推測規定値2_名前"],
                ss["user_input"]["推測規定値3_名前"],
                ss["user_input"]["推測規定値4_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")
                    
    if "previous_page" in ss:
        if st.button("戻る"):
            next_page(ss["previous_page"])


elif ss["page"] == "page3B":
    st.title("台数推測入力")

    # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガス{13A}の排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "LPG": ("LPGの排出係数", 0.0066, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "灯油": ("灯油の排出係数", 0.00249, "t-CO2/l", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
        "A重油": ("A重油の排出係数", 0.00271, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "B・C重油": ("B・C重油の排出係数", 0.003, "t-CO2/l", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "LNG": ("LNGの排出係数", 2.7, "t-CO2/t", "https://shift.env.go.jp/files/offering/2023/sf05f2.pdf"),
        "温水": ("温水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "冷水": ("冷水の排出係数", 0.0532, "t-CO2/GJ", "https://ghg-santeikohyo.env.go.jp/files/calc/r06_heat_coefficient_rev3.pdf"),
        "石炭": ("石炭の排出係数", 2.33, "t-CO2/t", "https://ghg-santeikohyo.env.go.jp/files/manual/chpt2_4-9_rev.pdf"),
        "軽油": ("軽油の排出係数", 0.00258, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
        "揮発油": ("揮発油の排出係数", 0.00232, "t-CO2/l", "https://www.env.go.jp/content/900443021.pdf"),
    }

    # 燃料ごとの価格データ
    fuel_prices = {
        "都市ガス": ("都市ガス{13A}料金", 78, "円/㎥", "https://www.env.go.jp/content/000123580.pdf"),
        "LPG": ("LPG価格", 314, "円/㎥", "https://www.j-lpgas.gr.jp/stat/kakaku/index.html"),
        "灯油": ("灯油価格", 115.8, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "A重油": ("A重油の価格", 95.5, "円/l", "https://pps-net.org/industrial"),
        "B・C重油": ("B・C重油の価格", 87.51, "円/l", "https://pps-net.org/industrial"),
        "LNG": ("LNG価格", 135434, "円/t", "https://oilgas-info.jogmec.go.jp/nglng/1007905/1009580.html"),
        "温水": ("温水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "冷水": ("冷水の価格", 5000, "円/GJ", "https://www.tokyo-rinnetu.co.jp/discounted/"),
        "石炭": ("石炭の価格", 19370, "円/t", "https://pps-net.org/statistics/coal2"),
        "軽油": ("軽油価格", 154.6, "円/l", "https://www.pref.miyazaki.lg.jp/seikatsu-kyodo-danjo/bosai/shohi/index.html"),
        "揮発油": ("揮発油価格", 183.5, "円/l", "https://pps-net.org/oilstand"),
    }

    fuel_heat = {
    "都市ガス": ("都市ガス{13A}の熱量", 44.8, "MJ/㎥", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LPG": ("LPGの熱量", 100.5, "MJ/㎥", "https://www.kanagawalpg.or.jp/lpg/01.html#:~:text=%EF%BC%AC%EF%BC%B0%E3%82%AC%E3%82%B9%E3%81%AE%E7%86%B1%E9%87%8F%E9%87%8F,%E5%8A%B9%E7%8E%87%E3%82%92%E3%81%8D%E3%81%A1%E3%82%93%E3%81%A8%E7%90%86%E8%A7%A3%E3%81%99%E3%82%8B%E3%80%82"),
    "灯油": ("灯油の熱量", 36.7, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "A重油": ("A重油の熱量", 39.1, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "B・C重油": ("B・C重油の熱量", 41.9, "MJ/l", "https://www.env.go.jp/policy/local_keikaku/data/guideline.pdf"),
    "LNG": ("LNGの熱量", 54500, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "石炭": ("石炭の熱量", 30100, "MJ/t", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "軽油": ("軽油の熱量", 38.2, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf"),
    "揮発油": ("揮発油の熱量", 34.6, "MJ/l", "https://www.ecofukuoka.jp/image/custom/data/santei/hatunetu.pdf")
    }

    # 負荷率データ
    load_factor_table = {
        "空調(電気)(パッケージ式)": 40, "空調(電気)(個別式)": 40, "冷蔵/冷凍": 45, "給湯": 75,
        "照明": 60, "OA機器(パソコン、コピー機等)": 60, "サーバー機器": 40, "エレベータ": 50,
        "コンプレッサー": 50, "ポンプ": 80, "送風機/給気・排気ファン": 50, "電気自動車": 60,
        "織機": 90, "ベルトコンベア": 50, "溶解炉": 50, "ヒーター": 70,
        "空調(電気)(冷凍機)": 40, "空調(電気)(ウォータチラー空冷式)": 40,
        "空調(電気)(ウォータチラー水冷式)": 40, "攪拌機": 60, "充填機": 40,
        "包装機": 50, "クリーンルーム用空調(電気)(パッケージ式)": 40,
        "クリーンルーム用空調(電気)(冷凍機)": 40, "クリーンルーム用空調(電気)(ウォータチラー空冷式)": 40,
        "クリーンルーム用空調(電気)(ウォータチラー水冷式)": 40, "曝気・水処理用ブロワ": 80,
        "その他用途のブロワ": 80
    }


    st.title("推測値(設備台数)入力")
    st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

    if 'default_value_to_estimate_persist' not in ss:
        ss['default_value_to_estimate_persist'] = ''
    if 'default_value_to_estimate_temp' not in ss:
        ss['default_value_to_estimate_temp'] = ss['default_value_to_estimate_persist']
    
    if 'default_round_flag_persist' not in ss:
        ss['default_round_flag_persist'] = ''
    if 'default_round_flag_temp' not in ss:
        ss['default_round_flag_temp'] = ss['default_round_flag_persist']
    
    select = st.selectbox(
        "推測値はどの因数ですか？", 
        ["", "additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"],
        key='default_value_to_estimate_temp',
        on_change=store_content,
        args=('default_value_to_estimate_persist', 'default_value_to_estimate_temp')
    )
    ss["user_input"]["推測対象"] = select
    
    under = st.selectbox(
        "小数点以下何桁まで推測しますか？", 
        ["", "0", "1"],
        key='default_round_flag_temp',
        on_change=store_content,
        args=('default_round_flag_persist', 'default_round_flag_temp')
    )
    ss["user_input"]["小数点以下の桁数"] = under
    
    # **推測式**
    fuel = ss["user_input"].get("燃料", "")

    if fuel == "電力":
        emission_factor_str = "電気の排出係数<t-CO2/kWh>"
        fuel_price_str = "電気料金<円/kWh>"
    elif fuel == "都市ガス":
        emission_factor_str = "都市ガス{13A}の排出係数<t-CO2/㎥>"
        fuel_price_str = "都市ガス{13A}料金<円/㎥>"
        fuel_heat_str = "都市ガス{13A}の熱量<MJ/㎥>"
    else:
        emission_name, _, emission_unit, _ = emission_factors.get(fuel, ("", 0, "", ""))
        price_name, _, price_unit, _ = fuel_prices.get(fuel, ("", 0, "", ""))
        heat_name, _, heat_unit, _ = fuel_heat.get(fuel, ("", 0, "", ""))
        emission_factor_str = f"{fuel}の排出係数<{emission_unit}>"
        fuel_price_str = f"{price_name}<{price_unit}>"
        fuel_heat_str = f"{heat_name}<{heat_unit}>"
    
    if fuel == "電力":
        default_suppose_formula = f"推測値={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
    else:
        default_suppose_formula = f"推測値={ss['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}×{fuel_heat_str}÷3.6÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
    
    if 'default_estimate_formula_persist' not in ss:
        ss['default_estimate_formula_persist'] =default_suppose_formula
    if 'default_estimate_formula_temp' not in ss:
        ss['default_estimate_formula_temp'] = ss['default_estimate_formula_persist']
    
    ss["user_input"].setdefault("推測式", default_suppose_formula)
    estimation_formula = st.text_area(
        "推測式", 
        key='default_estimate_formula_temp',
        on_change=store_content,
        args=('default_estimate_formula_persist', 'default_estimate_formula_temp')
    )
    ss["user_input"]["推測式"] = estimation_formula
    
    # **推測式用の規定値 4個**
    for i in range(4):
        st.subheader(f"推測規定値 {i+1}")

        value_format = "%.2f"
        description = ""

        if i == 0:
            name, unit, value = "稼働時間", "時間/日", 8.0
        elif i == 1:
            name, unit, value = "稼働日数", "日/年", 200.0
        elif i == 2:
            name, unit = "負荷率", "%"
            equipment = ss["user_input"].get("設備", "")
            value = float(load_factor_table.get(equipment, 0.0)) # デフォルト値を0.0に設定
        else:
            equipment = ss["user_input"].get("設備", "")
            name, unit, value = f"{equipment}平均容量", "kW", 0.0  # 初期値を1.0に設定
        
        if f'default_estimation_value_{i+1}_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_persist'] = name
        if f'default_estimation_value_{i+1}_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_temp'] = ss[f'default_estimation_value_{i+1}_persist']
        if f'default_estimation_value_{i+1}_value_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_value_persist'] = value
        if f'default_estimation_value_{i+1}_value_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_value_temp'] = ss[f'default_estimation_value_{i+1}_value_persist']
        if f'default_estimation_value_{i+1}_unit_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_unit_persist'] = unit
        if f'default_estimation_value_{i+1}_unit_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_unit_temp'] = ss[f'default_estimation_value_{i+1}_unit_persist']
        if f'default_estimation_value_{i+1}_description_persist' not in ss:
            ss[f'default_estimation_value_{i+1}_description_persist'] = description
        if f'default_estimation_value_{i+1}_description_temp' not in ss:
            ss[f'default_estimation_value_{i+1}_description_temp'] = ss[f'default_estimation_value_{i+1}_description_persist']
        
        ss["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
        ss["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
        ss["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
        ss["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
        
        estimation_value_name = st.text_input(
            f"推測規定値{i+1}_名前",
            key=f'default_estimation_value_{i+1}_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_persist', f'default_estimation_value_{i+1}_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_名前"] = estimation_value_name
        
        estimation_value_value = st.number_input(
            f"推測規定値{i+1}_数字",
            min_value=0.0,
            step=0.01,
            format=value_format,
            key=f'default_estimation_value_{i+1}_value_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_value_persist', f'default_estimation_value_{i+1}_value_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_数字"] = estimation_value_value
        
        estimation_value_unit = st.text_input(
            f"推測規定値{i+1}_単位",
            key=f'default_estimation_value_{i+1}_unit_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_unit_persist', f'default_estimation_value_{i+1}_unit_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_単位"] = estimation_value_unit
        
        estimation_value_description = st.text_area(
            f"推測規定値{i+1}_説明",
            key=f'default_estimation_value_{i+1}_description_temp',
            on_change=store_content,
            args=(f'default_estimation_value_{i+1}_description_persist', f'default_estimation_value_{i+1}_description_temp')
        )
        ss["user_input"][f"推測規定値{i+1}_説明"] = estimation_value_description
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("推測値(容量)を確定", key="submitted_3B"):
            ss['previous_page_of_description'] = ss['page'] 
            next_page("description")
    with col2:
        if st.button("エラーチェック", "error_check_3B"):
            # チェックする計算式の辞書
            target_formula_dict = {"推測式": ss["user_input"]["推測式"]}
            # チェックする因数
            target_factors = [
                ss["user_input"]["取得済みインプットの名前"],
                ss["user_input"]["追加インプット1の名前"],
                ss["user_input"]["追加インプット2の名前"],
                ss["user_input"]["追加インプット3の名前"],
                ss["user_input"]["追加インプット4の名前"],
                ss["user_input"]["規定値(電気の排出係数)の名前"],
                ss["user_input"]["規定値(電気料金)の名前"],
                ss["user_input"]["規定値(想定稼働年数)の名前"],
                ss["user_input"]["規定値1_名前"],
                ss["user_input"]["規定値2_名前"],
                ss["user_input"]["規定値3_名前"],
                ss["user_input"]["規定値4_名前"],
                ss["user_input"]["規定値5_名前"],
                ss["user_input"]["規定値6_名前"],
                ss["user_input"]["規定値7_名前"],
                ss["user_input"]["規定値8_名前"],
                ss["user_input"]["規定値9_名前"],
                ss["user_input"]["規定値10_名前"],
                ss["user_input"]["規定値11_名前"],
                ss["user_input"]["規定値12_名前"],
                ss["user_input"]["規定値13_名前"],
                ss["user_input"]["推測規定値1_名前"],
                ss["user_input"]["推測規定値2_名前"],
                ss["user_input"]["推測規定値3_名前"],
                ss["user_input"]["推測規定値4_名前"]
            ]
            for formula_name, formula in target_formula_dict.items():
                parsed_list = split_formula(formula)
                # 存在しなかった要素を保持するためのリスト
                not_found_items = []
                # リスト内の要素を1つずつ確認
                for item in parsed_list:
                    found_in_any = False
                    # target_factorsに含まれる各因数についてチェック
                    for factor in target_factors:
                        if item == factor:
                            found_in_any = True
                            break
                    if not found_in_any:
                        not_found_items.append(item)
                if not_found_items:
                    st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                    for i in not_found_items:
                        st.markdown(f"- {i}")
                else:
                    st.success(f"✅ {formula_name}の因数に問題はありません")

    if "previous_page" in ss:
        if st.button("戻る"):
            next_page(ss["previous_page"])

elif ss["page"] == "page3C":
    if ss['selected_option_persist'] == '使用しない':
        st.title("自由入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

        if 'default_value_to_estimate_persist' not in ss:
            ss['default_value_to_estimate_persist'] = ''
        if 'default_value_to_estimate_temp' not in ss:
            ss['default_value_to_estimate_temp'] = ss['default_value_to_estimate_persist']
        
        if 'default_round_flag_persist' not in ss:
            ss['default_round_flag_persist'] = ''
        if 'default_round_flag_temp' not in ss:
            ss['default_round_flag_temp'] = ss['default_round_flag_persist']

        select = st.selectbox(
            "推測値はどの因数ですか？", 
            ["", "additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"],
            key='default_value_to_estimate_temp',
            on_change=store_content,
            args=('default_value_to_estimate_persist', 'default_value_to_estimate_temp')
        )
        ss["user_input"]["推測対象"] = select
        
        under = st.selectbox(
            "小数点以下何桁まで推測しますか？", 
            ["", "0", "1"],
            key='default_round_flag_temp',
            on_change=store_content,
            args=('default_round_flag_persist', 'default_round_flag_temp')
        )
        ss["user_input"]["小数点以下の桁数"] = under
        
        fuel = ss["user_input"].get("燃料", "")
        
        emission_factors = {}
        fuel_prices = {}
        fuel_heat = {}
        load_factor_table = {}
        
        emission_factor_str = ""
        fuel_price_str = ""
        fuel_heat_str = ""
        
        default_suppose_formula = "推測値="
        
        if 'default_estimate_formula_persist' not in ss:
            ss['default_estimate_formula_persist'] =default_suppose_formula
        if 'default_estimate_formula_temp' not in ss:
            ss['default_estimate_formula_temp'] = ss['default_estimate_formula_persist']

        ss["user_input"].setdefault("推測式", default_suppose_formula)
        estimation_formula = st.text_area(
            "推測式",
            key='default_estimate_formula_temp',
            on_change=store_content,
            args=('default_estimate_formula_persist', 'default_estimate_formula_temp')
        )
        ss["user_input"]["推測式"] = estimation_formula
        
        for i in range(4):
            st.subheader(f"推測規定値 {i+1}")
            value_format = "%.2f"
            description = ""

            name, unit, value = "", "", 0.0  

            if f'default_estimation_value_{i+1}_persist' not in ss:
                ss[f'default_estimation_value_{i+1}_persist'] = name
            if f'default_estimation_value_{i+1}_temp' not in ss:
                ss[f'default_estimation_value_{i+1}_temp'] = ss[f'default_estimation_value_{i+1}_persist']
            if f'default_estimation_value_{i+1}_value_persist' not in ss:
                ss[f'default_estimation_value_{i+1}_value_persist'] = value
            if f'default_estimation_value_{i+1}_value_temp' not in ss:
                ss[f'default_estimation_value_{i+1}_value_temp'] = ss[f'default_estimation_value_{i+1}_value_persist']
            if f'default_estimation_value_{i+1}_unit_persist' not in ss:
                ss[f'default_estimation_value_{i+1}_unit_persist'] = unit
            if f'default_estimation_value_{i+1}_unit_temp' not in ss:
                ss[f'default_estimation_value_{i+1}_unit_temp'] = ss[f'default_estimation_value_{i+1}_unit_persist']
            if f'default_estimation_value_{i+1}_description_persist' not in ss:
                ss[f'default_estimation_value_{i+1}_description_persist'] = description
            if f'default_estimation_value_{i+1}_description_temp' not in ss:
                ss[f'default_estimation_value_{i+1}_description_temp'] = ss[f'default_estimation_value_{i+1}_description_persist']

            ss["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
            ss["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
            ss["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
            ss["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
            
            estimation_value_name = st.text_input(
                f"推測規定値{i+1}_名前",
                key=f'default_estimation_value_{i+1}_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_persist', f'default_estimation_value_{i+1}_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_名前"] = estimation_value_name
            
            estimation_value_value = st.number_input(
                f"推測規定値{i+1}_数字",
                min_value=0.0,
                step=0.01,
                format=value_format,
                key=f'default_estimation_value_{i+1}_value_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_value_persist', f'default_estimation_value_{i+1}_value_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_数字"] = estimation_value_value
            
            estimation_value_unit = st.text_input(
                f"推測規定値{i+1}_単位",
                key=f'default_estimation_value_{i+1}_unit_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_unit_persist', f'default_estimation_value_{i+1}_unit_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_単位"] = estimation_value_unit
            
            estimation_value_description = st.text_area(
                f"推測規定値{i+1}_説明",
                key=f'default_estimation_value_{i+1}_description_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_description_persist', f'default_estimation_value_{i+1}_description_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_説明"] = estimation_value_description

        col1, col2 = st.columns(2)
        with col1:
            if st.button("推測値(容量)を確定", key="submitted_3C"):
                ss['previous_page_of_description'] = ss['page'] 
                next_page("description")
        with col2:
            if st.button("エラーチェック", "error_check_3C"):
                # チェックする計算式の辞書
                target_formula_dict = {"推測式": ss["user_input"]["推測式"]}
                # チェックする因数
                target_factors = [
                    ss["user_input"]["取得済みインプットの名前"],
                    ss["user_input"]["追加インプット1の名前"],
                    ss["user_input"]["追加インプット2の名前"],
                    ss["user_input"]["追加インプット3の名前"],
                    ss["user_input"]["追加インプット4の名前"],
                    ss["user_input"]["規定値(電気の排出係数)の名前"],
                    ss["user_input"]["規定値(電気料金)の名前"],
                    ss["user_input"]["規定値(想定稼働年数)の名前"],
                    ss["user_input"]["規定値1_名前"],
                    ss["user_input"]["規定値2_名前"],
                    ss["user_input"]["規定値3_名前"],
                    ss["user_input"]["規定値4_名前"],
                    ss["user_input"]["規定値5_名前"],
                    ss["user_input"]["規定値6_名前"],
                    ss["user_input"]["規定値7_名前"],
                    ss["user_input"]["規定値8_名前"],
                    ss["user_input"]["規定値9_名前"],
                    ss["user_input"]["規定値10_名前"],
                    ss["user_input"]["規定値11_名前"],
                    ss["user_input"]["規定値12_名前"],
                    ss["user_input"]["規定値13_名前"],
                    ss["user_input"]["推測規定値1_名前"],
                    ss["user_input"]["推測規定値2_名前"],
                    ss["user_input"]["推測規定値3_名前"],
                    ss["user_input"]["推測規定値4_名前"]
                ]
                for formula_name, formula in target_formula_dict.items():
                    parsed_list = split_formula(formula)
                    # 存在しなかった要素を保持するためのリスト
                    not_found_items = []
                    # リスト内の要素を1つずつ確認
                    for item in parsed_list:
                        found_in_any = False
                        # target_factorsに含まれる各因数についてチェック
                        for factor in target_factors:
                            if item == factor:
                                found_in_any = True
                                break
                        if not found_in_any:
                            not_found_items.append(item)
                    if not_found_items:
                        st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                        for i in not_found_items:
                            st.markdown(f"- {i}")
                    else:
                        st.success(f"✅ {formula_name}の因数に問題はありません")
        
        if "previous_page" in ss:
            if st.button("戻る"):
                next_page(ss["previous_page"])
    
    elif ss['selected_option_persist'] == 'csvファイルを読み込む':
        filtered_df = df[df['施策ユニークNo'] == ss['strategy_number_persist']]
        st.write(f'「{filtered_df['施策名'].iloc[0]}」をテンプレートとして使用しています')

        if 'default_value_to_estimate_persist' not in ss:
            raw_content = filtered_df['value_to_estimate'].iloc[0]
            ss['default_value_to_estimate_persist'] = '' if pd.isna(raw_content) or raw_content == '' else str(raw_content)
        if 'default_value_to_estimate_temp' not in ss:
            ss['default_value_to_estimate_temp'] = ss['default_value_to_estimate_persist']

        if 'default_round_flag_persist' not in ss:
            ss['default_round_flag_persist'] = '' if pd.isna(v := filtered_df['round_flag'].iloc[0]) else str(int(v))
        if 'default_round_flag_temp' not in ss:
            ss['default_round_flag_temp'] = ss['default_round_flag_persist']

        if 'default_estimate_formula_persist' not in ss:
            raw_content = filtered_df['estimate_formula'].iloc[0]
            ss['default_estimate_formula_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimate_formula_temp' not in ss:
            ss['default_estimate_formula_temp'] = ss['default_estimate_formula_persist']

        if 'default_estimation_value_1_persist' not in ss:
            raw_content = filtered_df['estimation_value_1'].iloc[0]
            ss['default_estimation_value_1_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_1_temp' not in ss:
            ss['default_estimation_value_1_temp'] = ss['default_estimation_value_1_persist']
        pos = filtered_df.columns.get_loc('estimation_value_1')
        val = filtered_df.iloc[0, pos+1]
        if 'default_estimation_value_1_value_persist' not in ss:
            ss['default_estimation_value_1_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_estimation_value_1_value_temp' not in ss:
            ss['default_estimation_value_1_value_temp'] = ss['default_estimation_value_1_value_persist']
        if 'default_estimation_value_1_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_estimation_value_1_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_1_unit_temp' not in ss:
            ss['default_estimation_value_1_unit_temp'] = ss['default_estimation_value_1_unit_persist']
        if 'default_estimation_value_1_description_persist' not in ss:
            ss['default_estimation_value_1_description_persist'] = ''
        if 'default_estimation_value_1_description_temp' not in ss:
            ss['default_estimation_value_1_description_temp'] = ss['default_estimation_value_1_description_persist']

        if 'default_estimation_value_2_persist' not in ss:
            raw_content = filtered_df['estimation_value_2'].iloc[0]
            ss['default_estimation_value_2_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_2_temp' not in ss:
            ss['default_estimation_value_2_temp'] = ss['default_estimation_value_2_persist']
        pos = filtered_df.columns.get_loc('estimation_value_2')
        val = filtered_df.iloc[0, pos+1]
        if 'default_estimation_value_2_value_persist' not in ss:
            ss['default_estimation_value_2_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_estimation_value_2_value_temp' not in ss:
            ss['default_estimation_value_2_value_temp'] = ss['default_estimation_value_2_value_persist']
        if 'default_estimation_value_2_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_estimation_value_2_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_2_unit_temp' not in ss:
            ss['default_estimation_value_2_unit_temp'] = ss['default_estimation_value_2_unit_persist']
        if 'default_estimation_value_2_description_persist' not in ss:
            ss['default_estimation_value_2_description_persist'] = ''
        if 'default_estimation_value_2_description_temp' not in ss:
            ss['default_estimation_value_2_description_temp'] = ss['default_estimation_value_2_description_persist']

        if 'default_estimation_value_3_persist' not in ss:
            raw_content = filtered_df['estimation_value_3'].iloc[0]
            ss['default_estimation_value_3_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_3_temp' not in ss:
            ss['default_estimation_value_3_temp'] = ss['default_estimation_value_3_persist']
        pos = filtered_df.columns.get_loc('estimation_value_3')
        val = filtered_df.iloc[0, pos+1]
        if 'default_estimation_value_3_value_persist' not in ss:
            ss['default_estimation_value_3_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_estimation_value_3_value_temp' not in ss:
            ss['default_estimation_value_3_value_temp'] = ss['default_estimation_value_3_value_persist']
        if 'default_estimation_value_3_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_estimation_value_3_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_3_unit_temp' not in ss:
            ss['default_estimation_value_3_unit_temp'] = ss['default_estimation_value_3_unit_persist']
        if 'default_estimation_value_3_description_persist' not in ss:
            ss['default_estimation_value_3_description_persist'] = ''
        if 'default_estimation_value_3_description_temp' not in ss:
            ss['default_estimation_value_3_description_temp'] = ss['default_estimation_value_3_description_persist']

        if 'default_estimation_value_4_persist' not in ss:
            raw_content = filtered_df['estimation_value_4'].iloc[0]
            ss['default_estimation_value_4_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_4_temp' not in ss:
            ss['default_estimation_value_4_temp'] = ss['default_estimation_value_4_persist']
        pos = filtered_df.columns.get_loc('estimation_value_4')
        val = filtered_df.iloc[0, pos+1]
        if 'default_estimation_value_4_value_persist' not in ss:
            ss['default_estimation_value_4_value_persist'] = float(val) if isinstance(val, str) else val
        if 'default_estimation_value_4_value_temp' not in ss:
            ss['default_estimation_value_4_value_temp'] = ss['default_estimation_value_4_value_persist']
        if 'default_estimation_value_4_unit_persist' not in ss:
            raw_content = filtered_df.iloc[0, pos+2]
            ss['default_estimation_value_4_unit_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_estimation_value_4_unit_temp' not in ss:
            ss['default_estimation_value_4_unit_temp'] = ss['default_estimation_value_4_unit_persist']
        if 'default_estimation_value_4_description_persist' not in ss:
            ss['default_estimation_value_4_description_persist'] = ''
        if 'default_estimation_value_4_description_temp' not in ss:
            ss['default_estimation_value_4_description_temp'] = ss['default_estimation_value_4_description_persist']

        st.title("自由入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

        # # 'default_value_to_estimate_temp'が空の場合は、'additional_input_2'を初期値とする
        # if ss['default_value_to_estimate_temp'] == '':
        #     ss['default_value_to_estimate_temp'] = 'additional_input_2'

        select = st.selectbox(
            "推測値はどの因数ですか？",
            ["", "additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"],
            key='default_value_to_estimate_temp',
            on_change=store_content,
            args=('default_value_to_estimate_persist', 'default_value_to_estimate_temp')
        )
        ss["user_input"]["推測対象"] = select
        
        # # 'default_round_flag_temp'が空の場合は、0を初期値とする
        # if pd.isna(ss['default_round_flag_temp']):
        #     ss['default_round_flag_temp'] = '0'

        under = st.selectbox(
            "小数点以下何桁まで推測しますか？",
            ['', '0', '1'],
            key='default_round_flag_temp',
            on_change=store_content,
            args=('default_round_flag_persist', 'default_round_flag_temp')
        )
        ss["user_input"]["小数点以下の桁数"] = under
        
        fuel = ss["user_input"].get("燃料", "")
        
        emission_factors = {}
        fuel_prices = {}
        fuel_heat = {}
        load_factor_table = {}
        
        emission_factor_str = ""
        fuel_price_str = ""
        fuel_heat_str = ""
        
        default_suppose_formula = "推測値="
        ss["user_input"].setdefault("推測式", default_suppose_formula)

        estimation_formula = st.text_area(
            "推測式",
            key='default_estimate_formula_temp',
            on_change=store_content,
            args=('default_estimate_formula_persist', 'default_estimate_formula_temp')
        )
        ss["user_input"]["推測式"] = estimation_formula
        
        for i in range(4):
            st.subheader(f"推測規定値 {i+1}")
            value_format = "%.2f"
            description = ""

            name, unit, value = "", "", 0.0  
            
            ss["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
            ss["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
            ss["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
            ss["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
            
            estimation_value_name = st.text_input(
                f"推測規定値{i+1}_名前",
                key=f'default_estimation_value_{i+1}_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_persist', f'default_estimation_value_{i+1}_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_名前"] = estimation_value_name
            
            estimation_value_value = st.number_input(
                f"推測規定値{i+1}_数字",
                min_value=0.0,
                step=0.01,
                format=value_format,
                key=f'default_estimation_value_{i+1}_value_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_value_persist', f'default_estimation_value_{i+1}_value_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_数字"] = estimation_value_value
            
            estimation_value_unit = st.text_input(
                f"推測規定値{i+1}_単位",
                key=f'default_estimation_value_{i+1}_unit_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_unit_persist', f'default_estimation_value_{i+1}_unit_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_単位"] = estimation_value_unit
            
            estimation_value_description = st.text_area(
                f"推測規定値{i+1}_説明",
                key=f'default_estimation_value_{i+1}_description_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_description_persist', f'default_estimation_value_{i+1}_description_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_説明"] = estimation_value_description
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("推測値(容量)を確定", key="submitted_3C"):
                ss['previous_page_of_description'] = ss['page'] 
                next_page("description")
        with col2:
            if st.button("エラーチェック", "error_check_3C"):
                # チェックする計算式の辞書
                target_formula_dict = {"推測式": ss["user_input"]["推測式"]}
                # チェックする因数
                target_factors = [
                    ss["user_input"]["取得済みインプットの名前"],
                    ss["user_input"]["追加インプット1の名前"],
                    ss["user_input"]["追加インプット2の名前"],
                    ss["user_input"]["追加インプット3の名前"],
                    ss["user_input"]["追加インプット4の名前"],
                    ss["user_input"]["規定値(電気の排出係数)の名前"],
                    ss["user_input"]["規定値(電気料金)の名前"],
                    ss["user_input"]["規定値(想定稼働年数)の名前"],
                    ss["user_input"]["規定値1_名前"],
                    ss["user_input"]["規定値2_名前"],
                    ss["user_input"]["規定値3_名前"],
                    ss["user_input"]["規定値4_名前"],
                    ss["user_input"]["規定値5_名前"],
                    ss["user_input"]["規定値6_名前"],
                    ss["user_input"]["規定値7_名前"],
                    ss["user_input"]["規定値8_名前"],
                    ss["user_input"]["規定値9_名前"],
                    ss["user_input"]["規定値10_名前"],
                    ss["user_input"]["規定値11_名前"],
                    ss["user_input"]["規定値12_名前"],
                    ss["user_input"]["規定値13_名前"],
                    ss["user_input"]["推測規定値1_名前"],
                    ss["user_input"]["推測規定値2_名前"],
                    ss["user_input"]["推測規定値3_名前"],
                    ss["user_input"]["推測規定値4_名前"]
                ]

                for formula_name, formula in target_formula_dict.items():
                    parsed_list = split_formula(formula)
                    # 存在しなかった要素を保持するためのリスト
                    not_found_items = []
                    # リスト内の要素を1つずつ確認
                    for item in parsed_list:
                        found_in_any = False
                        # target_factorsに含まれる各因数についてチェック
                        for factor in target_factors:
                            if item == factor:
                                found_in_any = True
                                break
                        if not found_in_any:
                            not_found_items.append(item)
                    if not_found_items:
                        st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                        for i in not_found_items:
                            st.markdown(f"- {i}")
                    else:
                        st.success(f"✅ {formula_name}の因数に問題はありません")

        if "previous_page" in ss:
            if st.button("戻る"):
                next_page(ss["previous_page"])

    elif ss['selected_option_persist'] == 'jsonファイルを読み込む':
        st.write(f'「{ss['default_data']['設備']}_{ss['default_data']['施策名']}_{ss['default_data']['燃料']}」をテンプレートとして使用しています')

        if 'default_value_to_estimate_persist' not in ss:
            ss['default_value_to_estimate_persist'] = ss['default_data']['推測対象']
        if 'default_value_to_estimate_temp' not in ss:
            ss['default_value_to_estimate_temp'] = ss['default_value_to_estimate_persist']

        if 'default_round_flag_persist' not in ss:
            raw_content = ss['default_data']['小数点以下の桁数']
            ss['default_round_flag_persist'] = '' if pd.isna(raw_content) or raw_content == '' else str(int(raw_content))
        if 'default_round_flag_temp' not in ss:
            ss['default_round_flag_temp'] = ss['default_round_flag_persist']

        if 'default_estimate_formula_persist' not in ss:
            ss['default_estimate_formula_persist'] = ss['default_data']['推測式']
        if 'default_estimate_formula_temp' not in ss:
            ss['default_estimate_formula_temp'] = ss['default_estimate_formula_persist']

        if 'default_estimation_value_1_persist' not in ss:
            ss['default_estimation_value_1_persist'] = ss['default_data']['推測規定値1_名前']
        if 'default_estimation_value_1_temp' not in ss:
            ss['default_estimation_value_1_temp'] = ss['default_estimation_value_1_persist']
        if 'default_estimation_value_1_value_persist' not in ss:
            raw_content = ss['default_data']['推測規定値1_数字']
            ss['default_estimation_value_1_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_estimation_value_1_value_temp' not in ss:
            ss['default_estimation_value_1_value_temp'] = ss['default_estimation_value_1_value_persist']
        if 'default_estimation_value_1_unit_persist' not in ss:
            ss['default_estimation_value_1_unit_persist'] = ss['default_data']['推測規定値1_単位']
        if 'default_estimation_value_1_unit_temp' not in ss:
            ss['default_estimation_value_1_unit_temp'] = ss['default_estimation_value_1_unit_persist']
        if 'default_estimation_value_1_description_persist' not in ss:
            ss['default_estimation_value_1_description_persist'] = ss['default_data']['推測規定値1_説明']
        if 'default_estimation_value_1_description_temp' not in ss:
            ss['default_estimation_value_1_description_temp'] = ss['default_estimation_value_1_description_persist']

        if 'default_estimation_value_2_persist' not in ss:
            ss['default_estimation_value_2_persist'] = ss['default_data']['推測規定値2_名前']
        if 'default_estimation_value_2_temp' not in ss:
            ss['default_estimation_value_2_temp'] = ss['default_estimation_value_2_persist']
        if 'default_estimation_value_2_value_persist' not in ss:
            raw_content = ss['default_data']['推測規定値2_数字']
            ss['default_estimation_value_2_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_estimation_value_2_value_temp' not in ss:
            ss['default_estimation_value_2_value_temp'] = ss['default_estimation_value_2_value_persist']
        if 'default_estimation_value_2_unit_persist' not in ss:
            ss['default_estimation_value_2_unit_persist'] = ss['default_data']['推測規定値2_単位']
        if 'default_estimation_value_2_unit_temp' not in ss:
            ss['default_estimation_value_2_unit_temp'] = ss['default_estimation_value_2_unit_persist']
        if 'default_estimation_value_2_description_persist' not in ss:
            ss['default_estimation_value_2_description_persist'] = ss['default_data']['推測規定値2_説明']
        if 'default_estimation_value_2_description_temp' not in ss:
            ss['default_estimation_value_2_description_temp'] = ss['default_estimation_value_2_description_persist']

        if 'default_estimation_value_3_persist' not in ss:
            ss['default_estimation_value_3_persist'] = ss['default_data']['推測規定値3_名前']
        if 'default_estimation_value_3_temp' not in ss:
            ss['default_estimation_value_3_temp'] = ss['default_estimation_value_3_persist']
        if 'default_estimation_value_3_value_persist' not in ss:
            raw_content = ss['default_data']['推測規定値3_数字']
            ss['default_estimation_value_3_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_estimation_value_3_value_temp' not in ss:
            ss['default_estimation_value_3_value_temp'] = ss['default_estimation_value_3_value_persist']
        if 'default_estimation_value_3_unit_persist' not in ss:
            ss['default_estimation_value_3_unit_persist'] = ss['default_data']['推測規定値3_単位']
        if 'default_estimation_value_3_unit_temp' not in ss:
            ss['default_estimation_value_3_unit_temp'] = ss['default_estimation_value_3_unit_persist']
        if 'default_estimation_value_3_description_persist' not in ss:
            ss['default_estimation_value_3_description_persist'] = ss['default_data']['推測規定値3_説明']
        if 'default_estimation_value_3_description_temp' not in ss:
            ss['default_estimation_value_3_description_temp'] = ss['default_estimation_value_3_description_persist']

        if 'default_estimation_value_4_persist' not in ss:
            ss['default_estimation_value_4_persist'] = ss['default_data']['推測規定値4_名前']
        if 'default_estimation_value_4_temp' not in ss:
            ss['default_estimation_value_4_temp'] = ss['default_estimation_value_4_persist']
        if 'default_estimation_value_4_value_persist' not in ss:
            raw_content = ss['default_data']['推測規定値4_数字']
            ss['default_estimation_value_4_value_persist'] = np.nan if raw_content == '' else raw_content
        if 'default_estimation_value_4_value_temp' not in ss:
            ss['default_estimation_value_4_value_temp'] = ss['default_estimation_value_4_value_persist']
        if 'default_estimation_value_4_unit_persist' not in ss:
            ss['default_estimation_value_4_unit_persist'] = ss['default_data']['推測規定値4_単位']
        if 'default_estimation_value_4_unit_temp' not in ss:
            ss['default_estimation_value_4_unit_temp'] = ss['default_estimation_value_4_unit_persist']
        if 'default_estimation_value_4_description_persist' not in ss:
            ss['default_estimation_value_4_description_persist'] = ss['default_data']['推測規定値4_説明']
        if 'default_estimation_value_4_description_temp' not in ss:
            ss['default_estimation_value_4_description_temp'] = ss['default_estimation_value_4_description_persist']

        st.title("自由入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

        # # 'default_value_to_estimate_temp'が空の場合は、'additional_input_2'を初期値とする
        # if ss['default_value_to_estimate_temp'] == '':
        #     ss['default_value_to_estimate_temp'] = 'additional_input_2'

        select = st.selectbox(
            "推測値はどの因数ですか？",
            ["", "additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"],
            key='default_value_to_estimate_temp',
            on_change=store_content,
            args=('default_value_to_estimate_persist', 'default_value_to_estimate_temp')
        )
        ss["user_input"]["推測対象"] = select
        
        # # 'default_round_flag_temp'が空の場合は、0を初期値とする
        # if pd.isna(ss['default_round_flag_temp']):
        #     ss['default_round_flag_temp'] = '0'

        under = st.selectbox(
            "小数点以下何桁まで推測しますか？",
            ['', '0', '1'],
            key='default_round_flag_temp',
            on_change=store_content,
            args=('default_round_flag_persist', 'default_round_flag_temp')
        )
        ss["user_input"]["小数点以下の桁数"] = under
        
        fuel = ss["user_input"].get("燃料", "")
        
        emission_factors = {}
        fuel_prices = {}
        fuel_heat = {}
        load_factor_table = {}
        
        emission_factor_str = ""
        fuel_price_str = ""
        fuel_heat_str = ""
        
        default_suppose_formula = "推測値="
        ss["user_input"].setdefault("推測式", default_suppose_formula)

        estimation_formula = st.text_area(
            "推測式",
            key='default_estimate_formula_temp',
            on_change=store_content,
            args=('default_estimate_formula_persist', 'default_estimate_formula_temp')
        )
        ss["user_input"]["推測式"] = estimation_formula
        
        for i in range(4):
            st.subheader(f"推測規定値 {i+1}")
            value_format = "%.2f"
            description = ""

            name, unit, value = "", "", 0.0  
            
            ss["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
            ss["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
            ss["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
            ss["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
            
            estimation_value_name = st.text_input(
                f"推測規定値{i+1}_名前",
                key=f'default_estimation_value_{i+1}_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_persist', f'default_estimation_value_{i+1}_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_名前"] = estimation_value_name
            
            estimation_value_value = st.number_input(
                f"推測規定値{i+1}_数字",
                min_value=0.0,
                step=0.01,
                format=value_format,
                key=f'default_estimation_value_{i+1}_value_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_value_persist', f'default_estimation_value_{i+1}_value_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_数字"] = estimation_value_value
            
            estimation_value_unit = st.text_input(
                f"推測規定値{i+1}_単位",
                key=f'default_estimation_value_{i+1}_unit_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_unit_persist', f'default_estimation_value_{i+1}_unit_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_単位"] = estimation_value_unit
            
            estimation_value_description = st.text_area(
                f"推測規定値{i+1}_説明",
                key=f'default_estimation_value_{i+1}_description_temp',
                on_change=store_content,
                args=(f'default_estimation_value_{i+1}_description_persist', f'default_estimation_value_{i+1}_description_temp')
            )
            ss["user_input"][f"推測規定値{i+1}_説明"] = estimation_value_description
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("推測値(容量)を確定", key="submitted_3C"):
                ss['previous_page_of_description'] = ss['page'] 
                next_page("description")
        with col2:
            if st.button("エラーチェック", "error_check_3C"):
                # チェックする計算式の辞書
                target_formula_dict = {"推測式": ss["user_input"]["推測式"]}
                # チェックする因数
                target_factors = [
                    ss["user_input"]["取得済みインプットの名前"],
                    ss["user_input"]["追加インプット1の名前"],
                    ss["user_input"]["追加インプット2の名前"],
                    ss["user_input"]["追加インプット3の名前"],
                    ss["user_input"]["追加インプット4の名前"],
                    ss["user_input"]["規定値(電気の排出係数)の名前"],
                    ss["user_input"]["規定値(電気料金)の名前"],
                    ss["user_input"]["規定値(想定稼働年数)の名前"],
                    ss["user_input"]["規定値1_名前"],
                    ss["user_input"]["規定値2_名前"],
                    ss["user_input"]["規定値3_名前"],
                    ss["user_input"]["規定値4_名前"],
                    ss["user_input"]["規定値5_名前"],
                    ss["user_input"]["規定値6_名前"],
                    ss["user_input"]["規定値7_名前"],
                    ss["user_input"]["規定値8_名前"],
                    ss["user_input"]["規定値9_名前"],
                    ss["user_input"]["規定値10_名前"],
                    ss["user_input"]["規定値11_名前"],
                    ss["user_input"]["規定値12_名前"],
                    ss["user_input"]["規定値13_名前"],
                    ss["user_input"]["推測規定値1_名前"],
                    ss["user_input"]["推測規定値2_名前"],
                    ss["user_input"]["推測規定値3_名前"],
                    ss["user_input"]["推測規定値4_名前"]
                ]

                for formula_name, formula in target_formula_dict.items():
                    parsed_list = split_formula(formula)
                    # 存在しなかった要素を保持するためのリスト
                    not_found_items = []
                    # リスト内の要素を1つずつ確認
                    for item in parsed_list:
                        found_in_any = False
                        # target_factorsに含まれる各因数についてチェック
                        for factor in target_factors:
                            if item == factor:
                                found_in_any = True
                                break
                        if not found_in_any:
                            not_found_items.append(item)
                    if not_found_items:
                        st.error(f"{formula_name}において、以下のインプットまたは規定値に問題があります:")
                        for i in not_found_items:
                            st.markdown(f"- {i}")
                    else:
                        st.success(f"✅ {formula_name}の因数に問題はありません")

        if "previous_page" in ss:
            if st.button("戻る"):
                next_page(ss["previous_page"])


elif ss["page"] == "description":
    if ss['selected_option_persist'] == '使用しない':
        st.title("施策概要・専門家からの一言・適用条件入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")
    
        # ss["user_input"] = ss.get("user_input", {})
        
        # 施策概要
        formula_template = ss["user_input"].get("テンプレ", "")
        measure_type = ss["user_input"].get("施策の種類", "")
        fuel = ss["user_input"].get("燃料", "")
        neworold_scope_fuel = ss["user_input"].get("neworold_scope_燃料", "")
        equipment = ss["user_input"].get("設備", "")
        neworold_scope_equipment = ss["user_input"].get("neworold_scope_設備", "")
        
        default_summary = "施策概要記載準備中"
        if formula_template == "1(運用改善系)" or (formula_template == "5(自由入力)" and measure_type == "1(運用改善系)"):
            default_summary = f"前提(設備の解説など、必要な場合)\nユーザーのアクションで、施策の原理/仕組み(ないこともある)により、{equipment}の消費エネルギーとGHG排出量を削減することができます。"
        elif formula_template == "2(設備投資系)" or (formula_template == "5(自由入力)" and measure_type == "2(設備投資系)"):
            default_summary = f"前提(設備の解説など、必要な場合)\nユーザーのアクションで、施策の原理/仕組み(ないこともある)により、{equipment}の消費エネルギーとGHG排出量を削減することができます。\n設備更新の場合\n既存の{equipment}を高効率な{equipment}に更新することで、{equipment}の消費エネルギーとGHG排出量を削減することができます。{equipment}は年々省エネが進んでいるため、古い{equipment}と比較すると、最新の{equipment}は高効率になっています。"
        elif formula_template == "3(燃料転換系_1)" or (formula_template == "5(自由入力)" and measure_type == "3(燃料転換系_1)"):
            if neworold_scope_fuel == "電力":
                default_summary = f"化石燃料である{fuel}を用いる{equipment}を電力を用いる{neworold_scope_equipment}に転換します。CO2フリー電力などと組み合わせて、GHG排出量0を達成できますが、コストが増える可能性が高いです。"
            default_summary = f"{fuel}を用いる{equipment}をCO2排出量の少ない{neworold_scope_fuel}を用いる{neworold_scope_equipment}に転換することで、{equipment}のGHG排出量を削減することができます。"
        elif formula_template == "4(燃料転換系_2)" or (formula_template == "5(自由入力)" and measure_type == "4(燃料転換系_2)"):
            if neworold_scope_fuel == "電力":
                default_summary = f"化石燃料である{neworold_scope_fuel}を用いる{neworold_scope_equipment}を電力を用いる{equipment}に転換します。CO2フリー電力などと組み合わせて、GHG排出量0を達成できますが、コストが増える可能性が高いです。"
            default_summary = f"{neworold_scope_fuel}を用いる{neworold_scope_equipment}をCO2排出量の少ない{fuel}を用いる{equipment}に転換することで、{neworold_scope_equipment}のGHG排出量を削減することができます。"
        
        if 'default_施策概要_persist' not in ss:
            ss['default_施策概要_persist'] = default_summary
        if 'default_施策概要_temp' not in ss:
            ss['default_施策概要_temp'] = ss['default_施策概要_persist']

        if 'default_専門家からのアドバイス_persist' not in ss:
            ss['default_専門家からのアドバイス_persist'] = "専門家からの一言記載準備中"
        if 'default_専門家からのアドバイス_temp' not in ss:
            ss['default_専門家からのアドバイス_temp'] = ss['default_専門家からのアドバイス_persist']

        if 'default_適用条件1_persist' not in ss: 
            ss['default_適用条件1_persist'] = "適用条件記載準備中"
        if 'default_適用条件1_temp' not in ss: 
            ss['default_適用条件1_temp'] = ss['default_適用条件1_persist']

        if 'default_適用条件2_persist' not in ss:
            ss['default_適用条件2_persist'] = ""
        if 'default_適用条件2_temp' not in ss:
            ss['default_適用条件2_temp'] = ss['default_適用条件2_persist']

        if 'default_適用条件3_persist' not in ss:
            ss['default_適用条件3_persist'] = ""
        if 'default_適用条件3_temp' not in ss:
            ss['default_適用条件3_temp'] = ss['default_適用条件3_persist']

        if 'default_適用条件4_persist' not in ss:
            ss['default_適用条件4_persist'] =""
        if 'default_適用条件4_temp' not in ss:
            ss['default_適用条件4_temp'] = ss['default_適用条件4_persist']

        ss["user_input"].setdefault("施策概要", default_summary)
        ss["user_input"]["施策概要"] = st.text_area(
            "施策概要", 
            key='default_施策概要_temp',
            on_change=store_content,
            args=('default_施策概要_persist', 'default_施策概要_temp')
        )
        
        # 専門家からの一言
        ss["user_input"].setdefault("専門家からの一言", "専門家からの一言記載準備中")
        ss["user_input"]["専門家からの一言"] = st.text_area(
            "専門家からの一言",
            key='default_専門家からのアドバイス_temp',
            on_change=store_content,
            args=('default_専門家からのアドバイス_persist', 'default_専門家からのアドバイス_temp')
        )
        
        # 適用条件1
        ss["user_input"].setdefault("適用条件1", "適用条件記載準備中")
        ss["user_input"]["適用条件1"] = st.text_area(
            "適用条件1", 
            key='default_適用条件1_temp',
            on_change=store_content,
            args=('default_適用条件1_persist', 'default_適用条件1_temp')
        )

        # 適用条件2
        ss["user_input"].setdefault("適用条件2", "")
        ss["user_input"]["適用条件2"] = st.text_area(
            "適用条件2", 
            key='default_適用条件2_temp',
            on_change=store_content,
            args=('default_適用条件2_persist', 'default_適用条件2_temp')
        )

        # 適用条件3
        ss["user_input"].setdefault("適用条件3", "")
        ss["user_input"]["適用条件3"] = st.text_area(
            "適用条件3", 
            key='default_適用条件3_temp',
            on_change=store_content,
            args=('default_適用条件3_persist', 'default_適用条件3_temp')
        )

        # 適用条件4
        ss["user_input"].setdefault("適用条件4", "")
        ss["user_input"]["適用条件4"] = st.text_area(
            "適用条件4", 
            key='default_適用条件4_temp',
            on_change=store_content,
            args=('default_適用条件4_persist', 'default_適用条件4_temp')
        )
        
        # # 適用条件2~4
        # for i in range(2, 5):
        #     key = f"適用条件{i}"
        #     ss["user_input"].setdefault(key, "")
        #     ss["user_input"][key] = st.text_input(f"適用条件{i}", value=ss["user_input"].get(key, ""))
    
        left, right = st.columns(2)
        with right:
            if st.button('次へ'):
                next_page("flag_input")
        
        with left:
            if 'previous_page_of_description' in ss:
                if st.button("戻る"):
                    next_page(ss['previous_page_of_description'])
    
    elif ss['selected_option_persist'] == 'csvファイルを読み込む':
        st.title("施策概要・専門家からの一言・適用条件入力")
        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

        filtered_df = df[df['施策ユニークNo'] == ss['strategy_number_persist']]
        st.write(f'「{filtered_df['施策名'].iloc[0]}」をテンプレートとして使用しています')

        if 'default_施策概要_persist' not in ss:
            raw_content = filtered_df['施策概要'].iloc[0]
            ss['default_施策概要_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_施策概要_temp' not in ss:
            ss['default_施策概要_temp'] = ss['default_施策概要_persist']

        if 'default_専門家からのアドバイス_persist' not in ss:
            raw_content = filtered_df['専門家からのアドバイス'].iloc[0]
            ss['default_専門家からのアドバイス_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_専門家からのアドバイス_temp' not in ss:
            ss['default_専門家からのアドバイス_temp'] = ss['default_専門家からのアドバイス_persist']

        if 'default_適用条件1_persist' not in ss: 
            raw_content = filtered_df['適用条件1'].iloc[0]
            ss['default_適用条件1_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_適用条件1_temp' not in ss: 
            ss['default_適用条件1_temp'] = ss['default_適用条件1_persist']

        if 'default_適用条件2_persist' not in ss:
            raw_content = filtered_df['適用条件2'].iloc[0]
            ss['default_適用条件2_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_適用条件2_temp' not in ss:
            ss['default_適用条件2_temp'] = ss['default_適用条件2_persist']

        if 'default_適用条件3_persist' not in ss:
            raw_content = filtered_df['適用条件3'].iloc[0]
            ss['default_適用条件3_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_適用条件3_temp' not in ss:
            ss['default_適用条件3_temp'] = ss['default_適用条件3_persist']

        if 'default_適用条件4_persist' not in ss:
            raw_content = filtered_df['適用条件4'].iloc[0]
            ss['default_適用条件4_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_適用条件4_temp' not in ss:
            ss['default_適用条件4_temp'] = ss['default_適用条件4_persist']

        if 'default_適用条件（その他）_persist' not in ss:
            raw_content = filtered_df['適用条件（その他）'].iloc[0]
            ss['default_適用条件（その他）_persist'] = '' if pd.isna(raw_content) else raw_content
        if 'default_適用条件（その他）_temp' not in ss:
            ss['default_適用条件（その他）_temp'] = ss['default_適用条件（その他）_persist']
        
        # 施策概要
        formula_template = ss["user_input"].get("テンプレ", "")
        measure_type = ss["user_input"].get("施策の種類", "")
        fuel = ss["user_input"].get("燃料", "")
        neworold_scope_fuel = ss["user_input"].get("neworold_scope_燃料", "")
        equipment = ss["user_input"].get("設備", "")
        neworold_scope_equipment = ss["user_input"].get("neworold_scope_設備", "")
        
        default_summary = "施策概要記載準備中"
        if formula_template == "1(運用改善系)" or (formula_template == "5(自由入力)" and measure_type == "1(運用改善系)"):
            default_summary = f"前提(設備の解説など、必要な場合)\nユーザーのアクションで、施策の原理/仕組み(ないこともある)により、{equipment}の消費エネルギーとGHG排出量を削減することができます。"
        elif formula_template == "2(設備投資系)" or (formula_template == "5(自由入力)" and measure_type == "2(設備投資系)"):
            default_summary = f"前提(設備の解説など、必要な場合)\nユーザーのアクションで、施策の原理/仕組み(ないこともある)により、{equipment}の消費エネルギーとGHG排出量を削減することができます。\n設備更新の場合\n既存の{equipment}を高効率な{equipment}に更新することで、{equipment}の消費エネルギーとGHG排出量を削減することができます。{equipment}は年々省エネが進んでいるため、古い{equipment}と比較すると、最新の{equipment}は高効率になっています。"
        elif formula_template == "3(燃料転換系_1)" or (formula_template == "5(自由入力)" and measure_type == "3(燃料転換系_1)"):
            if neworold_scope_fuel == "電力":
                default_summary = f"化石燃料である{fuel}を用いる{equipment}を電力を用いる{neworold_scope_equipment}に転換します。CO2フリー電力などと組み合わせて、GHG排出量0を達成できますが、コストが増える可能性が高いです。"
            default_summary = f"{fuel}を用いる{equipment}をCO2排出量の少ない{neworold_scope_fuel}を用いる{neworold_scope_equipment}に転換することで、{equipment}のGHG排出量を削減することができます。"
        elif formula_template == "4(燃料転換系_2)" or (formula_template == "5(自由入力)" and measure_type == "4(燃料転換系_2)"):
            if neworold_scope_fuel == "電力":
                default_summary = f"化石燃料である{neworold_scope_fuel}を用いる{neworold_scope_equipment}を電力を用いる{equipment}に転換します。CO2フリー電力などと組み合わせて、GHG排出量0を達成できますが、コストが増える可能性が高いです。"
            default_summary = f"{neworold_scope_fuel}を用いる{neworold_scope_equipment}をCO2排出量の少ない{fuel}を用いる{equipment}に転換することで、{neworold_scope_equipment}のGHG排出量を削減することができます。"

        ss["user_input"].setdefault("施策概要", default_summary)
        strategy_explanation = st.text_area(
            "施策概要",
            key='default_施策概要_temp',
            on_change=store_content,
            args=('default_施策概要_persist', 'default_施策概要_temp')
        )
        ss["user_input"]["施策概要"] = strategy_explanation
        
        # 専門家からの一言
        ss["user_input"].setdefault("専門家からの一言", "専門家からの一言記載準備中")
        expert_advice = st.text_area(
            "専門家からの一言",
            key='default_専門家からのアドバイス_temp',
            on_change=store_content,
            args=('default_専門家からのアドバイス_persist', 'default_専門家からのアドバイス_temp')
        )
        ss["user_input"]["専門家からの一言"] = expert_advice
        
        # 適用条件1
        ss["user_input"].setdefault("適用条件1", "適用条件記載準備中")
        applicability_condition_1 = st.text_area(
            "適用条件1",
            key='default_適用条件1_temp',
            on_change=store_content,
            args=('default_適用条件1_persist', 'default_適用条件1_temp')
        )
        ss["user_input"]["適用条件1"] = applicability_condition_1

        # 適用条件2
        ss["user_input"].setdefault("適用条件2", "")
        applicability_condition_2 = st.text_area(
            "適用条件2",
            key='default_適用条件2_temp',
            on_change=store_content,
            args=('default_適用条件2_persist', 'default_適用条件2_temp')
        )
        ss["user_input"]["適用条件2"] = applicability_condition_2

        # 適用条件3
        ss["user_input"].setdefault("適用条件3", "")
        applicability_condition_3 = st.text_area(
            "適用条件3",
            key='default_適用条件3_temp',
            on_change=store_content,
            args=('default_適用条件3_persist', 'default_適用条件3_temp')
        )
        ss["user_input"]["適用条件3"] = applicability_condition_3

        # 適用条件4
        ss["user_input"].setdefault("適用条件4", "")
        applicability_condition_4 = st.text_area(
            "適用条件4",
            key='default_適用条件4_temp',
            on_change=store_content,
            args=('default_適用条件4_persist', 'default_適用条件4_temp')
        )
        ss["user_input"]["適用条件4"] = applicability_condition_4
    
        left, right = st.columns(2)
        with right:
            if st.button('次へ'):
                next_page("flag_input")
        
        with left:
            if 'previous_page_of_description' in ss:
                if st.button("戻る"):
                    next_page(ss['previous_page_of_description'])

    elif ss['selected_option_persist'] == 'jsonファイルを読み込む':
        st.title("施策概要・専門家からの一言・適用条件入力")
        st.write(f'「{ss['default_data']['設備']}_{ss['default_data']['施策名']}_{ss['default_data']['燃料']}」をテンプレートとして使用しています')

        st.write(f"現在入力中の施策：{ss['user_input']['設備']} {ss['user_input']['施策名']} {ss['user_input']['燃料']}")

        if 'default_施策概要_persist' not in ss:
            ss['default_施策概要_persist'] = ss['default_data']['施策概要']
        if 'default_施策概要_temp' not in ss:
            ss['default_施策概要_temp'] = ss['default_施策概要_persist']

        if 'default_専門家からのアドバイス_persist' not in ss:
            ss['default_専門家からのアドバイス_persist'] = ss['default_data']['専門家からの一言']
        if 'default_専門家からのアドバイス_temp' not in ss:
            ss['default_専門家からのアドバイス_temp'] = ss['default_専門家からのアドバイス_persist']

        if 'default_適用条件1_persist' not in ss: 
            ss['default_適用条件1_persist'] = ss['default_data']['適用条件1']
        if 'default_適用条件1_temp' not in ss: 
            ss['default_適用条件1_temp'] = ss['default_適用条件1_persist']

        if 'default_適用条件2_persist' not in ss:
            ss['default_適用条件2_persist'] = ss['default_data']['適用条件2']
        if 'default_適用条件2_temp' not in ss:
            ss['default_適用条件2_temp'] = ss['default_適用条件2_persist']

        if 'default_適用条件3_persist' not in ss:
            ss['default_適用条件3_persist'] = ss['default_data']['適用条件3']
        if 'default_適用条件3_temp' not in ss:
            ss['default_適用条件3_temp'] = ss['default_適用条件3_persist']

        if 'default_適用条件4_persist' not in ss:
            ss['default_適用条件4_persist'] = ss['default_data']['適用条件4']
        if 'default_適用条件4_temp' not in ss:
            ss['default_適用条件4_temp'] = ss['default_適用条件4_persist']
        
        # 施策概要
        formula_template = ss["user_input"].get("テンプレ", "")
        measure_type = ss["user_input"].get("施策の種類", "")
        fuel = ss["user_input"].get("燃料", "")
        neworold_scope_fuel = ss["user_input"].get("neworold_scope_燃料", "")
        equipment = ss["user_input"].get("設備", "")
        neworold_scope_equipment = ss["user_input"].get("neworold_scope_設備", "")
        
        default_summary = "施策概要記載準備中"
        if formula_template == "1(運用改善系)" or (formula_template == "5(自由入力)" and measure_type == "1(運用改善系)"):
            default_summary = f"前提(設備の解説など、必要な場合)\nユーザーのアクションで、施策の原理/仕組み(ないこともある)により、{equipment}の消費エネルギーとGHG排出量を削減することができます。"
        elif formula_template == "2(設備投資系)" or (formula_template == "5(自由入力)" and measure_type == "2(設備投資系)"):
            default_summary = f"前提(設備の解説など、必要な場合)\nユーザーのアクションで、施策の原理/仕組み(ないこともある)により、{equipment}の消費エネルギーとGHG排出量を削減することができます。\n設備更新の場合\n既存の{equipment}を高効率な{equipment}に更新することで、{equipment}の消費エネルギーとGHG排出量を削減することができます。{equipment}は年々省エネが進んでいるため、古い{equipment}と比較すると、最新の{equipment}は高効率になっています。"
        elif formula_template == "3(燃料転換系_1)" or (formula_template == "5(自由入力)" and measure_type == "3(燃料転換系_1)"):
            if neworold_scope_fuel == "電力":
                default_summary = f"化石燃料である{fuel}を用いる{equipment}を電力を用いる{neworold_scope_equipment}に転換します。CO2フリー電力などと組み合わせて、GHG排出量0を達成できますが、コストが増える可能性が高いです。"
            default_summary = f"{fuel}を用いる{equipment}をCO2排出量の少ない{neworold_scope_fuel}を用いる{neworold_scope_equipment}に転換することで、{equipment}のGHG排出量を削減することができます。"
        elif formula_template == "4(燃料転換系_2)" or (formula_template == "5(自由入力)" and measure_type == "4(燃料転換系_2)"):
            if neworold_scope_fuel == "電力":
                default_summary = f"化石燃料である{neworold_scope_fuel}を用いる{neworold_scope_equipment}を電力を用いる{equipment}に転換します。CO2フリー電力などと組み合わせて、GHG排出量0を達成できますが、コストが増える可能性が高いです。"
            default_summary = f"{neworold_scope_fuel}を用いる{neworold_scope_equipment}をCO2排出量の少ない{fuel}を用いる{equipment}に転換することで、{neworold_scope_equipment}のGHG排出量を削減することができます。"

        ss["user_input"].setdefault("施策概要", default_summary)
        strategy_explanation = st.text_area(
            "施策概要",
            key='default_施策概要_temp',
            on_change=store_content,
            args=('default_施策概要_persist', 'default_施策概要_temp')
        )
        ss["user_input"]["施策概要"] = strategy_explanation
        
        # 専門家からの一言
        ss["user_input"].setdefault("専門家からの一言", "専門家からの一言記載準備中")
        expert_advice = st.text_area(
            "専門家からの一言",
            key='default_専門家からのアドバイス_temp',
            on_change=store_content,
            args=('default_専門家からのアドバイス_persist', 'default_専門家からのアドバイス_temp')
        )
        ss["user_input"]["専門家からの一言"] = expert_advice
        
        # 適用条件1
        ss["user_input"].setdefault("適用条件1", "適用条件記載準備中")
        applicability_condition_1 = st.text_area(
            "適用条件1",
            key='default_適用条件1_temp',
            on_change=store_content,
            args=('default_適用条件1_persist', 'default_適用条件1_temp')
        )
        ss["user_input"]["適用条件1"] = applicability_condition_1

        # 適用条件2
        ss["user_input"].setdefault("適用条件2", "")
        applicability_condition_2 = st.text_area(
            "適用条件2",
            key='default_適用条件2_temp',
            on_change=store_content,
            args=('default_適用条件2_persist', 'default_適用条件2_temp')
        )
        ss["user_input"]["適用条件2"] = applicability_condition_2

        # 適用条件3
        ss["user_input"].setdefault("適用条件3", "")
        applicability_condition_3 = st.text_area(
            "適用条件3",
            key='default_適用条件3_temp',
            on_change=store_content,
            args=('default_適用条件3_persist', 'default_適用条件3_temp')
        )
        ss["user_input"]["適用条件3"] = applicability_condition_3

        # 適用条件4
        ss["user_input"].setdefault("適用条件4", "")
        applicability_condition_4 = st.text_area(
            "適用条件4",
            key='default_適用条件4_temp',
            on_change=store_content,
            args=('default_適用条件4_persist', 'default_適用条件4_temp')
        )
        ss["user_input"]["適用条件4"] = applicability_condition_4
    
        left, right = st.columns(2)
        with right:
            if st.button('次へ'):
                next_page("flag_input")
        
        with left:
            if 'previous_page_of_description' in ss:
                if st.button("戻る"):
                    next_page(ss['previous_page_of_description'])


elif ss["page"] == "flag_input":
    if ss['selected_option_persist'] == '使用しない':
        st.title("フラグ入力")

        if 'default_増加タグ_persist' not in ss:
            ss['default_増加タグ_persist'] = int(0)
        if 'default_増加タグ_temp' not in ss:
            ss['default_増加タグ_temp'] = ss['default_増加タグ_persist']

        if 'default_設備更新タグ_persist' not in ss:
            ss['default_設備更新タグ_persist'] = int(0)
        if 'default_設備更新タグ_temp' not in ss:
            ss['default_設備更新タグ_temp'] = ss['default_設備更新タグ_persist']

        if 'default_絶対値タグ_persist' not in ss:
            ss['default_絶対値タグ_persist'] = int(0)
        if 'default_絶対値タグ_temp' not in ss:
            ss['default_絶対値タグ_temp'] = ss['default_絶対値タグ_persist']

        if 'default_事例数タグ_persist' not in ss:
            ss['default_事例数_persist'] = int(2) 
        if 'default_事例数_temp' not in ss:
            ss['default_事例数_temp'] = ss['default_事例数_persist']
        
        if 'default_自社だけでできるか_persist' not in ss:
            ss['default_自社だけでできるか_persist'] = int(0)
        if 'default_自社だけでできるか_temp' not in ss:
            ss['default_自社だけでできるか_temp'] = ss['default_自社だけでできるか_persist']

        if 'default_メーカー候補はすぐ探せるか_persist' not in ss:
            ss['default_メーカー候補はすぐ探せるか_persist'] = int(0)
        if 'default_メーカー候補はすぐ探せるか_temp' not in ss:
            ss['default_メーカー候補はすぐ探せるか_temp'] = ss['default_メーカー候補はすぐ探せるか_persist']

        if 'default_工事なしでできるか_persist' not in ss:
            ss['default_工事なしでできるか_persist'] = int(0)
        if 'default_工事なしでできるか_temp' not in ss:
            ss['default_工事なしでできるか_temp'] = ss['default_工事なしでできるか_persist']

        if 'default_投資額が小さいか_persist' not in ss:
            ss['default_投資額が小さいか_persist'] = int(0)
        if 'default_投資額が小さいか_temp' not in ss:
            ss['default_投資額が小さいか_temp'] = ss['default_投資額が小さいか_persist']

        if 'default_準備期間が短いか_persist' not in ss:
            ss['default_準備期間が短いか_persist'] = int(0)
        if 'default_準備期間が短いか_temp' not in ss:
            ss['default_準備期間が短いか_temp'] = ss['default_準備期間が短いか_persist']

        if 'default_工期が短いか_persist' not in ss:
            ss['default_工期が短いか_persist'] = int(0)
        if 'default_工期が短いか_temp' not in ss:
            ss['default_工期が短いか_temp'] = ss['default_工期が短いか_persist']

        if 'default_他設備を止めずにできるか_persist' not in ss:
            ss['default_他設備を止めずにできるか_persist'] = int(0)
        if 'default_他設備を止めずにできるか_temp' not in ss:
            ss['default_他設備を止めずにできるか_temp'] = ss['default_他設備を止めずにできるか_persist']

        if 'default_導入時に他設備との接続確認が不要か_persist' not in ss:
            ss['default_導入時に他設備との接続確認が不要か_persist'] = int(0)
        if 'default_導入時に他設備との接続確認が不要か_temp' not in ss:
            ss['default_導入時に他設備との接続確認が不要か_temp'] = ss['default_導入時に他設備との接続確認が不要か_persist']
    
        # --- 施策種類フラグ ---
        st.subheader("施策種類に関するフラグ（0 or 1）")
        ss["user_input"].setdefault("増加タグ", 0)
        ss["user_input"].setdefault("設備更新タグ", 0)
        ss["user_input"].setdefault("絶対値タグ", 0)

        increase_tag = st.selectbox(
            "増加タグ（燃料転換による燃料増加）", 
            [0, 1], 
            key='default_増加タグ_temp',
            on_change=store_content,
            args=('default_増加タグ_persist', 'default_増加タグ_temp')
        )
        ss["user_input"]["増加タグ"] = increase_tag

        equipment_renewal_tag = st.selectbox(
            "設備更新タグ", 
            [0, 1], 
            key='default_設備更新タグ_temp',
            on_change=store_content,
            args=('default_設備更新タグ_persist', 'default_設備更新タグ_temp') 
        )
        ss["user_input"]["設備更新タグ"] = equipment_renewal_tag

        absolute_tag = st.selectbox(
            "絶対値タグ", [0, 1], 
            key='default_絶対値タグ_temp',
            on_change=store_content,
            args=('default_絶対値タグ_persist', 'default_絶対値タグ_temp')
        )
        ss["user_input"]["絶対値タグ"] = absolute_tag

        # --- 事例数フラグ ---
        st.subheader("事例数に関するフラグ（1〜5）")
        ss["user_input"].setdefault("事例数フラグ", 3)
        case_count_flag = st.selectbox(
            "Web上での事例の多さ（業種を問わず）",
            [5, 4, 3, 2, 1],
            format_func=lambda x: f"{x} - {['数千件以上の事例がある', '数百件の事例がある', '数十件の事例がある', '4～10件の事例しか見つからない', '1～3件の事例しか見つからない'][5 - x]}",
            key='default_事例数_temp',
            on_change=store_content,
            args=('default_事例数_persist', 'default_事例数_temp')
        )
        ss["user_input"]["事例数フラグ"] = case_count_flag

        ss["user_input"]["事例の多さフラグ"] =  (ss["user_input"]["事例数フラグ"]-1) / 4

        # --- 施策実行に関するフラグ ---
        st.subheader("施策実行に関するフラグ（感覚値で構いません）")

        exec_flags = [
            ("自社だけでできるか", "自社だけでできる1 / できない0"),
            ("メーカー候補はすぐ探せるか", "できる1 / できない0"),
            ("工事なしでできるか", "できる1 / できない0"),
            ("投資額が小さいか", "小さい1 / 大きい0 (目安：設備価格の30%以上で大きい)"),
            ("準備期間が短いか", "短い1 / 長い0"),
            ("工期が短いか", "短い1 / 長い0"),
            ("他設備を止めずにできるか", "できる1 / できない0"),
            ("導入時に他設備との接続確認が不要か", "不要1 / 必要0")
        ]

        total_exec_flag_score = 0

        for k, description in exec_flags:
            st.markdown(f"**{k}**  ")
            ss["user_input"].setdefault(k, 0)
            v = st.selectbox(
                f"{description}", 
                [0, 1], 
                key=f'default_{k}_temp',
                on_change=store_content,
                args=(f'default_{k}_persist', f'default_{k}_temp')
            )
            ss["user_input"][k] = v
            total_exec_flag_score += ss["user_input"][k]

        ss["user_input"]["施策実行の簡単さフラグ"] = total_exec_flag_score / 8

        left, right = st.columns(2)
        with right:
            if st.button('次へ'):
                next_page("calculation")
    
        with left:
            if st.button("戻る"):
                next_page("description")
    
    elif ss['selected_option_persist'] == 'csvファイルを読み込む':
        filtered_df = df[df['施策ユニークNo'] == ss['strategy_number_persist']]
        st.write(f'「{filtered_df['施策名'].iloc[0]}」をテンプレートとして使用しています')
        st.title("フラグ入力")
    
        if 'default_増加タグ_persist' not in ss:
            raw_content = filtered_df['増加タグ'].iloc[0]
            ss['default_増加タグ_persist'] = int(0) if (pd.isna(raw_content) or str(raw_content).strip() == '') else int(raw_content)
        if 'default_増加タグ_temp' not in ss:
            ss['default_増加タグ_temp'] = ss['default_増加タグ_persist']

        if 'default_設備更新タグ_persist' not in ss:
            raw_content = filtered_df['設備更新カウンタ'].iloc[0]
            ss['default_設備更新タグ_persist'] = int(0) if (pd.isna(raw_content) or str(raw_content).strip() == '') else int(raw_content)
        if 'default_設備更新タグ_temp' not in ss:
            ss['default_設備更新タグ_temp'] = ss['default_設備更新タグ_persist']

        if 'default_絶対値タグ_persist' not in ss:
            raw_content = filtered_df['絶対値タグ'].iloc[0]
            ss['default_絶対値タグ_persist'] = int(0) if (pd.isna(raw_content) or str(raw_content).strip() == '') else int(raw_content)
        if 'default_絶対値タグ_temp' not in ss:
            ss['default_絶対値タグ_temp'] = ss['default_絶対値タグ_persist']

        if 'default_事例数タグ_persist' not in ss:
            ss['default_事例数_persist'] = int(2)
        if 'default_事例数_temp' not in ss:
            ss['default_事例数_temp'] = ss['default_事例数_persist']
        
        if 'default_自社だけでできるか_persist' not in ss:
            ss['default_自社だけでできるか_persist'] = int(0)
        if 'default_自社だけでできるか_temp' not in ss:
            ss['default_自社だけでできるか_temp'] = ss['default_自社だけでできるか_persist']

        if 'default_メーカー候補はすぐ探せるか_persist' not in ss:
            ss['default_メーカー候補はすぐ探せるか_persist'] = int(0)
        if 'default_メーカー候補はすぐ探せるか_temp' not in ss:
            ss['default_メーカー候補はすぐ探せるか_temp'] = ss['default_メーカー候補はすぐ探せるか_persist']

        if 'default_工事なしでできるか_persist' not in ss:
            ss['default_工事なしでできるか_persist'] = int(0)
        if 'default_工事なしでできるか_temp' not in ss:
            ss['default_工事なしでできるか_temp'] = ss['default_工事なしでできるか_persist']

        if 'default_投資額が小さいか_persist' not in ss:
            ss['default_投資額が小さいか_persist'] = int(0)
        if 'default_投資額が小さいか_temp' not in ss:
            ss['default_投資額が小さいか_temp'] = ss['default_投資額が小さいか_persist']

        if 'default_準備期間が短いか_persist' not in ss:
            ss['default_準備期間が短いか_persist'] = int(0)
        if 'default_準備期間が短いか_temp' not in ss:
            ss['default_準備期間が短いか_temp'] = ss['default_準備期間が短いか_persist']

        if 'default_工期が短いか_persist' not in ss:
            ss['default_工期が短いか_persist'] = int(0)
        if 'default_工期が短いか_temp' not in ss:
            ss['default_工期が短いか_temp'] = ss['default_工期が短いか_persist']

        if 'default_他設備を止めずにできるか_persist' not in ss:
            ss['default_他設備を止めずにできるか_persist'] = int(0)
        if 'default_他設備を止めずにできるか_temp' not in ss:
            ss['default_他設備を止めずにできるか_temp'] = ss['default_他設備を止めずにできるか_persist']

        if 'default_導入時に他設備との接続確認が不要か_persist' not in ss:
            ss['default_導入時に他設備との接続確認が不要か_persist'] = int(0)
        if 'default_導入時に他設備との接続確認が不要か_temp' not in ss:
            ss['default_導入時に他設備との接続確認が不要か_temp'] = ss['default_導入時に他設備との接続確認が不要か_persist']
            
        # --- 施策種類フラグ ---
        st.subheader("施策種類に関するフラグ（0 or 1）")
        ss["user_input"].setdefault("増加タグ", 0)
        ss["user_input"].setdefault("設備更新タグ", 0)
        ss["user_input"].setdefault("絶対値タグ", 0)

        increase_tag = st.selectbox(
            "増加タグ（燃料転換による燃料増加）", 
            [0, 1], 
            key='default_増加タグ_temp',
            on_change=store_content,
            args=('default_増加タグ_persist', 'default_増加タグ_temp')
        )
        ss["user_input"]["増加タグ"] = increase_tag

        equipment_renewal_tag = st.selectbox(
            "設備更新タグ", 
            [0, 1], 
            key='default_設備更新タグ_temp',
            on_change=store_content,
            args=('default_設備更新タグ_persist', 'default_設備更新タグ_temp') 
        )
        ss["user_input"]["設備更新タグ"] = equipment_renewal_tag

        absolute_tag = st.selectbox(
            "絶対値タグ", 
            [0, 1], 
            key='default_絶対値タグ_temp',
            on_change=store_content,
            args=('default_絶対値タグ_persist', 'default_絶対値タグ_temp')
        )
        ss["user_input"]["絶対値タグ"] = absolute_tag

        # --- 事例数フラグ ---
        st.subheader("事例数に関するフラグ（1〜5）")
        ss["user_input"].setdefault("事例数フラグ", 3)
        case_count_flag = st.selectbox(
            "Web上での事例の多さ（業種を問わず）",
            [5, 4, 3, 2, 1],
            format_func=lambda x: f"{x} - {['数千件以上の事例がある', '数百件の事例がある', '数十件の事例がある', '4～10件の事例しか見つからない', '1～3件の事例しか見つからない'][5 - x]}",
            key='default_事例数_temp',
            on_change=store_content,
            args=('default_事例数_persist', 'default_事例数_temp')
        )
        ss["user_input"]["事例数フラグ"] = case_count_flag

        ss["user_input"]["事例の多さフラグ"] =  (ss["user_input"]["事例数フラグ"]-1) / 4

        # --- 施策実行に関するフラグ ---
        st.subheader("施策実行に関するフラグ（感覚値で構いません）")

        exec_flags = [
            ("自社だけでできるか", "自社だけでできる1 / できない0"),
            ("メーカー候補はすぐ探せるか", "できる1 / できない0"),
            ("工事なしでできるか", "できる1 / できない0"),
            ("投資額が小さいか", "小さい1 / 大きい0 (目安：設備価格の30%以上で大きい)"),
            ("準備期間が短いか", "短い1 / 長い0"),
            ("工期が短いか", "短い1 / 長い0"),
            ("他設備を止めずにできるか", "できる1 / できない0"),
            ("導入時に他設備との接続確認が不要か", "不要1 / 必要0")
        ]

        total_exec_flag_score = 0

        for k, description in exec_flags:
            st.markdown(f"**{k}**  ")
            ss["user_input"].setdefault(k, 0)
            v = st.selectbox(
                f"{description}", 
                [0, 1],  
                key=f'default_{k}_temp',
                on_change=store_content,
                args=(f'default_{k}_persist', f'default_{k}_temp')
            )
            ss["user_input"][k] = v
            total_exec_flag_score += ss["user_input"][k]

        ss["user_input"]["施策実行の簡単さフラグ"] = total_exec_flag_score / 8

        left, right = st.columns(2)
        with right:
            if st.button('次へ'):
                next_page("calculation")
    
        with left:
            if st.button("戻る"):
                next_page("description")
    
    elif ss['selected_option_persist'] == 'jsonファイルを読み込む':
        st.write(f'「{ss['default_data']['設備']}_{ss['default_data']['施策名']}_{ss['default_data']['燃料']}」をテンプレートとして使用しています')
        st.title("フラグ入力")
    
        if 'default_増加タグ_persist' not in ss:
            raw_content = ss['default_data']['増加タグ']
            ss['default_増加タグ_persist'] = int(0) if (pd.isna(raw_content) or str(raw_content).strip() == '') else int(raw_content)
        if 'default_増加タグ_temp' not in ss:
            ss['default_増加タグ_temp'] = ss['default_増加タグ_persist']

        if 'default_設備更新タグ_persist' not in ss:
            raw_content = ss['default_data']['設備更新タグ']
            ss['default_設備更新タグ_persist'] = int(0) if (pd.isna(raw_content) or str(raw_content).strip() == '') else int(raw_content)
        if 'default_設備更新タグ_temp' not in ss:
            ss['default_設備更新タグ_temp'] = ss['default_設備更新タグ_persist']

        if 'default_絶対値タグ_persist' not in ss:
            raw_content = ss['default_data']['絶対値タグ']
            ss['default_絶対値タグ_persist'] = int(0) if (pd.isna(raw_content) or str(raw_content).strip() == '') else int(raw_content)
        if 'default_絶対値タグ_temp' not in ss:
            ss['default_絶対値タグ_temp'] = ss['default_絶対値タグ_persist']

        if 'default_事例数タグ_persist' not in ss:
            raw_content = ss['default_data']['事例数フラグ']
            ss['default_事例数_persist'] = int(raw_content) 
        if 'default_事例数_temp' not in ss:
            ss['default_事例数_temp'] = ss['default_事例数_persist']
        
        if 'default_自社だけでできるか_persist' not in ss:
            raw_content = ss['default_data']['自社だけでできるか']
            ss['default_自社だけでできるか_persist'] = int(raw_content)
        if 'default_自社だけでできるか_temp' not in ss:
            ss['default_自社だけでできるか_temp'] = ss['default_自社だけでできるか_persist']

        if 'default_メーカー候補はすぐ探せるか_persist' not in ss:
            raw_content = ss['default_data']['メーカー候補はすぐ探せるか']
            ss['default_メーカー候補はすぐ探せるか_persist'] = int(raw_content)
        if 'default_メーカー候補はすぐ探せるか_temp' not in ss:
            ss['default_メーカー候補はすぐ探せるか_temp'] = ss['default_メーカー候補はすぐ探せるか_persist']

        if 'default_工事なしでできるか_persist' not in ss:
            raw_content = ss['default_data']['工事なしでできるか']
            ss['default_工事なしでできるか_persist'] = int(raw_content)
        if 'default_工事なしでできるか_temp' not in ss:
            ss['default_工事なしでできるか_temp'] = ss['default_工事なしでできるか_persist']

        if 'default_投資額が小さいか_persist' not in ss:
            raw_content = ss['default_data']['投資額が小さいか']
            ss['default_投資額が小さいか_persist'] = int(raw_content)
        if 'default_投資額が小さいか_temp' not in ss:
            ss['default_投資額が小さいか_temp'] = ss['default_投資額が小さいか_persist']

        if 'default_準備期間が短いか_persist' not in ss:
            raw_content = ss['default_data']['準備期間が短いか']
            ss['default_準備期間が短いか_persist'] = int(raw_content)
        if 'default_準備期間が短いか_temp' not in ss:
            ss['default_準備期間が短いか_temp'] = ss['default_準備期間が短いか_persist']

        if 'default_工期が短いか_persist' not in ss:
            raw_content = ss['default_data']['工期が短いか']
            ss['default_工期が短いか_persist'] = int(raw_content)
        if 'default_工期が短いか_temp' not in ss:
            ss['default_工期が短いか_temp'] = ss['default_工期が短いか_persist']

        if 'default_他設備を止めずにできるか_persist' not in ss:
            raw_content = ss['default_data']['他設備を止めずにできるか']
            ss['default_他設備を止めずにできるか_persist'] = int(raw_content)
        if 'default_他設備を止めずにできるか_temp' not in ss:
            ss['default_他設備を止めずにできるか_temp'] = ss['default_他設備を止めずにできるか_persist']

        if 'default_導入時に他設備との接続確認が不要か_persist' not in ss:
            raw_content = ss['default_data']['導入時に他設備との接続確認が不要か']
            ss['default_導入時に他設備との接続確認が不要か_persist'] = int(raw_content)
        if 'default_導入時に他設備との接続確認が不要か_temp' not in ss:
            ss['default_導入時に他設備との接続確認が不要か_temp'] = ss['default_導入時に他設備との接続確認が不要か_persist']
            
        # --- 施策種類フラグ ---
        st.subheader("施策種類に関するフラグ（0 or 1）")
        ss["user_input"].setdefault("増加タグ", 0)
        ss["user_input"].setdefault("設備更新タグ", 0)
        ss["user_input"].setdefault("絶対値タグ", 0)

        increase_tag = st.selectbox(
            "増加タグ（燃料転換による燃料増加）", 
            [0, 1], 
            key='default_増加タグ_temp',
            on_change=store_content,
            args=('default_増加タグ_persist', 'default_増加タグ_temp')
        )
        ss["user_input"]["増加タグ"] = increase_tag

        equipment_renewal_tag = st.selectbox(
            "設備更新タグ", 
            [0, 1], 
            key='default_設備更新タグ_temp',
            on_change=store_content,
            args=('default_設備更新タグ_persist', 'default_設備更新タグ_temp') 
        )
        ss["user_input"]["設備更新タグ"] = equipment_renewal_tag

        absolute_tag = st.selectbox(
            "絶対値タグ", 
            [0, 1], 
            key='default_絶対値タグ_temp',
            on_change=store_content,
            args=('default_絶対値タグ_persist', 'default_絶対値タグ_temp')
        )
        ss["user_input"]["絶対値タグ"] = absolute_tag

        # --- 事例数フラグ ---
        st.subheader("事例数に関するフラグ（1〜5）")
        ss["user_input"].setdefault("事例数フラグ", 3)
        case_count_flag = st.selectbox(
            "Web上での事例の多さ（業種を問わず）",
            [5, 4, 3, 2, 1],
            format_func=lambda x: f"{x} - {['数千件以上の事例がある', '数百件の事例がある', '数十件の事例がある', '4～10件の事例しか見つからない', '1～3件の事例しか見つからない'][5 - x]}",
            key='default_事例数_temp',
            on_change=store_content,
            args=('default_事例数_persist', 'default_事例数_temp')
        )
        ss["user_input"]["事例数フラグ"] = case_count_flag

        ss["user_input"]["事例の多さフラグ"] =  (ss["user_input"]["事例数フラグ"]-1) / 4

        # --- 施策実行に関するフラグ ---
        st.subheader("施策実行に関するフラグ（感覚値で構いません）")

        exec_flags = [
            ("自社だけでできるか", "自社だけでできる1 / できない0"),
            ("メーカー候補はすぐ探せるか", "できる1 / できない0"),
            ("工事なしでできるか", "できる1 / できない0"),
            ("投資額が小さいか", "小さい1 / 大きい0 (目安：設備価格の30%以上で大きい)"),
            ("準備期間が短いか", "短い1 / 長い0"),
            ("工期が短いか", "短い1 / 長い0"),
            ("他設備を止めずにできるか", "できる1 / できない0"),
            ("導入時に他設備との接続確認が不要か", "不要1 / 必要0")
        ]

        total_exec_flag_score = 0

        for k, description in exec_flags:
            st.markdown(f"**{k}**  ")
            ss["user_input"].setdefault(k, 0)
            v = st.selectbox(
                f"{description}", 
                [0, 1],  
                key=f'default_{k}_temp',
                on_change=store_content,
                args=(f'default_{k}_persist', f'default_{k}_temp')
            )
            ss["user_input"][k] = v
            total_exec_flag_score += ss["user_input"][k]

        ss["user_input"]["施策実行の簡単さフラグ"] = total_exec_flag_score / 8

        left, right = st.columns(2)
        with right:
            if st.button('次へ'):
                next_page("calculation")
    
        with left:
            if st.button("戻る"):
                next_page("description")

elif ss["page"] == "calculation":
    st.title("計算式シミュレーションページ")
    st.write("以下の式に基づき、ユーザーが入力した値から計算を行います")

    if "calculation_results" not in ss:
        ss["calculation_results"] = {}

    def evaluate_formula(label, formula_key, override_inputs=None):
        formula = ss["user_input"].get(formula_key, "")

        if not formula or formula.strip() == "なし":
            st.warning(f"{label}の計算式は未入力または'なし'のため、0として処理されました。")
            ss["calculation_results"][label] = 0.0
            ss["user_input"][f"{formula_key}計算結果"] = 0.0
            return 0.0

        st.subheader(f"対象の計算式：{label}")
        st.markdown(f"```{formula}```")

        values = {} if override_inputs is None else dict(override_inputs)

        def set_if_not_override(key, value):
            if override_inputs is None or key not in override_inputs:
                values[key] = value

        key = ss["user_input"].get("取得済みインプットの名前", "")
        val = ss["user_input"].get("取得済みインプットの数字", 0.0)
        if key:
            set_if_not_override(key, val)

        for i in range(6):
            name = ss["user_input"].get(f"追加インプット{i+1}の名前", "")
            val = ss["user_input"].get(f"追加インプット{i+1}の数字", 0.0)
            if name:
                set_if_not_override(name, val)

        for key in ['電気の排出係数', '電気料金', '想定稼働年数']:
            name = ss["user_input"].get(f"規定値({key})の名前", "")
            val = ss["user_input"].get(f"規定値({key})の数字", 0.0)
            if name:
                set_if_not_override(name, val)

        for i in range(13):
            name = ss["user_input"].get(f"規定値{i+1}_名前", "")
            val = ss["user_input"].get(f"規定値{i+1}_数字", 0.0)
            if name:
                set_if_not_override(name, val)

        evaluated_formula = formula
        for key, val in values.items():
            evaluated_formula = evaluated_formula.replace(key, str(val))

        st.subheader("置換後の計算式")
        st.markdown(f"```{evaluated_formula}```")

        evaluated_formula = re.sub(r"(\d+(?:\.\d+)?)<%>", r"(\1/100)", evaluated_formula)
        evaluated_formula = re.sub(r"<[^>]+>", "", evaluated_formula)
        evaluated_formula = evaluated_formula.replace("×", "*").replace("÷", "/")
        evaluated_formula = evaluated_formula.replace(" ", "")

        if "=" in evaluated_formula:
            rhs = evaluated_formula.split("=")[1]
        else:
            rhs = evaluated_formula

        try:
            if rhs.strip() in ["", "0", "0.0"]:
                raise ZeroDivisionError("無効な式")
            if rhs.strip() == "-inf":
                result = float('-inf')
            else:
                result = eval(rhs)
                if isinstance(result, float):
                    if result != result:  # NaN
                        raise ValueError("計算結果がNaNです")
                    if result == float("inf") or result == float("-inf"):
                        # JSON非対応のため、文字列で保存
                        st.warning(f"{label}の計算結果は {result} です（Google Sheetsでは文字列として送信されます）")
                        ss["calculation_results"][label] = str(result)
                        ss["user_input"][f"{formula_key}計算結果"] = str(result)
                        return result
                st.success(f"{label}の計算結果: {result:.2f}")
                ss["calculation_results"][label] = result
                ss["user_input"][f"{formula_key}計算結果"] = result
            return result
        except Exception as e:
            st.warning(f"{label}の計算に失敗しました。値を0として処理します。エラー内容: {e}")
            ss["calculation_results"][label] = 0.0
            ss["user_input"][f"{formula_key}計算結果"] = 0.0
            return 0.0

    estimated_value = None
    if "推測式" in ss["user_input"] and ss["user_input"]["推測式"].strip() != "なし":
        st.header("\n\n---\n\n推測式の評価")

        guess_values = {}
        target_input_key = ss["user_input"].get("推測対象", "")
        input_index = int(target_input_key.split("_")[-1]) if target_input_key.startswith("additional_input_") else None

        guess_formula = ss["user_input"]["推測式"]
        name = ss["user_input"].get(f"追加インプット{input_index}の名前", "")
        st.subheader(f"対象の計算式：推測式（追加インプット{input_index} = {name}）")
        st.markdown(f"```{guess_formula}```")

        for i in range(4):
            name = ss["user_input"].get(f"推測規定値{i+1}_名前", "")
            val = ss["user_input"].get(f"推測規定値{i+1}_数字", 0.0)
            if name:
                guess_values[name] = val

        base_key = ss["user_input"].get("取得済みインプットの名前", "")
        base_val = ss["user_input"].get("取得済みインプットの数字", 0.0)
        if base_key:
            guess_values[base_key] = base_val

        for i in range(6):
            name = ss["user_input"].get(f"追加インプット{i+1}の名前", "")
            val = ss["user_input"].get(f"追加インプット{i+1}の数字", 0.0)
            if name:
                guess_values[name] = val

        for key in ['電気の排出係数', '電気料金', '想定稼働年数']:
            name = ss["user_input"].get(f"規定値({key})の名前", "")
            val = ss["user_input"].get(f"規定値({key})の数字", 0.0)
            if name:
                guess_values[name] = val

        for i in range(13):
            name = ss["user_input"].get(f"規定値{i+1}_名前", "")
            val = ss["user_input"].get(f"規定値{i+1}_数字", 0.0)
            if name:
                guess_values[name] = val

        evaluated_formula = guess_formula
        for key, val in guess_values.items():
            evaluated_formula = evaluated_formula.replace(key, str(val))

        st.subheader("置換後の計算式")
        st.markdown(f"```{evaluated_formula}```")

        evaluated_formula = re.sub(r"(\d+(?:\.\d+)?)<%>", r"(\1/100)", evaluated_formula)
        evaluated_formula = re.sub(r"<[^>]+>", "", evaluated_formula)
        evaluated_formula = evaluated_formula.replace("×", "*").replace("÷", "/")
        evaluated_formula = evaluated_formula.replace(" ", "")

        if "=" in evaluated_formula:
            rhs = evaluated_formula.split("=")[1]
        else:
            rhs = evaluated_formula

        try:
            estimated_value = eval(rhs)
            decimals = int(ss["user_input"].get("小数点以下の桁数", 1))
            estimated_value = round(estimated_value, decimals)
            st.success(f"推測値: {estimated_value:.{decimals}f}")
            ss["user_input"]["推測式"] = guess_formula
            ss["user_input"]["推測式計算結果"] = estimated_value
            if input_index is not None:
                name_key = f"追加インプット{input_index}の名前"
                name = ss["user_input"].get(name_key, "")
                if name:
                    ss["user_input"][f"追加インプット{input_index}の数字"] = estimated_value
        except Exception as e:
            st.warning(f"推測式の計算に失敗しました。値を0として処理します。エラー内容: {e}")
            estimated_value = 0.0
            ss["user_input"]["推測式"] = guess_formula
            ss["user_input"]["推測式計算結果"] = estimated_value
        
    if estimated_value is None:
        st.warning("推測式が未入力または'なし'のため、0として処理されました。")
        estimated_value = 0.0
        ss["user_input"]["推測式計算結果"] = estimated_value

    override_map = {}
    if estimated_value is not None and input_index is not None:
        name = ss["user_input"].get(f"追加インプット{input_index}の名前", "")
        if name:
            override_map[name] = estimated_value

    evaluate_formula("GHG削減量", "GHG削減量計算式", override_inputs=override_map)
    evaluate_formula("コスト削減額", "コスト削減額計算式", override_inputs=override_map)
    evaluate_formula("投資額", "投資額計算式", override_inputs=override_map)
    evaluate_formula("追加投資額", "追加投資額計算式", override_inputs=override_map)

        # --- 指標評価 ---
    st.header("評価指標の算出(5段階評価)")

    ghg = ss["user_input"].get("GHG削減量計算式計算結果", 0.0)
    cost = ss["user_input"].get("コスト削減額計算式計算結果", 0.0)
    invest = ss["user_input"].get("投資額計算式計算結果", 0.0)
    add_invest = ss["user_input"].get("追加投資額計算式計算結果", 0.0)
    years = ss["user_input"].get("規定値(想定稼働年数)の数字", 0.0)

    # 投資回収年数
    if cost > 0:
        payback = add_invest / cost
    else:
        payback = float('inf')

    if payback <= 5:
        payback_score = 5
    elif payback <= 10:
        payback_score = 4
    elif payback <= 15:
        payback_score = 3
    elif payback <= 20:
        payback_score = 2
    else:
        payback_score = 1

    st.subheader("1. 投資回収年数")
    st.write(f"シミュレーション結果: {payback:.2f} 年")
    st.write(f"スコア: {payback_score}")
    if payback == float('inf'):
        ss["user_input"]["投資回収年数"] = str(payback)
    else:
        ss["user_input"]["投資回収年数"] = payback
    ss["user_input"]["投資回収年数スコア"] = payback_score

    # 経済収支÷CO2削減量（万円/ton）
    if ghg * years > 0:
        ratio = (cost * years - add_invest) / (ghg * years) / 10000  # 万円に変換
    else:
        ratio = float('-inf')

    if ratio >= 10:
        ratio_score = 5
    elif ratio >= 5:
        ratio_score = 4
    elif ratio >= 2:
        ratio_score = 3
    elif ratio >= 0:
        ratio_score = 2
    else:
        ratio_score = 1

    st.subheader("2. 経済収支÷CO2削減量")
    st.write(f"シミュレーション結果: {ratio:.2f} 万円/ton-CO2e")
    st.write(f"スコア: {ratio_score}")
    if ratio == float('-inf'):
        ss["user_input"]["経済収支÷CO2削減量"] = str(ratio)
    else:
        ss["user_input"]["経済収支÷CO2削減量"] = ratio
    ss["user_input"]["経済収支÷CO2削減量スコア"] = ratio_score

    # CO2削減量規模
    if ghg >= 50:
        ghg_score = 5
    elif ghg >= 10:
        ghg_score = 4
    elif ghg >= 5:
        ghg_score = 3
    elif ghg >= 2:
        ghg_score = 2
    else:
        ghg_score = 1

    st.subheader("3. CO2削減量の規模")
    st.write(f"シミュレーション結果: {ghg:.2f} t-CO2/年")
    st.write(f"スコア: {ghg_score}")
    ss["user_input"]["CO2削減量の規模"] = ghg
    ss["user_input"]["CO2削減量の規模スコア"] = ghg_score

    # 正規化スコア（0〜1に変換）
    ss["user_input"]["投資回収年数スコア_正規化"] = (payback_score - 1) / 4
    ss["user_input"]["経済収支÷CO2削減量スコア_正規化"] = (ratio_score - 1) / 4
    ss["user_input"]["CO2削減量の規模スコア_正規化"] = (ghg_score - 1) / 4

    left, right = st.columns(2)
    with right:
        if st.button("入力情報の確認へ"):
            next_page("summary")
    
    with left:
        if st.button('戻る'):
            next_page('flag_input')

# ** サマリーページ **
elif ss["page"] == "summary":
    st.title("入力情報確認")
    for key, value in ss["user_input"].items():
        st.write(f"{key}: {'' if pd.isna(value) else value}")

    # # **Google Sheets にデータを送信**
    # if st.button("データを送信"):
    #     try:
    #         st.write("✅ Google Sheets にデータを追加中...")
    #         user_data = [st.session_state["user_input"].get(k, "") for k in st.session_state["user_input"]]  # データをリスト化
    #         sheet.append_row(user_data)  # スプレッドシートにデータを追加
    #         st.success("✅ データをGoogle Sheetsに送信しました！")
    #     except Exception as e:
    #         st.error(f"❌ Google Sheets 書き込みエラー: {e}")
    # **Google Sheets にデータを送信**
    # **Google Sheets にデータを送信**

    left, right = st.columns(2)
    with right:
        if st.button("データを送信"):
            try:
                st.write("✅ Google Sheets にデータを追加中...")
    
                # データを取得
                user_data = ["" if pd.isna(v := ss["user_input"].get(k, "")) else v for k in ss["user_input"]]

                # データの中身を確認
                st.write("送信データ:", user_data)

                # jsonファイルに保存
                user_inputs = {k: ('' if pd.isna(v) else v) for k, v in ss['user_input'].items()}
                save_to_json = {f'{ss['user_input']['設備']}_{ss['user_input']['施策名']}_{ss['user_input']['燃料']}': user_inputs}
                json_path = Path('saved_inputs.json') # 保存するファイルを指定
                # ファイルが無ければエラーを発生させる
                if not json_path.exists():
                    raise FileNotFoundError(f'設定ファイル {json_path} が存在しません。先にファイルを作成してください。')
                # jsonファイルを開く
                with json_path.open('r', encoding='utf-8') as f:
                    data = json.load(f) 
                # 既存＋新規をマージ（キー重複時は上書き）
                data.update(save_to_json)
                # 上書き
                with json_path.open('w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
    
                # データが空でないことを確認
                if not any(user_data):
                    st.error("❌ 送信データが空のため、Google Sheets に追加できません。")
                else:
                    # デバッグ出力
                    st.write("✅ sheetの型チェック:", type(sheet))
                    # **スプレッドシートの最終行を取得して、次の行を決定**
                    last_row = len(sheet.get_all_values())  # すべてのデータを取得し、最後の行番号を取得
    
                    # **データを A 列から開始する**
                    sheet.insert_row(user_data, index=last_row + 1)
    
                    st.success("✅ データをGoogle Sheetsに送信しました！")

    
            except Exception as e:
                st.error(f"❌ Google Sheets 書き込みエラー: {e}")

    with left:
        if st.button('戻る'):
            next_page('calculation')