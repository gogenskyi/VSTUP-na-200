import sqlite3

from scraper.crawler.regions import get_regions
from scraper.crawler.universities import get_universities
from scraper.crawler.directions import get_directions
from scraper.crawler.applicants import parse_direction

from database.repository import (
    get_or_create_region,
    insert_university,
    insert_direction,
    insert_applicants,
    init_db
)


def main():
    conn = sqlite3.connect("vstup.db", timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    cur = conn.cursor()

    init_db(conn)

    regions = get_regions()

    for region in regions:
        try:
            region_id = get_or_create_region(cur, region["name"])

            universities = get_universities(region["url"])

            for university in universities:
                uni_id = insert_university(
                    cur,
                    region_id,
                    university["name"],
                    university["url"]
                )

                directions = get_directions(university["url"])

                for direction in directions:

                    # 1. завжди зберігаємо direction
                    dir_id, field_code = insert_direction(
                        cur,
                        uni_id,
                        direction["name"],
                        direction["url"],
                        "F"
                    )

                    applicants = parse_direction(direction["url"])

                    insert_applicants(cur, dir_id, field_code, applicants)
                    if applicants:
                        print(
                            f"{university['name']} | {direction['name']} -> {len(applicants)}"
                        )

                # commit після кожного університету
                conn.commit()

        except Exception as e:
            print("ERROR:", e)
            conn.rollback()

    conn.close()


if __name__ == "__main__":
    main()