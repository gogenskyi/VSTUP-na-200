import sqlite3

from scraper.crawler.regions import get_regions
from scraper.crawler.universities import get_universities
from scraper.crawler.directions import get_directions
from scraper.crawler.applicants import parse_direction

from database.repository import (
    init_db,
    get_or_create_region,
    insert_university,
    insert_direction
)

from scraper.crawler.applications import insert_applications


def main():
    conn = sqlite3.connect("vstup.db", timeout=30)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    cur = conn.cursor()

    init_db(conn)

    regions = get_regions()

    for region in regions:
        try:
            region_id = get_or_create_region(
                cur,
                region["name"]
            )

            universities = get_universities(
                region["url"]
            )

            for university in universities:

                name = university["name"].lower()

                if "коледж" in name or "ліцей" in name:
                    print(f"SKIP: {university['name']}")
                    continue

                uni_id = insert_university(
                    cur,
                    region_id,
                    university["name"],
                    university["url"]
                )

                directions = get_directions(
                    university["url"]
                )

                for direction in directions:
                    direction_id = insert_direction(
                        cur,
                        uni_id,
                        direction["name"],
                        direction["url"],
                        "денна",
                        direction["budget_places"],
                        direction["max_places"],
                        direction["contract_places"],
                        direction["applications_count"]
                    )

                    applicants = parse_direction(
                        direction["url"]
                    )

                    insert_applications(
                        cur,
                        direction_id,
                        applicants
                    )

                    print(
                        f"{university['name']} | "
                        f"{direction['name']} | "
                        f"БМ={direction['budget_places']} "
                        f"ВМ={direction['max_places']} "
                        f"Контракт={direction['contract_places']} "
                        f"Заяв={direction['applications_count']} | "
                        f"{len(applicants)} applicants"
                    )

                conn.commit()

        except Exception as e:
            print("ERROR:", e)
            conn.rollback()

    conn.close()


if __name__ == "__main__":
    main()
