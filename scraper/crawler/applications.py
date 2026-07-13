import re

from .applicants import get_or_create_applicant


def safe_float(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def extract_priority(value):
    if value is None:
        return "к"

    value = str(value).strip()

    if value in {"", "-", "—"}:
        return "к"

    match = re.search(r"Пр\.\s*(\d+)", value)
    if match:
        return int(match.group(1))

    match = re.search(r"\d+", value)
    if match:
        return int(match.group())

    return "к"

def extract_quota(row):
    quota = str(row.get("Квота", "")).lower()

    if "квота-1" in quota:
        return 1

    if "квота-2" in quota:
        return 2

    return 0


def insert_application(cur, applicant_id, direction_id, row):
    rank = row.get("№")

    try:
        rank = int(rank)
    except Exception:
        rank = None

    cur.execute("""
        INSERT INTO applications (
            applicant_id,
            direction_id,
            rank,
            priority,
            score,
            status,
            quota
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(applicant_id, direction_id)
        DO UPDATE SET
            rank = excluded.rank,
            priority = excluded.priority,
            score = excluded.score,
            status = excluded.status,
            quota = excluded.quota
    """, (
        applicant_id,
        direction_id,
        rank,
        extract_priority(row.get("П")),
        safe_float(row.get("Заг.бал")),
        row.get("Статус"),
        extract_quota(row)
    ))


def insert_applications(cur, direction_id, applicants):
    for row in applicants:

        applicant_id = get_or_create_applicant(
            cur,
            row
        )

        insert_application(
            cur,
            applicant_id,
            direction_id,
            row
        )