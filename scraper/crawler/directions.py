import re
from bs4 import BeautifulSoup
from scraper.http_client import get_html

BASE_URL = "https://abit-poisk.org.ua"


def parse_int(text: str) -> int:
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else 0


def get_directions(univer_url: str) -> list[dict]:
    html = get_html(univer_url)

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    directions = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")

        if "/rate2026/direction/" not in href:
            continue

        name = a.get_text(" ", strip=True)

        if not name or name.isdigit():
            continue

        tr = a.find_parent("tr")

        if not tr:
            continue

        cells = tr.find_all("td")

        if len(cells) < 6:
            continue

        # Нормалізуємо ОКР
        okr = (
            cells[0]
            .get_text(" ", strip=True)
            .upper()
            .replace(" ", "")
        )

        # Залишаємо тільки бакалавра після ПЗСО
        if okr != "Б":
            continue
        #print(f"{okr}: {name}")
        direction_info = get_direction_info(
            BASE_URL + href
        )

        directions.append({
            "name": name,
            "url": BASE_URL + href,

            "field_code": direction_info.get("field_code"),
            "field_name": direction_info.get("field_name"),

            "speciality_code": direction_info.get("speciality_code"),
            "speciality_name": direction_info.get("speciality_name"),

            "budget_places": parse_int(cells[2].get_text(" ", strip=True)),
            "max_places": parse_int(cells[3].get_text(" ", strip=True)),
            "contract_places": parse_int(cells[4].get_text(" ", strip=True)),
            "applications_count": parse_int(cells[5].get_text(" ", strip=True))
        })

    return directions

def get_direction_info(direction_url: str) -> dict:
    html = get_html(direction_url)

    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    result = {
        "field_code": None,
        "field_name": None,
        "speciality_code": None,
        "speciality_name": None,
    }

    for line in text.splitlines():
        line = line.strip()

        # Галузь
        if line.startswith("Галузь:"):
            value = line.replace("Галузь:", "").strip()
            # Оновлений regex для цифр і крапок (напр., 12 або 014)
            m = re.match(r"([\d\.]+)\s+(.*)", value) 
            if m:
                result["field_code"] = m.group(1)
                result["field_name"] = m.group(2)

        # Спеціальність
        elif line.startswith("Спеціальність:"):
            value = line.replace("Спеціальність:", "").strip()
            # Оновлений regex для цифр і крапок (напр., 122 або 014.01)
            m = re.match(r"([\d\.]+)\s+(.*)", value)
            if m:
                result["speciality_code"] = m.group(1)
                result["speciality_name"] = m.group(2)

    return result