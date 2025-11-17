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

IGNORED_KEYWORDS = [
    "Force MajeureStatus", "Status", "Not Due", "Unknown", "Due Range",
    "Survey Manager", "Report", "ABS", "DNV", "Airpipe Closing Device", "Device Examination"
]

def clean_name(name):
    name = re.sub(r"\d{1,2}-[A-Za-z]{3}-\d{4}", "", name)
    name = re.sub(r"\d{4}-\d{2}-\d{2}", "", name)
    name = re.sub(r"[-]{1,}|\s{2,}", " ", name)
    name = re.sub(r"\b[Dd]ue\b$", "", name)
    name = re.sub(r"\bNot Due\b$", "", name)
    name = re.sub(r"\s*\d{1,2}\s*$", "", name)
    return name.strip()

def is_meaningful_name(name):
    if not name.strip():
        return False
    if "Not" in name:
        return False
    for kw in IGNORED_KEYWORDS:
        if kw.lower() in name.lower():
            return False
    if re.match(r"^[0-9\- ]+$", name.strip()):
        return False
    if len(name.split()) > 0 and name.split()[0].isdigit():
        return False
    return True

def parse_date(raw_date):
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d%b%Y", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(raw_date, fmt).date()
        except Exception:
            continue
    return None

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
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2}|\d{2}[A-Z]{3}\d{4}|\d{4}\.\d{2}\.\d{2})")

    in_cr_table = False
    cr_table_headers = ["Survey Description", "Next Survey Date", "到期日"]
    for i, line in enumerate(lines):
        if any(header in line for header in cr_table_headers):
            in_cr_table = True
            continue

        # CR/CCS表格主體專屬解法，直至遇到空列或其他大標
        if in_cr_table:
            if not line.strip() or re.match(r"^[A-Za-z].*:$", line):
                in_cr_table = False
                continue
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) >= 3:
                name = cols[0].strip()
                # 盡量抓最右的日期欄(Next Survey/到期日)
                for idx in range(2, len(cols)):
                    due_val = cols[idx].strip()
                    due_date = parse_date(due_val)
                    if due_date and is_meaningful_name(name):
                        key = (name, due_date)
                        if key not in seen:
                            seen.add(key)
                            due_items.append((name, due_date))
                        break
            continue

        # 傳統格式匹配
        matches = list(date_pattern.finditer(line))
        for match in matches:
            raw_date = match.group(1)
            due_date = parse_date(raw_date)
            name = lines[i-1].strip() if i > 0 else "未知項目"
            name = clean_name(name)
            if due_date and is_meaningful_name(name):
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

# 主分類名稱（已符合你圖片細項+常見CCS/CR格式）
main_keywords = [
    "Class Annual Survey", "Class Intermediate Survey", "Class Special Survey",
    "Continuous Survey", "BTS", "Screwshaft Survey", "Boiler Survey", "Tailshaft Survey", "Propeller Shaft",
    "Annual", "Special", "Periodical", "Intermediate", "Continuous", "Boiler", "Tailshaft"
]
main_df = df[df["項目名稱"].str.contains("|".join(main_keywords), case=False, na=False)]

vessel_names = sorted(set(name.replace('.pdf', '') for name in main_df["檔案"].unique()))

st.markdown("#### 檢驗到期船舶：")
if vessel_names:
    for name in vessel_names:
        st.markdown(f"- {name}")
    selected_vessel = st.selectbox("請選擇船舶檔案（只顯示到期船名）", vessel_names)
    real_vessel_file = selected_vessel + ".pdf"
    vessel_df = main_df[main_df["檔案"] == real_vessel_file]
    if not vessel_df.empty:
        st.subheader(f"{selected_vessel} 檢驗到期明細 (主分類)")
        st.dataframe(vessel_df)
else:
    st.info("目前無任何船舶到期檢驗。")
