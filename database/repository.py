import sqlite3
import re
import json
from pathlib import Path
from scraper.utils.specialities import extract_speciality_info
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
        field_code TEXT,   -- NEW

        rank INTEGER,
        name TEXT,
        priority INTEGER,
        score REAL,
        status TEXT,
        quota INTEGER,

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
    name = normalize(direction_name)

    best_spec = None
    best_score = 0

    for spec in SPECIALITIES.values():
        spec_name = normalize(spec["name"])

        score = _score(name, spec_name)

        if score > best_score:
            best_score = score
            best_spec = spec

    if not best_spec or best_score < 0.25:
        return None, None, None, None

    return (
        best_spec["old_code"],
        best_spec["name"],
        best_spec["field_code"],
        best_spec["field_name"]
    )


def _score(text: str, spec: str) -> float:
    text_tokens = set(text.split())
    spec_tokens = set(spec.split())

    if not spec_tokens:
        return 0

    overlap = len(text_tokens & spec_tokens)

    keywords = {
        "електроніка",
        "телекомунікації",
        "приладобудування",
        "радіотехніка",
        "інженерія",
        "техніка",
        "комп'ютер",
        "комп’ютер"
    }

    bonus = len([w for w in text_tokens if w in keywords]) * 0.2

    return overlap / len(spec_tokens) + bonus


# =========================
# DIRECTIONS
# =========================

def insert_direction(cur, university_id, name, url, form):
    speciality_code, speciality_name, field_code, field_name = extract_speciality_info(name)

    cur.execute("""
        SELECT id FROM directions
        WHERE university_id = ? AND name = ?
    """, (university_id, name))

    row = cur.fetchone()
    if row:
        return row[0], field_code

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

    return cur.lastrowid, field_code


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

    match = re.search(r"Пр\.\s*(\d+)", value)
    if match:
        return int(match.group(1))

    match = re.search(r"\d+", value)
    if match:
        return int(match.group())

    if value in {"К", "Б"}:
        return 1

    return None


def extract_quota(row: dict):
    quota = str(row.get("Квота", "")).strip().lower()

    if "квота-1" in quota:
        return 1

    if "квота-2" in quota:
        return 2

    return 0


# =========================
# APPLICANTS
# =========================

def insert_applicants(cur, direction_id, field_code, applicants):
    if not applicants:
        return

    for a in applicants:

        quota = extract_quota(a)

        cur.execute("""
            INSERT INTO applicants (
                direction_id,
                field_code,
                rank,
                name,
                priority,
                score,
                status,
                quota,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(direction_id, name, priority)
            DO UPDATE SET
                rank = excluded.rank,
                score = excluded.score,
                status = excluded.status,
                quota = excluded.quota,
                raw_json = excluded.raw_json,
                field_code = excluded.field_code
        """, (
            direction_id,
            field_code,
            a.get("№"),
            a.get("ПІБ"),
            extract_priority(a.get("П")),
            safe_float(a.get("Заг.бал")),
            a.get("Статус"),
            quota,
            json.dumps(a, ensure_ascii=False)
        ))