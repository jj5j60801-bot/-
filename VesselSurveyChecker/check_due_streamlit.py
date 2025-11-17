import datetime
import re
import os
import pandas as pd
from PyPDF2 import PdfReader
import streamlit as st

PASSWORD = "yourpassword123"
input_pwd = st.text_input("請輸入密碼：", type="password")
if input_pwd != PASSWORD:
    st.warning("請輸入正確密碼")
    st.stop()

MAJOR_KEYWORDS = [
    "Class Annual Survey", "Class Intermediate Survey", "Class Special Survey",
    "Continuous Survey", "Boiler Survey", "Tailshaft Survey",
    "Screwshaft Survey", "Propeller Shaft"
]

def parse_date(raw_date):
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d%b%Y", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(raw_date, fmt).date()
        except Exception:
            continue
    return None

def is_major_check_item(name):
    return any(name.strip().startswith(kw) for kw in MAJOR_KEYWORDS)

def extract_due_dates(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            text += txt + "\n"
    lines = text.splitlines()
    due_items = []
    seen = set()
    prev_name = ""
    for line in lines:
        for kw in MAJOR_KEYWORDS:
            if line.strip().startswith(kw):
                prev_name = line.strip()
                break  # 只要命中主名稱開頭即設定
        for match in re.finditer(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})", line):
            due_date = parse_date(match.group(1))
            name = prev_name
            if due_date and is_major_check_item(name):
                key = (name, due_date)
                if key not in seen:
                    seen.add(key)
                    due_items.append((name, due_date))
    return due_items

st.title("全船隊PDF檢驗到期查詢")

pdf_folder = os.path.join(os.path.dirname(__file__), "pdfs")
today = datetime.date.today()
days_limit = st.number_input('列出幾天內到期（例：90）', min_value=1, value=90)

all_results = []
pdf_files = [
    os.path.join(pdf_folder, f)
    for f in os.listdir(pdf_folder)
    if f.lower().endswith(".pdf")
]

for pdf in pdf_files:
    due_list = extract_due_dates(pdf)
    for name, due_date in due_list:
        days_left = (due_date - today).days
        if 0 <= days_left <= days_limit:
            all_results.append({
                "檔案": os.path.basename(pdf),
                "項目名稱": name,
                "到期日": due_date.strftime("%Y-%m-%d"),
                "剩餘天數": days_left
            })

df = pd.DataFrame(all_results)

if df.empty:
    st.info("未解析出任何到期檢查項目。")
else:
    vessel_names = sorted(set(name.replace('.pdf', '') for name in df["檔案"].unique()))
    st.markdown("#### 檢驗到期船舶：")
    if vessel_names:
        for name in vessel_names:
            st.markdown(f"- {name}")
        selected_vessel = st.selectbox("請選擇船舶檔案（只顯示到期船名）", vessel_names)
        real_vessel_file = selected_vessel + ".pdf"
        vessel_df = df[df["檔案"] == real_vessel_file]
        if not vessel_df.empty:
            st.subheader(f"{selected_vessel} 檢驗到期明細 (主分類)")
            st.dataframe(vessel_df)
        else:
            st.info("此船未找到符號主分類的項目。")
    else:
        st.info("目前無任何船舶到期檢驗。")
