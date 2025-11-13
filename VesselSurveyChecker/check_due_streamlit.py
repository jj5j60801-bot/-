import datetime
import re
from PyPDF2 import PdfReader
import streamlit as st
import os

IGNORED_KEYWORDS = [
    "Force MajeureStatus","Status","Not Due","Unknown","Due Range",
    "Survey Manager","Report","ABS","DNV","Airpipe Closing Device","Device Examination"
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
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4})")

    for i, line in enumerate(lines):
        match = date_pattern.search(line)
        if not match:
            continue
        raw_date = match.group(1)
        try:
            try:
                due_date = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                due_date = datetime.datetime.strptime(raw_date, "%d-%b-%Y").date()

            name = lines[i - 1].strip() if i > 0 else "未知項目"
            name = clean_name(name)
            if not is_meaningful_name(name):
                continue

            key = (name, due_date)
            if key not in seen:
                seen.add(key)
                due_items.append((name, due_date))
        except Exception:
            continue

    return due_items

st.title("全船隊PDF檢驗到期查詢")
pdf_folder = "./pdfs"
today = datetime.date.today()
days_limit = st.number_input('列出幾天內到期（例：90）', min_value=1, value=90)

all_results = []
pdf_files = [os.path.join(pdf_folder, f) for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")]

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

if all_results:
    st.dataframe(all_results)
else:
    st.info("所有PDF中無項目即將到期。")

