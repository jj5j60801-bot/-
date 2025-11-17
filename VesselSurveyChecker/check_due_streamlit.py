import datetime
import re
import os
import pandas as pd
from PyPDF2 import PdfReader
import streamlit as st

PASSWORD = "ENGX"
input_pwd = st.text_input("請輸入密碼：", type="password")
if input_pwd != PASSWORD:
    st.warning("請輸入正確密碼")
    st.stop()

MAJOR_KEYWORDS = [
    "Class Annual Survey", "Annual Survey", "Class Intermediate Survey", "Intermediate Survey",
    "Special Survey", "Class Special Survey", "Continuous Survey", "Main class annual",
    "Main class intermediate", "Main class renewal", "Annual Automation Survey", "Annual Hull Survey",
    "Annual Machinery Survey", "Special Continuous Survey", "Special Periodical Survey",
    "Drydocking Survey", "Boiler Survey", "Auxiliary Boiler", "Screwshaft Survey", "Propeller Shaft",
    "Tailshaft Survey", "Tail Shaft", "Propeller Shaft Condition Monitoring", "Propeller Shaft Survey",
    "Machinery items", "Hull items", "Cargo Gear Load Test", "BTS"
]

def parse_date(raw_date):
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d%b%Y", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(raw_date, fmt).date()
        except Exception:
            continue
    return None

def is_major_check_item(name):
    return any(kw.lower() in name.lower() for kw in MAJOR_KEYWORDS)

def remove_dates_from_name(name):
    pat = r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4}|Due Date\s*:\s*\d{2}-[A-Za-z]{3}-\d{4}|Not Due|Due|[-/]|:)"
    return re.sub(pat, '', name).strip()

def extract_due_dates(pdf_path):
    reader = PdfReader(pdf_path)
    lines = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            lines += txt.splitlines()
    due_items = []
    seen = set()
    prev_name = ""
    for i, line in enumerate(lines):
        has_major = any(kw.lower() in line.lower() for kw in MAJOR_KEYWORDS)
        dates = re.findall(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})", line)
        # CR/CCS/WH101格式：同一行同時有主檢查與多個日期
        if has_major and len(dates) >= 1:
            namepure = remove_dates_from_name(line)
            due_date = parse_date(dates[-1])
            if due_date and is_major_check_item(namepure) and len(namepure) > 2:
                key = (namepure, due_date)
                if key not in seen:
                    seen.add(key)
                    due_items.append((namepure, due_date))
            prev_name = line.strip()
            continue
        # ABS/DNV一行主名稱一行日期格式
        if not has_major and len(dates) == 1:
            due_date = parse_date(dates[0])
            namepure = remove_dates_from_name(prev_name)
            if due_date and is_major_check_item(namepure) and len(namepure) > 2:
                key = (namepure, due_date)
                if key not in seen:
                    seen.add(key)
                    due_items.append((namepure, due_date))
        if has_major:
            prev_name = line.strip()
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
        st.info("目前無
