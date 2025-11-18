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
    "Class Annual Survey", "Annual Survey", "Class Intermediate Survey", "Intermediate Survey",
    "Special Survey", "Class Special Survey", "Continuous Survey", "Main class annual",
    "Main class intermediate", "Main class renewal", "Annual Automation Survey", "Annual Hull Survey",
    "Annual Machinery Survey", "Special Continuous Survey", "Special Periodical Survey",
    "Drydocking Survey", "Boiler Survey", "Auxiliary Boiler", "Screwshaft Survey", "Propeller Shaft",
    "Tailshaft Survey", "Tail Shaft", "Propeller Shaft Condition Monitoring", "Propeller Shaft Survey",
    "Machinery items", "Hull items", "Cargo Gear Load Test", "BTS", "LL Annual Survey", "SC Annual Survey", "SE Annual Survey", "IAPP Annual Survey", "Iopp Annual Survey", "BWM Annual Survey"
]
CR_LOCATIONS = [
    "Xiamen", "Shenzhen", "Shanghai", "Keelung", "Kaohsiung", "Qingdao", "Tianjin",
    "Dalian", "Fuzhou", "Zhoushan", "Ningbo", "Hong Kong", "Taichung", "Tainan"
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

def remove_location_from_name(name):
    pat = r"\b(" + "|".join(re.escape(loc) for loc in CR_LOCATIONS) + r")\b"
    return re.sub(pat, '', name).replace("  ", " ").strip()

def get_lines_from_pdf(pdf_path):
    lines = []
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            lines += txt.splitlines()
    return lines

def extract_due_dates_cr_ccs(lines):
    due_items, seen = [], set()
    for line in lines:
        if any(kw.lower() in line.lower() for kw in MAJOR_KEYWORDS):
            dates = re.findall(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})", line)
            namepure = remove_dates_from_name(line)
            nameclean = remove_location_from_name(namepure)
            if len(dates) >= 1:
                due_date = parse_date(dates[-1])
                if due_date and is_major_check_item(nameclean) and len(nameclean) > 2:
                    key = (nameclean, due_date, "")
                    if key not in seen:
                        seen.add(key)
                        due_items.append((nameclean, due_date, ""))
    return due_items

def extract_due_dates_abs(lines):
    due_items, seen = [], set()
    prev_name = ""
    for i, line in enumerate(lines):
        has_major = any(kw.lower() in line.lower() for kw in MAJOR_KEYWORDS)
        # Range區間：抓日期數以2為單位處理（DUE + RANGE），如有就組成文字
        dates = re.findall(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4})", line)
        if has_major and len(dates) == 2:
            namepure = remove_dates_from_name(line)
            due_date = parse_date(dates[0])
            range_start = dates[0]
            range_end = dates[1]
            if due_date and is_major_check_item(namepure) and len(namepure) > 2:
                rangedisp = f"{range_start} ~ {range_end}"
                key = (namepure, due_date, rangedisp)
                if key not in seen:
                    seen.add(key)
                    due_items.append((namepure, due_date, rangedisp))
            prev_name = line.strip()
        elif has_major and len(dates) == 1:
            namepure = remove_dates_from_name(line)
            due_date = parse_date(dates[0])
            if due_date and is_major_check_item(namepure) and len(namepure) > 2:
                key = (namepure, due_date, "")
                if key not in seen:
                    seen.add(key)
                    due_items.append((namepure, due_date, ""))
            prev_name = line.strip()
        elif has_major:
            prev_name = line.strip()
        elif prev_name and len(dates) == 1:
            namepure = remove_dates_from_name(prev_name)
            due_date = parse_date(dates[0])
            if due_date and is_major_check_item(namepure) and len(namepure) > 2:
                key = (namepure, due_date, "")
                if key not in seen:
                    seen.add(key)
                    due_items.append((namepure, due_date, ""))
    return due_items

def extract_due_dates_default(lines):
    due_items, seen = [],
