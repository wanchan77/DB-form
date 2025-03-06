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
...

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
        measure_type = st.selectbox("施策の種類はどれですか？", ["1(運用改善系)", "2(設備投資系)", "3(燃料転換系_1)", "4(燃料転換系_2)", "5(緑施策)"])
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

# ** 2ページ目 **
elif st.session_state["page"] == "page2A":
    st.title("運用改善系施策式入力")
    input_value = st.text_area("運用改善の詳細を入力してください")
    st.session_state["user_input"]["運用改善詳細"] = input_value

    if st.button("完了"):
        next_page("summary")

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

# ** サマリーページ **
elif st.session_state["page"] == "summary":
    st.title("入力情報確認")
    st.write(st.session_state["user_input"])

    # **Google Sheets にデータを送信**
    if st.button("データを送信"):
        try:
            st.write("\u2705 Google Sheets にデータを追加中...")
            user_data = list(st.session_state["user_input"].values())  # データをリスト化
            sheet.append_row(user_data)  # スプレッドシートにデータを追加
            st.success("\u2705 データをGoogle Sheetsに送信しました！")
        except Exception as e:
            st.error(f"\u274C Google Sheets 書き込みエラー: {e}")


