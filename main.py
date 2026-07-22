import sqlite3
import time

from scraper.utils.retry import fetch_with_retry
from scraper.crawler.regions import get_regions
from scraper.crawler.universities import get_universities
from scraper.crawler.directions import get_directions
from scraper.crawler.applicants import parse_direction
from scraper.crawler.applications import insert_applications

from database.repository import (
    init_db,
    get_or_create_region,
    insert_university,
    insert_direction
)


def main():
    conn = sqlite3.connect("vstup2026.db", timeout=30)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    cur = conn.cursor()
    init_db(conn)

    # Отримуємо регіони через fetch_with_retry на випадок помилки з'єднання
    try:
        regions = fetch_with_retry(get_regions)
    except Exception as e:
        print(f"КРИТИЧНА ПОМИЛКА: Не вдалося отримати список регіонів -> {e}")
        return

    for region in regions:
        print(f"Починаємо обробку регіону: {region['name']}")
        region_id = get_or_create_region(cur, region["name"])

        try:
            universities = fetch_with_retry(get_universities, region["url"])
        except Exception as e:
            print(f"КРИТИЧНА ПОМИЛКА: Пропускаємо регіон {region['name']} -> {e}")
            continue

        for university in universities:
            name = university["name"].lower()

            skip_words = [
                "коледж", "ліцей", "училище", "навчальний центр",
                "навчально", "міжшкіль", "автомобільна школа",
                "автошкол", "спортивно-техніч", "ресурсний центр",
                "інститут національної академії", "нан україни",
                "філія", "всп", "військова частина", "обленерго",
                "товариства сприяння обороні",
            ]

            if any(word in name for word in skip_words):
                print(f"SKIP: {university['name']}")
                continue

            try:
                uni_id = insert_university(
                    cur,
                    region_id,
                    university["name"],
                    university["url"]
                )

                directions = fetch_with_retry(get_directions, university["url"])

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

                    applicants = fetch_with_retry(parse_direction, direction["url"])

                    insert_applications(
                        cur,
                        direction_id,
                        applicants
                    )

                    time.sleep(0.5)

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
                print(f"ERROR з університетом {university['name']}: {e}")
                conn.rollback()


if __name__ == "__main__":
    main()