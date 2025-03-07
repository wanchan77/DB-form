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

    # **GHG削減量計算式**
    st.session_state["user_input"]["GHG削減量計算式"] = st.text_area(
        "GHG削減量計算式",
        f"CO2削減量<t-CO2/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>"
    )

    # **コスト削減額計算式**
    st.session_state["user_input"]["コスト削減額計算式"] = st.text_area(
        "コスト削減額計算式",
        f"コスト削減額<円/年>={st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量<t-CO2/年>×対象設備の中で施策を実施する設備の割合<%>×省エネ率<%>÷電気の排出係数<t-CO2/kWh>×電気料金<円/kWh>"
    )

    # **投資額計算式**
    st.session_state["user_input"]["投資額計算式"] = st.text_area("投資額計算式", "なし")

    # **追加投資額計算式**
    st.session_state["user_input"]["追加投資額計算式"] = st.text_area("追加投資額計算式", "なし")


    st.subheader("取得済みインプット")
    st.session_state["user_input"]["取得済みインプットの名前"] = st.text_input("インプットの名前", f"{st.session_state['user_input'].get('設備', '')}{{{st.session_state['user_input'].get('燃料', '')}}}のCO2排出量")
    st.session_state["user_input"]["取得済みインプットの数字"] = st.number_input("数字", value=200.0, min_value=0.0, step=1.0)
    st.session_state["user_input"]["取得済みインプットの単位"] = st.text_input("単位", "t-CO2")

    # **追加インプット 6個**
    for i in range(6):
        st.subheader(f"追加インプット {i+1}")
        name_key = f"追加インプット{i+1}の名前"
        num_key = f"追加インプット{i+1}の数字"
        unit_key = f"追加インプット{i+1}の単位"

        st.session_state["user_input"][name_key] = st.text_input(name_key, "対象設備の中で施策を実施する設備の割合" if i == 0 else "")
        st.session_state["user_input"][num_key] = st.number_input(num_key, value=50.0 if i == 0 else None, min_value=0.0, step=1.0)
        st.session_state["user_input"][unit_key] = st.text_input(unit_key, "%" if i == 0 else "")

    # 規定値 3つを個別に配置
    predefined_values = [
        ("電気の排出係数", 0.000434, "t-CO2/kWh", "・環境省令和5年：0.000434(t-CO2/kWh)\nhttps://ghg-santeikohyo.env.go.jp/files/calc/r05_coefficient_rev4.pdf\n\n・環境省：0.000488(t-CO2/kWh)\n環境省のエクセル"),
        ("電気料金", 22.97, "円/kWh", "・新電力ネット(高圧)22.97(円/kWh)\nhttps://pps-net.org/unit\n\n・環境省：12.1587 (円/kWh)\n環境省のエクセル"),
        ("想定稼働年数", 10, "年", "")
    ]

    for name, value, unit, description in predefined_values:
        st.subheader(f"規定値: {name}")
        st.session_state["user_input"][f"規定値_{name}_名前"] = st.text_input(f"規定値 {name} の名前", value=name)
        st.session_state["user_input"][f"規定値_{name}_数字"] = st.number_input(
            f"規定値 {name} の数字",
            min_value=0.0,
            step=0.000001 if name == "電気の排出係数" else 0.01,
            format="%.6f" if name == "電気の排出係数" else "%.2f",
            value=float(value)
        )
        st.session_state["user_input"][f"規定値_{name}_単位"] = st.text_input(f"規定値 {name} の単位", value=unit)
        st.session_state["user_input"][f"規定値_{name}_説明"] = st.text_area(f"規定値 {name} の説明", value=description)

     # 燃料ごとの排出係数データ
    emission_factors = {
        "都市ガス": ("都市ガスの排出係数", 0.00223, "t-CO2/㎥", "https://www.env.go.jp/nature/info/onsen_ondanka/h23-2/ref02.pdf"),
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

    # **追加の規定値 13個**
    for i in range(13):
        st.subheader(f"規定値 {i+1}")
        if i == 1:
            fuel = st.session_state["user_input"]["燃料"]
            name, value, unit, description = emission_factors.get(fuel, ("", None, "", ""))
            value_format = "%.6f"
        else:
            name, value, unit, description = "", None, "", ""
            value_format = "%.2f"
        
        st.session_state["user_input"][f"規定値{i+1}_名前"] = st.text_input(f"規定値 {i+1} の名前", value=name)
        st.session_state["user_input"][f"規定値{i+1}_数字"] = st.number_input(f"規定値 {i+1} の数字", min_value=0.0, step=0.000001 if i == 1 else 0.01, format=value_format, value=value if value is not None else 0.0)
        st.session_state["user_input"][f"規定値{i+1}_単位"] = st.text_input(f"規定値 {i+1} の単位", value=unit)
        st.session_state["user_input"][f"規定値{i+1}_説明"] = st.text_area(f"規定値 {i+1} の説明", value=description)

    # **推測値テンプレートの選択**
    prediction_template = st.selectbox("推測値のテンプレはどれを使用しますか？", ["1(容量推測)", "2(台数推測)", "3(自由入力)"])
    st.session_state["user_input"]["推測値のテンプレ"] = prediction_template

    if st.button("次へ"):
        if prediction_template.startswith("1"):
            next_page("page3A")
        elif prediction_template.startswith("2"):
            next_page("page3B")
        else:
            next_page("page3C")

    # if st.button("完了"):
    #     next_page("summary")


elif st.session_state["page"] == "page2B":
    st.title("フォーム入力 - Step 2B (設備投資系)")
    input_value = st.text_area("設備投資の詳細を入力してください")
    st.session_state["user_input"]["設備投資詳細"] = input_value

    if st.button("完了"):
        next_page("summary")

elif st.session_state["page"] == "page2C":
    st.title("フォーム入力 - Step 2C (燃料転換系_1)")
    input_value = st.text_area("燃料転換（第一種）の詳細を入力してください")
    st.session_state["user_input"]["燃料転換1詳細"] = input_value

    if st.button("完了"):
        next_page("summary")

elif st.session_state["page"] == "page2D":
    st.title("フォーム入力 - Step 2D (燃料転換系_2)")
    input_value = st.text_area("燃料転換（第二種）の詳細を入力してください")
    st.session_state["user_input"]["燃料転換2詳細"] = input_value

    if st.button("完了"):
        next_page("summary")

elif st.session_state["page"] == "page2E":
    st.title("フォーム入力 - Step 2E (自由入力)")
    input_value = st.text_area("自由入力の詳細を記入してください")
    st.session_state["user_input"]["自由入力詳細"] = input_value

    if st.button("完了"):
        next_page("summary")

# ** 2ページ目F (緑施策) **
elif st.session_state["page"] == "page2F":
    st.title("フォーム入力 - Step 2F (緑施策)")
    input_value = st.text_area("緑施策の詳細を入力してください")
    st.session_state["user_input"]["緑施策詳細"] = input_value

    if st.button("完了"):
        next_page("summary")

elif st.session_state["page"] == "page3A":
    st.title("容量推測入力")
    st.text_area("容量推測の詳細を入力してください")
    if st.button("次へ"):
        next_page("summary")

elif st.session_state["page"] == "page3B":
    st.title("台数推測入力")
    st.text_area("台数推測の詳細を入力してください")
    if st.button("次へ"):
        next_page("summary")

elif st.session_state["page"] == "page3C":
    st.title("自由入力")
    st.text_area("自由入力の詳細を入力してください")
    if st.button("次へ"):
        next_page("summary")

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



