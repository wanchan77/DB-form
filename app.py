import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

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
    sheet = spreadsheet.sheet1
    st.write("\u2705 Google Sheets に接続成功！")
except Exception as e:
    st.error(f"\u274C Google Sheets への接続エラー: {e}")

# === ページ管理のためのセッション変数を初期化 ===
if "page" not in st.session_state:
    st.session_state["page"] = "page1"

if "user_input" not in st.session_state:
    st.session_state["user_input"] = {}

# ページ遷移関数
def next_page(next_page_name):
    st.session_state["page"] = next_page_name

# 設備と燃料の選択肢

# ** 1ページ目 **
if st.session_state["page"] == "page1":
    st.title("施策基本情報入力")
    scope = st.selectbox("どのScopeですか？", ["Scope1", "Scope2"])
    st.session_state["user_input"]["Scope"] = scope
    
    if scope == "Scope1":
        equipment_options = ["空調(ボイラ)", "空調(冷凍機)", "空調(ウォータチラー空冷式)", "空調(ウォータチラー水冷式)", "空調(GHP)(パッケージ式)", "冷蔵/冷凍", "給湯", "発電", "自動車", "トラック", "重機/建機(トラック除く)", "船舶", "航空機", "溶解炉", "焼却炉", "生産用ボイラー", "バーナー", "生産用ヒーター", "クリーンルーム用空調(ボイラ)", "クリーンルーム用空調(冷凍機)", "クリーンルーム用空調(ウォータチラー空冷式)", "クリーンルーム用空調(ウォータチラー水冷式)", "クリーンルーム用空調(GHP)(パッケージ式)", "焼鈍炉", "乾燥炉", "焼結炉/焼成炉", "焼入れ炉", "鍛造炉・鍛造加熱炉", "メッキ槽・電着塗装", "焼戻し炉", "衣類用乾燥機", "工業用乾燥機", "自家用発電機", "その他(SCOPE1)", "SCOPE1全体"]
        fuel_options = ["軽油", "原油", "灯油", "LPG", "LNG", "揮発油", "コンデンセート", "ナフサ", "A重油", "B・C重油", "石油アスファルト", "石油コークス", "水素ガス", "その他可燃性天然ガス", "原料炭", "一般炭", "無煙炭", "石炭コークス", "コールタール", "コークス炉ガス", "高炉ガス", "転炉ガス", "都市ガス", "その他燃料", "全体(カーボンオフセット)"]
    else:
        equipment_options = ["空調(電気)(パッケージ式)", "空調(電気)(冷凍機)", "空調(電気)(ウォーターチラー水冷式)", "空調(電気)(ウォーターチラー空冷式)", "冷蔵/冷凍", "給湯", "照明", "サーバー機器", "エレベータ", "コンプレッサー", "ポンプ", "送風機/給気・排気ファン", "電気自動車", "電動トラック", "その他(SCOPE2)", "SCOPE2全体"]
        fuel_options = ["電力","産業用蒸気", "産業用以外の蒸気", "温水", "冷水", "その他", "全体(カーボンオフセット)"]

    equipment = st.selectbox("どの設備の施策ですか？", equipment_options)
    st.session_state["user_input"]["設備"] = equipment

    fuel = st.selectbox("どの燃料ですか？", fuel_options)
    st.session_state["user_input"]["燃料"] = fuel

    formula_template = st.selectbox("式はテンプレですか？", ["1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(自由入力)"])
    st.session_state["user_input"]["テンプレ"] = formula_template

    if formula_template == "5(自由入力)":
        measure_type = st.selectbox("施策の種類はどれですか？(自由入力の場合のみ入力)", ["1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(緑施策)"])
        st.session_state["user_input"]["施策の種類"] = measure_type

    measures = st.text_input("施策名はなんですか？")
    st.session_state["user_input"]["施策名"] = measures

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
elif st.session_state["page"] == "page2A":
    st.title("運用改善系施策式入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")

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

    with st.form("input_form"):

        # **GHG削減量計算式**
        default_ghg_formula = f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
        st.session_state["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)
        st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
            "GHG削減量計算式",
            value=st.session_state["user_input"]["GHG削減量計算式"]
        )

        # **コスト削減額計算式**
        fuel = st.session_state["user_input"].get("燃料", "")
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

        default_cost_formula = f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
        st.session_state["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
        st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
            "コスト削減額計算式",
            value=st.session_state["user_input"]["コスト削減額計算式"]
        )

        # **投資額計算式**
        st.session_state["user_input"].setdefault("投資額計算式", "なし")
        st.session_state["user_input"]["投資額計算式"] = st.text_area(
            "投資額計算式",
            value=st.session_state["user_input"]["投資額計算式"]
        )

        # **追加投資額計算式**
        st.session_state["user_input"].setdefault("追加投資額計算式", "なし")
        st.session_state["user_input"]["追加投資額計算式"] = st.text_area(
            "追加投資額計算式",
            value=st.session_state["user_input"]["追加投資額計算式"]
        )

        st.subheader("取得済みインプット")
        default_input_name = f"{st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        st.session_state["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input(
            "インプットの名前",
            value=st.session_state["user_input"]["取得済みインプットの名前"]
        )
        st.session_state["user_input"].setdefault("取得済みインプットの数字", 200.0)
        st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input(
            "数字",
            value=st.session_state["user_input"]["取得済みインプットの数字"],
            min_value=0.0,
            step=1.0
        )
        st.session_state["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input(
            "単位",
            value=st.session_state["user_input"]["取得済みインプットの単位"]
        )

        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            st.session_state["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
            st.session_state["user_input"][name_key] = st.text_input(
                name_key,
                value=st.session_state["user_input"][name_key]
            )
            st.session_state["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
            st.session_state["user_input"][num_key] = st.number_input(
                num_key,
                value=st.session_state["user_input"][num_key],
                min_value=0.0,
                step=1.0
            )
            st.session_state["user_input"].setdefault(unit_key, "%" if i == 0 else "")
            st.session_state["user_input"][unit_key] = st.text_input(
                unit_key,
                value=st.session_state["user_input"][unit_key]
            )

        # 燃料取得
        fuel = st.session_state["user_input"].get("燃料", "")

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
            st.session_state["user_input"].setdefault(f"規定値({name})の名前", name_display)
            st.session_state["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            st.session_state["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            st.session_state["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            # ユーザー入力欄
            st.session_state["user_input"][f"規定値({name})の名前"] = st.text_input(
                f"規定値({name})の名前", value=st.session_state["user_input"][f"規定値({name})の名前"]
            )
            st.session_state["user_input"][f"規定値({name})の数字"] = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                value=st.session_state["user_input"][f"規定値({name})の数字"]
            )
            st.session_state["user_input"][f"規定値({name})の単位"] = st.text_input(
                f"規定値({name})の単位", value=st.session_state["user_input"][f"規定値({name})の単位"]
            )
            st.session_state["user_input"][f"規定値({name})の説明"] = st.text_area(
                f"規定値({name})の説明", value=st.session_state["user_input"][f"規定値({name})の説明"]
    )

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = st.session_state["user_input"].get("燃料", "")
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
            
            st.session_state["user_input"].setdefault(f"規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_説明", description)
            
            st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=st.session_state["user_input"][f"規定値{i+1}_名前"])
            st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                value=st.session_state["user_input"][f"規定値{i+1}_数字"]
            )
            st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=st.session_state["user_input"][f"規定値{i+1}_単位"])
            st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=st.session_state["user_input"][f"規定値{i+1}_説明"])

        # **推測値テンプレートの選択**
        prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
        st.session_state["user_input"].setdefault("推測値のテンプレ", prediction_template)
        st.session_state["user_input"]["推測値のテンプレ"] = prediction_template
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        st.session_state["previous_page"] = st.session_state["page"]  # 現在のページを保存
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    if st.button("戻る"):
        next_page("page1")

    # if st.button("完了"):
    #     next_page("summary")


elif st.session_state["page"] == "page2B":
    st.title("設備投資系式入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")

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

    with st.form("input_form"):

        # **GHG削減量計算式**
        default_ghg_formula = f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
        st.session_state["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)
        st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
            "GHG削減量計算式",
            value=st.session_state["user_input"]["GHG削減量計算式"]
        )

        # **コスト削減額計算式**
        fuel = st.session_state["user_input"].get("燃料", "")
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

        default_cost_formula = f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
        st.session_state["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
        st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
            "コスト削減額計算式",
            value=st.session_state["user_input"]["コスト削減額計算式"]
        )

        # **投資額計算式**
        st.session_state["user_input"].setdefault("投資額計算式", "なし")
        st.session_state["user_input"]["投資額計算式"] = st.text_area(
            "投資額計算式",
            value=st.session_state["user_input"]["投資額計算式"]
        )

        # **追加投資額計算式**
        st.session_state["user_input"].setdefault("追加投資額計算式", "なし")
        st.session_state["user_input"]["追加投資額計算式"] = st.text_area(
            "追加投資額計算式",
            value=st.session_state["user_input"]["追加投資額計算式"]
        )

        st.subheader("取得済みインプット")
        default_input_name = f"{st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        st.session_state["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input(
            "インプットの名前",
            value=st.session_state["user_input"]["取得済みインプットの名前"]
        )
        st.session_state["user_input"].setdefault("取得済みインプットの数字", 200.0)
        st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input(
            "数字",
            value=st.session_state["user_input"]["取得済みインプットの数字"],
            min_value=0.0,
            step=1.0
        )
        st.session_state["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input(
            "単位",
            value=st.session_state["user_input"]["取得済みインプットの単位"]
        )

        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            st.session_state["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
            st.session_state["user_input"][name_key] = st.text_input(
                name_key,
                value=st.session_state["user_input"][name_key]
            )
            st.session_state["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
            st.session_state["user_input"][num_key] = st.number_input(
                num_key,
                value=st.session_state["user_input"][num_key],
                min_value=0.0,
                step=1.0
            )
            st.session_state["user_input"].setdefault(unit_key, "%" if i == 0 else "")
            st.session_state["user_input"][unit_key] = st.text_input(
                unit_key,
                value=st.session_state["user_input"][unit_key]
            )

        # 燃料取得
        fuel = st.session_state["user_input"].get("燃料", "")

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
            st.session_state["user_input"].setdefault(f"規定値({name})の名前", name_display)
            st.session_state["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            st.session_state["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            st.session_state["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            # ユーザー入力欄
            st.session_state["user_input"][f"規定値({name})の名前"] = st.text_input(
                f"規定値({name})の名前", value=st.session_state["user_input"][f"規定値({name})の名前"]
            )
            st.session_state["user_input"][f"規定値({name})の数字"] = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                value=st.session_state["user_input"][f"規定値({name})の数字"]
            )
            st.session_state["user_input"][f"規定値({name})の単位"] = st.text_input(
                f"規定値({name})の単位", value=st.session_state["user_input"][f"規定値({name})の単位"]
            )
            st.session_state["user_input"][f"規定値({name})の説明"] = st.text_area(
                f"規定値({name})の説明", value=st.session_state["user_input"][f"規定値({name})の説明"]
    )

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = st.session_state["user_input"].get("燃料", "")
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
            
            st.session_state["user_input"].setdefault(f"規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_説明", description)
            
            st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=st.session_state["user_input"][f"規定値{i+1}_名前"])
            st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                value=st.session_state["user_input"][f"規定値{i+1}_数字"]
            )
            st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=st.session_state["user_input"][f"規定値{i+1}_単位"])
            st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=st.session_state["user_input"][f"規定値{i+1}_説明"])

        # **推測値テンプレートの選択**
        prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
        st.session_state["user_input"].setdefault("推測値のテンプレ", prediction_template)
        st.session_state["user_input"]["推測値のテンプレ"] = prediction_template
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        st.session_state["previous_page"] = st.session_state["page"]  # 現在のページを保存
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    if st.button("戻る"):
        next_page("page1")


elif st.session_state["page"] == "page2C":
    st.title("燃料転換系_1式入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")

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

    with st.form("input_form"):

        # **GHG削減量計算式**
        default_ghg_formula = f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
        st.session_state["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)
        st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
            "GHG削減量計算式",
            value=st.session_state["user_input"]["GHG削減量計算式"]
        )

        # **コスト削減額計算式**
        fuel = st.session_state["user_input"].get("燃料", "")
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

        default_cost_formula = f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
        st.session_state["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
        st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
            "コスト削減額計算式",
            value=st.session_state["user_input"]["コスト削減額計算式"]
        )

        # **投資額計算式**
        st.session_state["user_input"].setdefault("投資額計算式", "なし")
        st.session_state["user_input"]["投資額計算式"] = st.text_area(
            "投資額計算式",
            value=st.session_state["user_input"]["投資額計算式"]
        )

        # **追加投資額計算式**
        st.session_state["user_input"].setdefault("追加投資額計算式", "なし")
        st.session_state["user_input"]["追加投資額計算式"] = st.text_area(
            "追加投資額計算式",
            value=st.session_state["user_input"]["追加投資額計算式"]
        )

        st.subheader("取得済みインプット")
        default_input_name = f"{st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        st.session_state["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input(
            "インプットの名前",
            value=st.session_state["user_input"]["取得済みインプットの名前"]
        )
        st.session_state["user_input"].setdefault("取得済みインプットの数字", 200.0)
        st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input(
            "数字",
            value=st.session_state["user_input"]["取得済みインプットの数字"],
            min_value=0.0,
            step=1.0
        )
        st.session_state["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input(
            "単位",
            value=st.session_state["user_input"]["取得済みインプットの単位"]
        )

        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            st.session_state["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
            st.session_state["user_input"][name_key] = st.text_input(
                name_key,
                value=st.session_state["user_input"][name_key]
            )
            st.session_state["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
            st.session_state["user_input"][num_key] = st.number_input(
                num_key,
                value=st.session_state["user_input"][num_key],
                min_value=0.0,
                step=1.0
            )
            st.session_state["user_input"].setdefault(unit_key, "%" if i == 0 else "")
            st.session_state["user_input"][unit_key] = st.text_input(
                unit_key,
                value=st.session_state["user_input"][unit_key]
            )

        # 燃料取得
        fuel = st.session_state["user_input"].get("燃料", "")

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
            st.session_state["user_input"].setdefault(f"規定値({name})の名前", name_display)
            st.session_state["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            st.session_state["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            st.session_state["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            # ユーザー入力欄
            st.session_state["user_input"][f"規定値({name})の名前"] = st.text_input(
                f"規定値({name})の名前", value=st.session_state["user_input"][f"規定値({name})の名前"]
            )
            st.session_state["user_input"][f"規定値({name})の数字"] = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                value=st.session_state["user_input"][f"規定値({name})の数字"]
            )
            st.session_state["user_input"][f"規定値({name})の単位"] = st.text_input(
                f"規定値({name})の単位", value=st.session_state["user_input"][f"規定値({name})の単位"]
            )
            st.session_state["user_input"][f"規定値({name})の説明"] = st.text_area(
                f"規定値({name})の説明", value=st.session_state["user_input"][f"規定値({name})の説明"]
    )

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = st.session_state["user_input"].get("燃料", "")
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
            
            st.session_state["user_input"].setdefault(f"規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_説明", description)
            
            st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=st.session_state["user_input"][f"規定値{i+1}_名前"])
            st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                value=st.session_state["user_input"][f"規定値{i+1}_数字"]
            )
            st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=st.session_state["user_input"][f"規定値{i+1}_単位"])
            st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=st.session_state["user_input"][f"規定値{i+1}_説明"])

        # **推測値テンプレートの選択**
        prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
        st.session_state["user_input"].setdefault("推測値のテンプレ", prediction_template)
        st.session_state["user_input"]["推測値のテンプレ"] = prediction_template
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        st.session_state["previous_page"] = st.session_state["page"]  # 現在のページを保存
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    if st.button("戻る"):
        next_page("page1")


elif st.session_state["page"] == "page2D":
    st.title("燃料転換系_2式入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")

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

    with st.form("input_form"):

        # **GHG削減量計算式**
        default_ghg_formula = f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
        st.session_state["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)
        st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
            "GHG削減量計算式",
            value=st.session_state["user_input"]["GHG削減量計算式"]
        )

        # **コスト削減額計算式**
        fuel = st.session_state["user_input"].get("燃料", "")
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

        default_cost_formula = f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
        st.session_state["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
        st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
            "コスト削減額計算式",
            value=st.session_state["user_input"]["コスト削減額計算式"]
        )

        # **投資額計算式**
        st.session_state["user_input"].setdefault("投資額計算式", "なし")
        st.session_state["user_input"]["投資額計算式"] = st.text_area(
            "投資額計算式",
            value=st.session_state["user_input"]["投資額計算式"]
        )

        # **追加投資額計算式**
        st.session_state["user_input"].setdefault("追加投資額計算式", "なし")
        st.session_state["user_input"]["追加投資額計算式"] = st.text_area(
            "追加投資額計算式",
            value=st.session_state["user_input"]["追加投資額計算式"]
        )

        st.subheader("取得済みインプット")
        default_input_name = f"{st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        st.session_state["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input(
            "インプットの名前",
            value=st.session_state["user_input"]["取得済みインプットの名前"]
        )
        st.session_state["user_input"].setdefault("取得済みインプットの数字", 200.0)
        st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input(
            "数字",
            value=st.session_state["user_input"]["取得済みインプットの数字"],
            min_value=0.0,
            step=1.0
        )
        st.session_state["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input(
            "単位",
            value=st.session_state["user_input"]["取得済みインプットの単位"]
        )

        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            st.session_state["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
            st.session_state["user_input"][name_key] = st.text_input(
                name_key,
                value=st.session_state["user_input"][name_key]
            )
            st.session_state["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
            st.session_state["user_input"][num_key] = st.number_input(
                num_key,
                value=st.session_state["user_input"][num_key],
                min_value=0.0,
                step=1.0
            )
            st.session_state["user_input"].setdefault(unit_key, "%" if i == 0 else "")
            st.session_state["user_input"][unit_key] = st.text_input(
                unit_key,
                value=st.session_state["user_input"][unit_key]
            )

        # 燃料取得
        fuel = st.session_state["user_input"].get("燃料", "")

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
            st.session_state["user_input"].setdefault(f"規定値({name})の名前", name_display)
            st.session_state["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            st.session_state["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            st.session_state["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            # ユーザー入力欄
            st.session_state["user_input"][f"規定値({name})の名前"] = st.text_input(
                f"規定値({name})の名前", value=st.session_state["user_input"][f"規定値({name})の名前"]
            )
            st.session_state["user_input"][f"規定値({name})の数字"] = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                value=st.session_state["user_input"][f"規定値({name})の数字"]
            )
            st.session_state["user_input"][f"規定値({name})の単位"] = st.text_input(
                f"規定値({name})の単位", value=st.session_state["user_input"][f"規定値({name})の単位"]
            )
            st.session_state["user_input"][f"規定値({name})の説明"] = st.text_area(
                f"規定値({name})の説明", value=st.session_state["user_input"][f"規定値({name})の説明"]
    )

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = st.session_state["user_input"].get("燃料", "")
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
            
            st.session_state["user_input"].setdefault(f"規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_説明", description)
            
            st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=st.session_state["user_input"][f"規定値{i+1}_名前"])
            st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                value=st.session_state["user_input"][f"規定値{i+1}_数字"]
            )
            st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=st.session_state["user_input"][f"規定値{i+1}_単位"])
            st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=st.session_state["user_input"][f"規定値{i+1}_説明"])

        # **推測値テンプレートの選択**
        prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
        st.session_state["user_input"].setdefault("推測値のテンプレ", prediction_template)
        st.session_state["user_input"]["推測値のテンプレ"] = prediction_template
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        st.session_state["previous_page"] = st.session_state["page"]  # 現在のページを保存
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    if st.button("戻る"):
        next_page("page1")


elif st.session_state["page"] == "page2E":
    st.title("自由入力式入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")

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

    with st.form("input_form"):

        # **GHG削減量計算式**
        default_ghg_formula = f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
        st.session_state["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)
        st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
            "GHG削減量計算式",
            value=st.session_state["user_input"]["GHG削減量計算式"]
        )

        # **コスト削減額計算式**
        fuel = st.session_state["user_input"].get("燃料", "")
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

        default_cost_formula = f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
        st.session_state["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
        st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
            "コスト削減額計算式",
            value=st.session_state["user_input"]["コスト削減額計算式"]
        )

        # **投資額計算式**
        st.session_state["user_input"].setdefault("投資額計算式", "なし")
        st.session_state["user_input"]["投資額計算式"] = st.text_area(
            "投資額計算式",
            value=st.session_state["user_input"]["投資額計算式"]
        )

        # **追加投資額計算式**
        st.session_state["user_input"].setdefault("追加投資額計算式", "なし")
        st.session_state["user_input"]["追加投資額計算式"] = st.text_area(
            "追加投資額計算式",
            value=st.session_state["user_input"]["追加投資額計算式"]
        )

        st.subheader("取得済みインプット")
        default_input_name = f"{st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        st.session_state["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input(
            "インプットの名前",
            value=st.session_state["user_input"]["取得済みインプットの名前"]
        )
        st.session_state["user_input"].setdefault("取得済みインプットの数字", 200.0)
        st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input(
            "数字",
            value=st.session_state["user_input"]["取得済みインプットの数字"],
            min_value=0.0,
            step=1.0
        )
        st.session_state["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input(
            "単位",
            value=st.session_state["user_input"]["取得済みインプットの単位"]
        )

        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            st.session_state["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
            st.session_state["user_input"][name_key] = st.text_input(
                name_key,
                value=st.session_state["user_input"][name_key]
            )
            st.session_state["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
            st.session_state["user_input"][num_key] = st.number_input(
                num_key,
                value=st.session_state["user_input"][num_key],
                min_value=0.0,
                step=1.0
            )
            st.session_state["user_input"].setdefault(unit_key, "%" if i == 0 else "")
            st.session_state["user_input"][unit_key] = st.text_input(
                unit_key,
                value=st.session_state["user_input"][unit_key]
            )

        # 燃料取得
        fuel = st.session_state["user_input"].get("燃料", "")

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
            st.session_state["user_input"].setdefault(f"規定値({name})の名前", name_display)
            st.session_state["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            st.session_state["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            st.session_state["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            # ユーザー入力欄
            st.session_state["user_input"][f"規定値({name})の名前"] = st.text_input(
                f"規定値({name})の名前", value=st.session_state["user_input"][f"規定値({name})の名前"]
            )
            st.session_state["user_input"][f"規定値({name})の数字"] = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                value=st.session_state["user_input"][f"規定値({name})の数字"]
            )
            st.session_state["user_input"][f"規定値({name})の単位"] = st.text_input(
                f"規定値({name})の単位", value=st.session_state["user_input"][f"規定値({name})の単位"]
            )
            st.session_state["user_input"][f"規定値({name})の説明"] = st.text_area(
                f"規定値({name})の説明", value=st.session_state["user_input"][f"規定値({name})の説明"]
    )

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = st.session_state["user_input"].get("燃料", "")
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
            
            st.session_state["user_input"].setdefault(f"規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_説明", description)
            
            st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=st.session_state["user_input"][f"規定値{i+1}_名前"])
            st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                value=st.session_state["user_input"][f"規定値{i+1}_数字"]
            )
            st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=st.session_state["user_input"][f"規定値{i+1}_単位"])
            st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=st.session_state["user_input"][f"規定値{i+1}_説明"])

        # **推測値テンプレートの選択**
        prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
        st.session_state["user_input"].setdefault("推測値のテンプレ", prediction_template)
        st.session_state["user_input"]["推測値のテンプレ"] = prediction_template
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        st.session_state["previous_page"] = st.session_state["page"]  # 現在のページを保存
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    if st.button("戻る"):
        next_page("page1")


# ** 2ページ目F (緑施策) **
elif st.session_state["page"] == "page2F":
    st.title("緑施策式入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")

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

    with st.form("input_form"):

        # **GHG削減量計算式**
        default_ghg_formula = f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
        st.session_state["user_input"].setdefault("GHG削減量計算式", default_ghg_formula)
        st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
            "GHG削減量計算式",
            value=st.session_state["user_input"]["GHG削減量計算式"]
        )

        # **コスト削減額計算式**
        fuel = st.session_state["user_input"].get("燃料", "")
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

        default_cost_formula = f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷{emission_factor_str}×{fuel_price_str}"
        st.session_state["user_input"].setdefault("コスト削減額計算式", default_cost_formula)
        st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
            "コスト削減額計算式",
            value=st.session_state["user_input"]["コスト削減額計算式"]
        )

        # **投資額計算式**
        st.session_state["user_input"].setdefault("投資額計算式", "なし")
        st.session_state["user_input"]["投資額計算式"] = st.text_area(
            "投資額計算式",
            value=st.session_state["user_input"]["投資額計算式"]
        )

        # **追加投資額計算式**
        st.session_state["user_input"].setdefault("追加投資額計算式", "なし")
        st.session_state["user_input"]["追加投資額計算式"] = st.text_area(
            "追加投資額計算式",
            value=st.session_state["user_input"]["追加投資額計算式"]
        )

        st.subheader("取得済みインプット")
        default_input_name = f"{st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量"
        st.session_state["user_input"].setdefault("取得済みインプットの名前", default_input_name)
        st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input(
            "インプットの名前",
            value=st.session_state["user_input"]["取得済みインプットの名前"]
        )
        st.session_state["user_input"].setdefault("取得済みインプットの数字", 200.0)
        st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input(
            "数字",
            value=st.session_state["user_input"]["取得済みインプットの数字"],
            min_value=0.0,
            step=1.0
        )
        st.session_state["user_input"].setdefault("取得済みインプットの単位", "t-CO2")
        st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input(
            "単位",
            value=st.session_state["user_input"]["取得済みインプットの単位"]
        )

        # **追加インプット 6個**
        for i in range(6):
            st.subheader(f"追加インプット {i+1}")
            name_key = f"追加インプット{i+1}の名前"
            num_key = f"追加インプット{i+1}の数字"
            unit_key = f"追加インプット{i+1}の単位"

            st.session_state["user_input"].setdefault(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
            st.session_state["user_input"][name_key] = st.text_input(
                name_key,
                value=st.session_state["user_input"][name_key]
            )
            st.session_state["user_input"].setdefault(num_key, 50.0 if i == 0 else 0.0)
            st.session_state["user_input"][num_key] = st.number_input(
                num_key,
                value=st.session_state["user_input"][num_key],
                min_value=0.0,
                step=1.0
            )
            st.session_state["user_input"].setdefault(unit_key, "%" if i == 0 else "")
            st.session_state["user_input"][unit_key] = st.text_input(
                unit_key,
                value=st.session_state["user_input"][unit_key]
            )

        # 燃料取得
        fuel = st.session_state["user_input"].get("燃料", "")

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
            st.session_state["user_input"].setdefault(f"規定値({name})の名前", name_display)
            st.session_state["user_input"].setdefault(f"規定値({name})の数字", float(value_display))
            st.session_state["user_input"].setdefault(f"規定値({name})の単位", unit if value is not None else "")
            st.session_state["user_input"].setdefault(f"規定値({name})の説明", description if value is not None else "")

            # ユーザー入力欄
            st.session_state["user_input"][f"規定値({name})の名前"] = st.text_input(
                f"規定値({name})の名前", value=st.session_state["user_input"][f"規定値({name})の名前"]
            )
            st.session_state["user_input"][f"規定値({name})の数字"] = st.number_input(
                f"規定値({name})の数字",
                min_value=0.0,
                step=float(0.000001 if name == "電気の排出係数" else 0.01),
                format="%.6f" if name == "電気の排出係数" else "%.2f",
                value=st.session_state["user_input"][f"規定値({name})の数字"]
            )
            st.session_state["user_input"][f"規定値({name})の単位"] = st.text_input(
                f"規定値({name})の単位", value=st.session_state["user_input"][f"規定値({name})の単位"]
            )
            st.session_state["user_input"][f"規定値({name})の説明"] = st.text_area(
                f"規定値({name})の説明", value=st.session_state["user_input"][f"規定値({name})の説明"]
    )

        # **追加の規定値 13個**
        for i in range(13):
            st.subheader(f"規定値 {i+1}")
            fuel = st.session_state["user_input"].get("燃料", "")
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
            
            st.session_state["user_input"].setdefault(f"規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"規定値{i+1}_説明", description)
            
            st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=st.session_state["user_input"][f"規定値{i+1}_名前"])
            st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(
                f"規定値 {i+1} の数字",
                min_value=0.0,
                step=0.000001 if i == 1 else 0.01,
                format=value_format,
                value=st.session_state["user_input"][f"規定値{i+1}_数字"]
            )
            st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=st.session_state["user_input"][f"規定値{i+1}_単位"])
            st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=st.session_state["user_input"][f"規定値{i+1}_説明"])

        # **推測値テンプレートの選択**
        prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
        st.session_state["user_input"].setdefault("推測値のテンプレ", prediction_template)
        st.session_state["user_input"]["推測値のテンプレ"] = prediction_template
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        st.session_state["previous_page"] = st.session_state["page"]  # 現在のページを保存
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    if st.button("戻る"):
        next_page("page1")


elif st.session_state["page"] == "page3A":

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
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")
    with st.form("input_form"):
        select = st.selectbox("推測値はどの因数ですか？", ["additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"])
        st.session_state["user_input"]["推測対象"] = select
        
        under = st.selectbox("小数点以下何桁まで推測しますか？", ["0", "1"])
        st.session_state["user_input"]["小数点以下の桁数"] = float(under)
        
        # **推測式**
        fuel = st.session_state["user_input"].get("燃料", "")
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
            default_suppose_formula = f"推測値={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
        else:
            default_suppose_formula = f"推測値={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}×{fuel_heat_str}÷3.6÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
        
        st.session_state["user_input"].setdefault("推測式", default_suppose_formula)
        st.session_state["user_input"]["推測式"] = st.text_area("推測式", value=st.session_state["user_input"]["推測式"])
        
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
                equipment = st.session_state["user_input"].get("設備", "")
                value = float(load_factor_table.get(equipment, 0.0)) # デフォルト値を0.0に設定
            else:
                name, unit, value = "", "", 0.0  # 初期値を1.0に設定
            
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
            
            st.text_input(
                f"推測規定値 {i+1} の名前",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_名前", ""),
                key=f"推測規定値{i+1}_名前"
            )
            
            st.number_input(
                f"推測規定値 {i+1} の数字",
                min_value=0.0,
                step=0.01,
                format=value_format,
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_数字", 0.0),
                key=f"推測規定値{i+1}_数字"
            )
            
            st.text_input(
                f"推測規定値 {i+1} の単位",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_単位", ""),
                key=f"推測規定値{i+1}_単位"
            )
            
            st.text_area(
                f"推測規定値 {i+1} の説明",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_説明", ""),
                key=f"推測規定値{i+1}_説明"
            )
        
        submitted = st.form_submit_button("入力を確定")



    if submitted:
        next_page("summary")
    if "previous_page" in st.session_state:
        if st.button("戻る"):
            next_page(st.session_state["previous_page"])

elif st.session_state["page"] == "page3B":
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
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")
    with st.form("input_form"):
        select = st.selectbox("推測値はどの因数ですか？", ["additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"])
        st.session_state["user_input"]["推測対象"] = select
        
        under = st.selectbox("小数点以下何桁まで推測しますか？", ["0", "1"])
        st.session_state["user_input"]["小数点以下の桁数"] = float(under)
        
        # **推測式**
        fuel = st.session_state["user_input"].get("燃料", "")
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
            default_suppose_formula = f"推測値={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
        else:
            default_suppose_formula = f"推測値={st.session_state['user_input'].get('設備', '')}{{{fuel}}}のCO2排出量<t-CO2/年>÷{emission_factor_str}×{fuel_heat_str}÷3.6÷稼働時間<時間/日>÷稼働日数<日/年>÷負荷率<%>"
        
        st.session_state["user_input"].setdefault("推測式", default_suppose_formula)
        st.session_state["user_input"]["推測式"] = st.text_area("推測式", value=st.session_state["user_input"]["推測式"])
        
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
                equipment = st.session_state["user_input"].get("設備", "")
                value = float(load_factor_table.get(equipment, 0.0)) # デフォルト値を0.0に設定
            else:
                equipment = st.session_state["user_input"].get("設備", "")
                name, unit, value = f"{equipment}平均容量", "kW", 0.0  # 初期値を1.0に設定
            
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
            
            st.text_input(
                f"推測規定値 {i+1} の名前",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_名前", ""),
                key=f"推測規定値{i+1}_名前"
            )
            
            st.number_input(
                f"推測規定値 {i+1} の数字",
                min_value=0.0,
                step=0.01,
                format=value_format,
                value=float(st.session_state["user_input"].get(f"推測規定値{i+1}_数字", 0.0)),
                key=f"推測規定値{i+1}_数字"
            )
            
            st.text_input(
                f"推測規定値 {i+1} の単位",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_単位", ""),
                key=f"推測規定値{i+1}_単位"
            )
            
            st.text_area(
                f"推測規定値 {i+1} の説明",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_説明", ""),
                key=f"推測規定値{i+1}_説明"
            )
        
        submitted = st.form_submit_button("入力を確定")
    
    if submitted:
        next_page("summary")
    if "previous_page" in st.session_state:
        if st.button("戻る"):
            next_page(st.session_state["previous_page"])

elif st.session_state["page"] == "page3C":
    st.title("自由入力")
    st.write(f"現在入力中の施策：{st.session_state['user_input']['設備']} {st.session_state['user_input']['施策名']} {st.session_state['user_input']['燃料']}")
    with st.form("input_form"):
        select = st.selectbox("推測値はどの因数ですか？", ["additional_input_2", "additional_input_1", "additional_input_3", "additional_input_4", "additional_input_5", "additional_input_6"])
        st.session_state["user_input"]["推測対象"] = select
        
        under = st.selectbox("小数点以下何桁まで推測しますか？", ["0", "1"])
        st.session_state["user_input"]["小数点以下の桁数"] = float(under)
        
        fuel = st.session_state["user_input"].get("燃料", "")
        
        emission_factors = {}
        fuel_prices = {}
        fuel_heat = {}
        load_factor_table = {}
        
        emission_factor_str = ""
        fuel_price_str = ""
        fuel_heat_str = ""
        
        default_suppose_formula = "推測値="
        
        st.session_state["user_input"].setdefault("推測式", default_suppose_formula)
        st.session_state["user_input"]["推測式"] = st.text_area("推測式",value=st.session_state["user_input"]["推測式"])
        
        for i in range(4):
            st.subheader(f"推測規定値 {i+1}")
            value_format = "%.2f"
            description = ""

            name, unit, value = "", "", 0.0  
            
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_名前", name)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_数字", value)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_単位", unit)
            st.session_state["user_input"].setdefault(f"推測規定値{i+1}_説明", description)
            
            st.text_input(
                f"推測規定値 {i+1} の名前",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_名前", ""),
                key=f"推測規定値{i+1}_名前"
            )
            
            st.number_input(
                f"推測規定値 {i+1} の数字",
                min_value=0.0,
                step=0.01,
                format=value_format,
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_数字", 0.0),
                key=f"推測規定値{i+1}_数字"
            )
            
            st.text_input(
                f"推測規定値 {i+1} の単位",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_単位", ""),
                key=f"推測規定値{i+1}_単位"
            )
            
            st.text_area(
                f"推測規定値 {i+1} の説明",
                value=st.session_state["user_input"].get(f"推測規定値{i+1}_説明", ""),
                key=f"推測規定値{i+1}_説明"
            )
        
        submitted = st.form_submit_button("入力を確定")

    if submitted:
        next_page("summary")
    if "previous_page" in st.session_state:
        if st.button("戻る"):
            next_page(st.session_state["previous_page"])

# ** サマリーページ **
elif st.session_state["page"] == "summary":
    st.title("入力情報確認")
    for key, value in st.session_state["user_input"].items():
        st.write(f"{key}: {value if value is not None else ''}")

    # **Google Sheets にデータを送信**
    if st.button("データを送信"):
        try:
            st.write("✅ Google Sheets にデータを追加中...")
            user_data = [st.session_state["user_input"].get(k, "") for k in st.session_state["user_input"]]  # データをリスト化
            sheet.append_row(user_data)  # スプレッドシートにデータを追加
            st.success("✅ データをGoogle Sheetsに送信しました！")
        except Exception as e:
            st.error(f"❌ Google Sheets 書き込みエラー: {e}")



