from bs4 import BeautifulSoup
from scraper.http_client import get_html

BASE_URL = "https://abit-poisk.org.ua"


def get_directions(univer_url: str) -> list[dict]:
    html = get_html(univer_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    directions = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/rate2025/direction/" not in href:
            continue

        name = " ".join(a.stripped_strings).strip()

        if not name or name.isdigit():
            continue

        directions.append({
            "name": name,
            "url": BASE_URL + href
        })

    return directions