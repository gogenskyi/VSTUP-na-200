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

    # Ітеруємося безпосередньо по рядках таблиці <tr>
    for tr in soup.find_all("tr"):
        a = tr.find("a", href=True)
        if not a:
            continue

        href = a.get("href", "")

        if "/rate2026/direction/" not in href:
            continue

        name = a.get_text(" ", strip=True)

        if not name or name.isdigit():
            continue

        cells = tr.find_all("td")

        if len(cells) < 6:
            continue

        okr = (
            cells[0]
            .get_text(" ", strip=True)
            .upper()
            .replace(" ", "")
        )

        if okr != "Б":
            continue

        direction_url = BASE_URL + href

        directions.append({
            "name": name,
            "url": direction_url,
            "budget_places": parse_int(
                cells[2].get_text(" ", strip=True)
            ),
            "max_places": parse_int(
                cells[3].get_text(" ", strip=True)
            ),
            "contract_places": parse_int(
                cells[4].get_text(" ", strip=True)
            ),
            "applications_count": parse_int(
                cells[5].get_text(" ", strip=True)
            )
        })

    return directions