import sqlite3
import re
import json

with open("data/specialities.json", encoding="utf-8") as f:
    SPECIALITIES = json.load(f)
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
# DIRECTIONS
# =========================

def insert_direction(
    cur,
    university_id,
    name,
    url,
    form
):
    code = extract_speciality_code(name)

    field_code, field_name = get_field_by_code(code)

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

def extract_speciality_code(name: str):
    match = re.search(r"\d{3}", name)
    return match.group(0) if match else None
def get_field_by_code(code: str):
    spec = SPECIALITIES.get(code)
    if not spec:
        return None, None

    return spec["field_code"], spec["field_name"]
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
def safe_float(value):
    try:
        return float(value)
    except:
        return None

    

def extract_priority(value):
    if not value:
        return None

    match = re.search(r"\d+", value)
    return int(match.group()) if match else None

