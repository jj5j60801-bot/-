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
    in_table = False
    survey_col, due_col = None, None
    table_start_keywords = ["Survey Description", "檢驗名稱"]
    due_col_keywords = ["Next Survey Date", "到期日"]
    for i, line in enumerate(lines):
        linetxt = line.replace("　", " ").strip()
        # 判斷CCS/CR主表格
        if any(k in linetxt for k in table_start_keywords) and any(k in linetxt for k in due_col_keywords):
            headers = re.split(r"\s{2,}|\t+", linetxt)
            survey_col, due_col = None, None
            for idx, h in enumerate(headers):
                if any(x in h for x in table_start_keywords):
                    survey_col = idx
                if any(x in h for x in due_col_keywords):
                    due_col = idx
            in_table = True
            continue
        if in_table and (not linetxt or re.match(r"^[A-Za-z ]+Surveys?$", linetxt) or re.match(r"^[A-Za-z ]+:", linetxt)):
            in_table = False
            continue
        # CCS主表格分段抓
        if in_table and survey_col is not None and due_col is not None:
            cols = re.split(r"\s{2,}|\t+", linetxt)
            # Fallback: 若欄不足，補嘗試用1次正則全抓
            if len(cols) > max(survey_col, due_col):
                name, due_str = cols[survey_col].strip(), cols[due_col].strip()
                due_date = parse_date(due_str)
                if due_date and is_meaningful_name(name):
                    key = (name, due_date)
                    if key not in seen:
                        seen.add(key)
                        due_items.append((name, due_date))
            else:
                # 萬一欄位不足，直接正則找該行所有日期，全行唯一項目配最右日期
                date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2}|\d{4}\.\d{2}\.\d{2})")
                dates = list(date_pattern.finditer(linetxt))
                if len(dates) >= 1:
                    due_str = dates[-1][0]
                    text_parts = linetxt.split(due_str)
                    name = text_parts[0].strip() if text_parts else linetxt
                    due_date = parse_date(due_str)
                    if due_date and is_meaningful_name(name):
                        key = (name, due_date)
                        if key not in seen:
                            seen.add(key)
                            due_items.append((name, due_date))
            continue
        # 除了CCS表外也還是保留單行regex fallback
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}-[A-Za-z]{3}-\d{4}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2}|\d{4}\.\d{2}\.\d{2})")
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
