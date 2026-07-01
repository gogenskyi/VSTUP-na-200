from bs4 import BeautifulSoup
from scraper.http_client import get_html
import re
import json

BASE_URL = "https://abit-poisk.org.ua"

with open("data/specialities.json", encoding="utf-8") as f:
    SPECIALITIES = json.load(f)

def normalize_text(text: str) -> str:
    return " ".join(text.split())


def get_directions(univer_url):
    html = get_html(univer_url)
    soup = BeautifulSoup(html, "html.parser")

    directions = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/rate2025/direction/" not in href:
            continue

        name = normalize_text(" ".join(a.stripped_strings))

        # пропускаємо чисті числа типу "192", "376"
        if name.isdigit():
            continue

        directions.append({
            "name": name,
            "url": BASE_URL + href
        })

    return directions


def extract_direction_id(url: str):
    match = re.search(r"/direction/(\d+)", url)
    return match.group(1) if match else None

def extract_speciality_code(name: str):
    """
    шукає F3, D8, G12 і т.д.
    """
    match = re.search(r"\b([A-Z]\d{1,2})\b", name)
    return match.group(1) if match else None

def get_field_by_code(code: str):
    if not code:
        return None, None

    spec = SPECIALITIES.get(code)

    if not spec:
        return None, None

    return spec["field_code"], spec["field_name"]

def insert_direction(cur, university_id, name, url, form):

    code = extract_speciality_code(name)
    field_code, field_name = get_field_by_code(code)

    # якщо вже є — не дублюємо
    cur.execute("""
        SELECT id FROM directions
        WHERE university_id = ? AND name = ?
    """, (university_id, name))

    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("""
        INSERT INTO directions (
            university_id,
            name,
            url,
            form,
            field_code,
            field_name
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        university_id,
        name,
        url,
        form,
        field_code,
        field_name
    ))

    return cur.lastrowid