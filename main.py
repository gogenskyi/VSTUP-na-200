import csv
import os

from scraper.crawler.regions import get_regions
from scraper.crawler.universities import get_universities
from scraper.crawler.directions import get_directions
from scraper.crawler.applicants import parse_direction

os.makedirs("data", exist_ok=True)

regions = get_regions()

for region in regions:

    universities = get_universities(region["url"])

    for university in universities:

        directions = get_directions(university["url"])

        for direction in directions:

            applicants = parse_direction(direction["url"])

            #print(direction["name"], len(applicants))

            if not applicants:
                continue

            # безпечна назва файлу
            filename = (
                direction["name"]
                .replace("/", "_")
                .replace("\\", "_")
                .replace(":", "_")
                .replace("|", "_")
            )

            filepath = os.path.join("data", f"{filename}.csv")

            headers = list(applicants[0].keys())

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)

                writer.writeheader()
                writer.writerows(applicants)