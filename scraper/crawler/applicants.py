import json
import re
from bs4 import BeautifulSoup
from scraper.http_client import get_html


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

        if len(cols) == len(headers):
            rows.append(dict(zip(headers, cols)))

    return rows


# -------------------------
# HELPERS
# -------------------------

def extract_priority(value):
    if not value:
        return None

    value = str(value)

    m = re.search(r"Пр\.\s*(\d+)", value)
    if m:
        return int(m.group(1))

    m = re.search(r"\d+", value)
    if m:
        return int(m.group())

    return None


def extract_quota(row):
    q = str(row.get("Квота", "")).lower()

    if "квота-1" in q:
        return 1
    if "квота-2" in q:
        return 2

    return 0


def safe_float(v):
    try:
        return float(v)
    except:
        return None


# -------------------------
# INSERT
# -------------------------

def insert_applicants(cur, direction_code, applicants):
    for a in applicants:

        cur.execute("""
            INSERT INTO applicants (
                direction_code,
                rank,
                name,
                priority,
                score,
                status,
                quota,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(direction_code, name, priority)
            DO UPDATE SET
                rank=excluded.rank,
                score=excluded.score,
                status=excluded.status,
                quota=excluded.quota,
                raw_json=excluded.raw_json
        """, (
            direction_code,
            a.get("№"),
            a.get("ПІБ"),
            extract_priority(a.get("П")),
            safe_float(a.get("Заг.бал")),
            a.get("Статус"),
            extract_quota(a),
            json.dumps(a, ensure_ascii=False)
        ))