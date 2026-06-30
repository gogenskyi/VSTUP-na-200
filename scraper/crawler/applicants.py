from bs4 import BeautifulSoup
from scraper.http_client import get_html


def parse_direction(direction_url):
    html = get_html(direction_url)
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        return []

    headers = [
        th.get_text(strip=True)
        for th in table.find_all("th")
    ]

    rows = []

    for tr in table.find_all("tr")[1:]:
        cols = [
            td.get_text(" ", strip=True)
            for td in tr.find_all("td")
        ]

        if cols and len(cols) == len(headers):
            rows.append(dict(zip(headers, cols)))

    return rows