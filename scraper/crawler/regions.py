from bs4 import BeautifulSoup
from scraper.http_client import get_html

BASE_URL = "https://abit-poisk.org.ua"


def get_regions():
    html = get_html(f"{BASE_URL}/rate2026")

    soup = BeautifulSoup(html, "html.parser")

    regions = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if "/rate2026/region/" in href:

            regions.append({
                "name": a.get_text(strip=True),
                "url": BASE_URL + href
            })

    return regions