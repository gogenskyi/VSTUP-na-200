import json
import sqlite3
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


# =========================
# INIT DB
# =========================

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS universities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        region_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        url TEXT,

        FOREIGN KEY(region_id)
            REFERENCES regions(id),

        UNIQUE(region_id, name)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS directions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    university_id INTEGER NOT NULL,

    name TEXT NOT NULL,
    url TEXT,
    form TEXT,

    speciality_code TEXT,
    speciality_name TEXT,

    field_code TEXT,
    field_name TEXT,

    budget_places INTEGER DEFAULT 0,
    max_places INTEGER DEFAULT 0,
    contract_places INTEGER DEFAULT 0,
    applications_count INTEGER DEFAULT 0,

    FOREIGN KEY(university_id)
        REFERENCES universities(id),

    UNIQUE(university_id, name)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        person_key TEXT NOT NULL UNIQUE,

        full_name TEXT NOT NULL,

        quota INTEGER DEFAULT 0,

        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        applicant_id INTEGER NOT NULL,
        direction_id INTEGER NOT NULL,

        rank INTEGER,
        priority INTEGER,

        score REAL,

        status TEXT,
        quota INTEGER DEFAULT 0,

        FOREIGN KEY(applicant_id)
            REFERENCES applicants(id),

        FOREIGN KEY(direction_id)
            REFERENCES directions(id),

        UNIQUE(applicant_id, direction_id)
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_applications_direction
    ON applications(direction_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_applications_applicant
    ON applications(applicant_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_directions_speciality
    ON directions(speciality_code)
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

def insert_university(cur, region_id, name, url):
    cur.execute("""
        SELECT id
        FROM universities
        WHERE region_id = ? AND name = ?
    """, (region_id, name))

    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("""
        INSERT INTO universities (
            region_id,
            name,
            url
        )
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

def insert_direction(
    cur,
    university_id,
    name,
    url,
    form,
    budget_places=0,
    max_places=0,
    contract_places=0,
    applications_count=0
):
    speciality_code, speciality_name, field_code, field_name = (
        extract_speciality_info(name)
    )

    cur.execute("""
        SELECT id
        FROM directions
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
            field_name,
            budget_places,
            max_places,
            contract_places,
            applications_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        university_id,
        name,
        url,
        form,
        speciality_code,
        speciality_name,
        field_code,
        field_name,
        budget_places,
        max_places,
        contract_places,
        applications_count
    ))

    return cur.lastrowid
