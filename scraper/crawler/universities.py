from bs4 import BeautifulSoup
from scraper.http_client import get_html

BASE_URL = "https://abit-poisk.org.ua"


def get_universities(region_url: str) -> list[dict]:
    html = get_html(region_url)

    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    universities = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")

        if "/rate2025/univer/" not in href:
            continue

        name = a.get_text(" ", strip=True)

        if not name:
            continue

        full_url = BASE_URL + href

        if full_url in seen:
            continue

        seen.add(full_url)

        universities.append({
            "name": name,
            "url": full_url
        })

    return universities