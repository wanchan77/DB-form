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
...

# ** 2ページ目 **
elif st.session_state["page"] == "page2A":
    st.title("フォーム入力 - Step 2A (運用改善系)")
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

# ** サマリーページ **
elif st.session_state["page"] == "summary":
    st.title("入力内容の確認")
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


