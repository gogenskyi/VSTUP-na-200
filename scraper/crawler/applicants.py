import json
import re
from bs4 import BeautifulSoup
from scraper.http_client import get_html
# ========================= # PARSE # =========================

def parse_direction(direction_url):
    html = get_html(direction_url)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cols = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cols) == len(headers): rows.append(dict(zip(headers, cols)))
    return rows

def extract_applicant_name(value):
    if not value:
        return ""

    value = str(value).strip()

    # номер рейтингу
    value = re.sub(r"^\d+\s+", "", value)

    # код абітурієнта
    value = re.sub(r"^\d{2}-\d+\s*", "", value)

    # пріоритет
    value = re.sub(r"\s+Пр\.\s*\d+.*$", "", value)

    return value.strip()

def build_person_key(row):
    raw_name = row.get("ПІБ", "")

    code = extract_applicant_code(raw_name)

    if code:
        return f"code:{code}"

    return f"name:{extract_applicant_name(raw_name)}"

def extract_applicant_code(value):
    m = re.search(r"(\d{2}-\d+)", value or "")
    return m.group(1) if m else None

def extract_quota(row):
    quota = str(row.get("Квота", "")).lower()

    if "квота-1" in quota:
        return 1

    if "квота-2" in quota:
        return 2

    return 0

def build_person_key(row):
    raw_name = row.get("ПІБ", "")

    code = extract_applicant_code(raw_name)

    if code:
        return f"code:{code}"

    name = extract_applicant_name(raw_name)

    subjects = row.get("Складові заг. балу", "")

    numbers = re.findall(r"\b\d{3}\b", subjects)

    if numbers:
        return f"name:{name}|{'-'.join(numbers[:4])}"

    return f"name:{name}"

def get_or_create_applicant(cur, row):
    person_key = build_person_key(row)

    full_name = extract_applicant_name(
        row.get("ПІБ")
    )

    quota = extract_quota(row)

    cur.execute("""
        INSERT INTO applicants (
            person_key,
            full_name,
            quota,
            raw_json
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(person_key)
        DO UPDATE SET
            quota = excluded.quota,
            raw_json = excluded.raw_json
    """, (
        person_key,
        full_name,
        quota,
        json.dumps(row, ensure_ascii=False)
    ))

    cur.execute("""
        SELECT id
        FROM applicants
        WHERE person_key = ?
    """, (person_key,))

    return cur.fetchone()[0]