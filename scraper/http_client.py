import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_html(url: str) -> str:
    response = session.get(
        url,
        headers=HEADERS,
        timeout=30,
        verify=False
    )

    response.raise_for_status()
    return response.text