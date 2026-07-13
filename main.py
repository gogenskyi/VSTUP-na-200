import sqlite3
import time

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


def fetch_with_retry(func, *args, max_retries=3, delay=5, **kwargs):
    """
    Виконує функцію. Якщо стається помилка, повторює спробу.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Помилка сервера під час {func.__name__}: {e}. Спроба {attempt + 1} з {max_retries}...")
            time.sleep(delay)

    # Якщо всі спроби вичерпано, прокидаємо помилку далі
    raise Exception(f"Не вдалося виконати {func.__name__} після {max_retries} спроб.")

def main():
    conn = sqlite3.connect("vstup2.db", timeout=30)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    cur = conn.cursor()
    init_db(conn)

    # Припускаємо, що get_regions відпрацює без проблем, 
    # або її теж можна обгорнути у fetch_with_retry
    regions = get_regions()

    for region in regions:
        print(f"Починаємо обробку регіону: {region['name']}")
        region_id = get_or_create_region(cur, region["name"])

        try:
            # Використовуємо retry для отримання списку університетів
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

            # РОЗДІЛЯЄМО TRY-EXCEPT: Тепер ловимо помилки для КОЖНОГО університету окремо
            try:
                uni_id = insert_university(
                    cur,
                    region_id,
                    university["name"],
                    university["url"]
                )

                # Retry для отримання напрямків
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

                    # Retry для отримання абітурієнтів
                    applicants = fetch_with_retry(parse_direction, direction["url"])

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

                # Комітимо дані після УСПІШНОЇ обробки всього університету
                conn.commit()

            except Exception as e:
                # Якщо сталася помилка з конкретним університетом — відкочуємо тільки його
                print(f"ERROR з університетом {university['name']}: {e}")
                conn.rollback()
                # Цикл продовжить роботу з НАСТУПНИМ університетом, а не регіоном


if __name__ == "__main__":
    main()
