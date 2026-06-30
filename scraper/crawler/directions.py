from bs4 import BeautifulSoup
from scraper.http_client import get_html

BASE_URL = "https://abit-poisk.org.ua"


def get_directions(univer_url):
    html = get_html(univer_url)

    soup = BeautifulSoup(html, "html.parser")

    directions = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if "/rate2025/direction/" in href:

            directions.append({
                "name": a.get_text(strip=True),
                "url": BASE_URL + href
            })

    return directions
def insert_direction(cur, university_id, name, url, category):
    cur.execute(
        "INSERT INTO directions (university_id, name, url, category) VALUES (?, ?, ?, ?)",
        (university_id, name, url, category)
    )
    return cur.lastrowid