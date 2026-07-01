import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SPECIALITIES_FILE = BASE_DIR / "data" / "specialities.json"

with open(SPECIALITIES_FILE, encoding="utf-8") as f:
    SPECIALITIES = json.load(f)


def normalize(text: str) -> str:
    return (
        text.lower()
        .replace("’", "'")
        .replace("`", "'")
        .replace("ʼ", "'")
        .strip()
    )


def extract_speciality_info(direction_name: str):
    text = normalize(direction_name)

    # 1. пошук коду типу F3, G21 ...
    m = re.search(r"\b([A-Z]{1,2}\d{1,2})\b", direction_name)

    if m:
        code = m.group(1)

        if code in SPECIALITIES:
            return _pack(SPECIALITIES[code])

    # 2. назва спеціальності є підрядком
    for spec in SPECIALITIES.values():

        spec_name = normalize(spec["name"])

        if spec_name in text:
            return _pack(spec)

    # 3. token matching
    best = None
    best_score = 0

    text_tokens = set(re.findall(r"\w+", text))

    for spec in SPECIALITIES.values():

        spec_tokens = set(
            re.findall(r"\w+", normalize(spec["name"]))
        )

        if not spec_tokens:
            continue

        overlap = len(text_tokens & spec_tokens)

        score = overlap / len(spec_tokens)

        if score > best_score:
            best_score = score
            best = spec

    if best_score >= 0.5:
        return _pack(best)

    return None, None, None, None


def _pack(spec: dict):
    return (
        spec.get("old_code"),
        spec.get("name"),
        spec.get("field_code"),
        spec.get("field_name"),
    )