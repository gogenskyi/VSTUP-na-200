import sqlite3
import re
import json
from pathlib import Path

# =========================
# PATHS + LOAD DATA
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
SPECIALITIES_FILE = BASE_DIR / "data" / "specialities.json"

with open(SPECIALITIES_FILE, encoding="utf-8") as f:
    SPECIALITIES = json.load(f)


# =========================
# NORMALIZATION
# =========================

def normalize(text: str) -> str:
    return (
        text.lower()
        .replace("’", "'")
        .replace("ʼ", "'")
        .replace("`", "'")
        .strip()
    )


SPECIALITIES_BY_NAME = {
    normalize(v["name"]): v
    for v in SPECIALITIES.values()
}


# =========================
# INIT DB
# =========================

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS universities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_id INTEGER,
        name TEXT,
        url TEXT,
        UNIQUE(region_id, name)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS directions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        university_id INTEGER,

        name TEXT,
        url TEXT,
        form TEXT,

        speciality_code TEXT,
        speciality_name TEXT,

        field_code TEXT,
        field_name TEXT,

        UNIQUE(university_id, name)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction_id INTEGER,
        rank INTEGER,
        name TEXT,
        priority INTEGER,
        score REAL,
        status TEXT,
        raw_json TEXT,
        UNIQUE(direction_id, name, priority)
    )
    """)

    conn.commit()


# =========================
# REGIONS
# =========================

def get_or_create_region(cur: sqlite3.Cursor, name: str) -> int:
    cur.execute("SELECT id FROM regions WHERE name = ?", (name,))
    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("INSERT INTO regions (name) VALUES (?)", (name,))
    return cur.lastrowid


# =========================
# UNIVERSITIES
# =========================

def insert_university(cur: sqlite3.Cursor, region_id: int, name: str, url: str) -> int:
    cur.execute("""
        SELECT id FROM universities
        WHERE region_id = ? AND name = ?
    """, (region_id, name))

    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("""
        INSERT INTO universities (region_id, name, url)
        VALUES (?, ?, ?)
    """, (region_id, name, url))

    return cur.lastrowid


# =========================
# SPECIALITY MATCHING
# =========================

def get_speciality_info(direction_name: str):
    name_norm = normalize(direction_name)

    best_match = None
    best_score = 0

    for spec in SPECIALITIES_BY_NAME.values():
        spec_name = normalize(spec["name"])

        # рахуємо простий overlap score
        score = _match_score(name_norm, spec_name)

        if score > best_score:
            best_score = score
            best_match = spec

    # поріг щоб не ловити сміття
    if best_score < 0.35:
        return None, None, None, None

    return (
        best_match["old_code"],
        best_match["name"],
        best_match["field_code"],
        best_match["field_name"]
    )

def _match_score(text: str, spec: str) -> float:
    text_tokens = set(text.split())
    spec_tokens = set(spec.split())

    if not spec_tokens:
        return 0

    intersection = text_tokens.intersection(spec_tokens)

    return len(intersection) / len(spec_tokens)

# =========================
# DIRECTIONS
# =========================

def insert_direction(
    cur,
    university_id,
    name,
    url,
    form
):
    speciality_code, speciality_name, field_code, field_name = get_speciality_info(name)

    if field_code is None:
        print("NOT MATCHED SPECIALITY:", name)

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
            speciality_code,
            speciality_name,
            field_code,
            field_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        university_id,
        name,
        url,
        form,
        speciality_code,
        speciality_name,
        field_code,
        field_name
    ))

    return cur.lastrowid


# =========================
# APPLICANTS HELPERS
# =========================

def safe_float(value):
    try:
        return float(value)
    except:
        return None


def extract_priority(value):
    if not value:
        return None

    value = str(value).strip()

    # 1) стандартний формат "Пр. 3 (К)"
    match = re.search(r"Пр\.\s*(\d+)", value)
    if match:
        return int(match.group(1))

    # 2) просто число всередині рядка
    match = re.search(r"\d+", value)
    if match:
        return int(match.group())

    # 3) якщо є тільки "К", "Б" і т.д. — даємо дефолт
    if value in {"К", "Б"}:
        return 1

    return None


# =========================
# APPLICANTS
# =========================

def insert_applicants(cur, direction_id, applicants):
    if not applicants:
        return

    cur.executemany("""
        INSERT OR IGNORE INTO applicants
        (direction_id, rank, name, priority, score, status, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            direction_id,
            int(a.get("№")) if a.get("№") else None,
            a.get("ПІБ"),
            extract_priority(a.get("П")),
            safe_float(a.get("Заг.бал")),
            a.get("Статус"),
            str(a)
        )
        for a in applicants
    ])