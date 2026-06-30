from bs4 import BeautifulSoup
from scraper.http_client import get_html

BASE_URL = "https://abit-poisk.org.ua"


def get_universities(region_url):
    html = get_html(region_url)

    soup = BeautifulSoup(html, "html.parser")

    universities = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if "/rate2025/univer/" in href:

            universities.append({
                "name": a.get_text(strip=True),
                "url": BASE_URL + href
            })

    return universities
def insert_university(cur, region_id, name, url):
    cur.execute(
        "INSERT INTO universities (region_id, name, url) VALUES (?, ?, ?)",
        (region_id, name, url)
    )
    return cur.lastrowid