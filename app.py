import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# === Google Sheets 接続設定 ===
st.write("✅ 認証情報をロード中...")

# secrets から Google 認証情報を取得（明示的に dict に変換）
credentials_info = dict(st.secrets["google_sheets"])

# private_key の改行を適切に処理
credentials_info["private_key"] = credentials_info["private_key"].replace("\\n", "\n")

st.write("✅ 認証情報の形式: ", type(credentials_info))
st.write("✅ private_key の長さ: ", len(credentials_info["private_key"]))
st.write("✅ private_key の先頭50文字: ", credentials_info["private_key"][:50])
st.write("✅ private_key の最後の50文字: ", credentials_info["private_key"][-50:])

# 認証を作成
try:
    creds = Credentials.from_service_account_info(credentials_info)
    client = gspread.authorize(creds)
    st.write("✅ Google Sheets に接続完了！")
except Exception as e:
    st.error(f"❌ 認証エラー: {e}")


# === ページ管理のためのセッション変数を初期化 ===
if "page" not in st.session_state:
    st.session_state["page"] = "page1"

if "user_input" not in st.session_state:
    st.session_state["user_input"] = {}

# ページ遷移関数
def next_page(next_page_name):
    st.session_state["page"] = next_page_name

# ** 1ページ目 **
if st.session_state["page"] == "page1":
    st.title("フォーム入力 - Step 1")

    scope = st.selectbox("どのScopeですか？", ["Scope1", "Scope2"])
    st.session_state["user_input"]["Scope"] = scope

    if scope == "Scope1":
        equipment_options = ["ボイラー", "発電機", "その他"]
        fuel_options = ["石炭", "LNG", "重油"]
    else:
        equipment_options = ["空調", "照明", "その他"]
        fuel_options = ["電気", "太陽光", "その他"]

    equipment = st.selectbox("どの設備の施策ですか？", equipment_options)
    st.session_state["user_input"]["設備"] = equipment

    fuel = st.selectbox("どの燃料ですか？", fuel_options)
    st.session_state["user_input"]["燃料"] = fuel

    formula_template = st.selectbox("式はテンプレですか？", ["1", "2", "3", "4", "5"])
    st.session_state["user_input"]["テンプレ"] = formula_template

    if st.button("次へ"):
        if formula_template in ["1", "2"]:
            next_page("page2A")
        elif formula_template in ["3", "4"]:
            next_page("page2B")
        else:
            next_page("page2C")

# ** 2ページ目A **
elif st.session_state["page"] == "page2A":
    st.title("フォーム入力 - Step 2A")
    input_value = st.text_input("追加の入力をしてください")
    st.session_state["user_input"]["追加入力"] = input_value

    if st.button("完了"):
        next_page("summary")

# ** 2ページ目B **
elif st.session_state["page"] == "page2B":
    st.title("フォーム入力 - Step 2B")
    input_value = st.text_input("詳細を入力してください")
    st.session_state["user_input"]["詳細入力"] = input_value

    if st.button("完了"):
        next_page("summary")

# ** 2ページ目C **
elif st.session_state["page"] == "page2C":
    st.title("フォーム入力 - Step 2C")
    input_value = st.text_area("特別な詳細を記入してください")
    st.session_state["user_input"]["特別入力"] = input_value

    if st.button("完了"):
        next_page("summary")

# ** サマリーページ **
elif st.session_state["page"] == "summary":
    st.title("入力内容の確認")
    st.write(st.session_state["user_input"])

    # **Google Sheets にデータを送信**
    if st.button("データを送信"):
        user_data = list(st.session_state["user_input"].values())  # データをリスト化
        sheet.append_row(user_data)  # スプレッドシートにデータを追加
        st.success("データをGoogle Sheetsに送信しました！")

