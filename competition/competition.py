import heapq
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Set


@dataclass(slots=True)
class Application:
    applicant_id: int
    direction_id: int
    priority: int
    score: float
    quota: str


def load_data(conn: sqlite3.Connection) -> Tuple[Dict[int, List[Application]], Dict[int, int]]:
    """Завантажує заяви та обсяги бюджетних місць з БД."""
    cur = conn.cursor()

    # Завантаження заяв
    cur.execute("""
        SELECT
            applicant_id,
            direction_id,
            priority,
            score,
            quota
        FROM applications
        WHERE priority IS NOT NULL AND priority > 0
        ORDER BY applicant_id, priority
    """)

    applications = defaultdict(list)
    for row in cur.fetchall():
        app = Application(
            applicant_id=int(row[0]),
            direction_id=int(row[1]),
            priority=int(row[2]),
            score=float(row[3]),
            quota=row[4]
        )
        applications[app.applicant_id].append(app)

    # Завантаження обсягів (бюджетних місць)
    cur.execute("""
        SELECT
            id,
            budget_places
        FROM directions
    """)

    capacities = {
        direction_id: int(budget_places or 0)
        for direction_id, budget_places in cur.fetchall()
    }

    return applications, capacities


def run_competition(
        applications: Dict[int, List[Application]],
        capacities: Dict[int, int]
) -> Tuple[Dict[int, dict], Dict[int, List[Application]]]:
    """Виконує алгоритм розподілу (аналог Гейла-Шеплі)."""

    # Індекс наступної заяви для кожного абітурієнта
    next_choice = {applicant_id: 0 for applicant_id in applications}
    accepted_heap = defaultdict(list)
    free_applicants: Set[int] = set(applications.keys())

    while free_applicants:
        applicant_id = free_applicants.pop()
        choices = applications[applicant_id]
        idx = next_choice[applicant_id]

        if idx >= len(choices):
            continue  # Абітурієнт вичерпав усі пріоритети

        app = choices[idx]
        next_choice[applicant_id] += 1

        direction_id = app.direction_id
        capacity = capacities.get(direction_id, 0)

        # Якщо місць немає взагалі, пробуємо наступний пріоритет
        if capacity <= 0:
            free_applicants.add(applicant_id)
            continue

        heap = accepted_heap[direction_id]

        # Кандидат оцінюється за балом (чим більше, тим краще)
        # При рівних балах перевага надається вищому пріоритету (менше число)
        candidate_score = (app.score, -app.priority, applicant_id)

        # Якщо є вільні місця, просто додаємо
        if len(heap) < capacity:
            heapq.heappush(heap, (candidate_score, app))
            continue

        # Якщо місць немає, порівнюємо з найслабшим кандидатом
        weakest_candidate, weakest_app = heap[0]

        if candidate_score > weakest_candidate:
            # Витісняємо найслабшого
            removed_candidate, removed_app = heapq.heapreplace(heap, (candidate_score, app))
            free_applicants.add(removed_app.applicant_id)
        else:
            # Абітурієнт не пройшов, повертаємо його в чергу для наступного пріоритету
            free_applicants.add(applicant_id)

    # Формування результатів
    allocations = {}
    accepted = defaultdict(list)

    for direction_id, heap in accepted_heap.items():
        # Сортуємо зарахованих за балом (від найбільшого до найменшого)
        sorted_apps = sorted(
            [item[1] for item in heap],
            key=lambda x: x.score,
            reverse=True
        )
        accepted[direction_id] = sorted_apps

        for app in sorted_apps:
            allocations[app.applicant_id] = {
                "direction_id": direction_id,
                "priority": app.priority,
                "score": app.score,
                "quota": app.quota
            }

    return allocations, accepted


def calculate_passing_scores(accepted: Dict[int, List[Application]]) -> Dict[int, float]:
    """Рахує прохідний бал для кожної конкурсної пропозиції."""
    result = {}
    for direction_id, apps in accepted.items():
        if apps:
            result[direction_id] = min(app.score for app in apps)
    return result


def save_results(
        source_conn: sqlite3.Connection,
        allocations: Dict[int, dict],
        accepted: Dict[int, List[Application]],
        passing_scores: Dict[int, float]
):
    result_db = Path(__file__).resolve().parent / "competition_results.db"

    with sqlite3.connect(result_db) as conn:
        cur = conn.cursor()

        cur.executescript("""
            DROP TABLE IF EXISTS results;

            CREATE TABLE results (
                applicant_id INTEGER PRIMARY KEY,
                direction_id INTEGER NOT NULL,

                university_name TEXT,
                field_code TEXT,
                field_name TEXT,

                speciality_code TEXT,
                speciality_name TEXT,

                direction_name TEXT,

                priority INTEGER,
                score REAL,
                quota TEXT,

                budget_places INTEGER,
                allocated_count INTEGER,
                passing_score REAL
            );

            CREATE INDEX idx_results_speciality
            ON results(speciality_code);

            CREATE INDEX idx_results_field
            ON results(field_code);

            CREATE INDEX idx_results_direction
            ON results(direction_id);
        """)

        src = source_conn.cursor()

        src.execute("""
            SELECT
                d.id,
                u.name,
                d.field_code,
                d.field_name,
                d.speciality_code,
                d.speciality_name,
                d.name,
                d.budget_places
            FROM directions d
            JOIN universities u
                ON u.id = d.university_id
        """)

        direction_info = {}

        for row in src.fetchall():
            direction_info[row[0]] = {
                "university_name": row[1],
                "field_code": row[2],
                "field_name": row[3],
                "speciality_code": row[4],
                "speciality_name": row[5],
                "direction_name": row[6],
                "budget_places": int(row[7] or 0)
            }

        rows = []

        for applicant_id, data in allocations.items():

            direction_id = data["direction_id"]

            info = direction_info.get(direction_id)

            if not info:
                continue

            rows.append(
                (
                    applicant_id,
                    direction_id,

                    info["university_name"],

                    info["field_code"],
                    info["field_name"],

                    info["speciality_code"],
                    info["speciality_name"],

                    info["direction_name"],

                    data["priority"],
                    data["score"],
                    data["quota"],

                    info["budget_places"],

                    len(accepted.get(direction_id, [])),

                    passing_scores.get(direction_id)
                )
            )

        cur.executemany(
            """
            INSERT INTO results (
                applicant_id,
                direction_id,

                university_name,

                field_code,
                field_name,

                speciality_code,
                speciality_name,

                direction_name,

                priority,
                score,
                quota,

                budget_places,
                allocated_count,
                passing_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows
        )

        conn.commit()


def main():
    db_path = Path(__file__).resolve().parent.parent / "vstup2026.db"

    print(f"Шукаю базу даних за шляхом: {db_path}")

    if not db_path.exists():
        print("❌ ПОМИЛКА: Файл бази даних не знайдено!")
        print("Будь ласка, перевірте, як точно називається файл з вашою базою.")
        return

    if db_path.stat().st_size == 0:
        print("❌ ПОМИЛКА: Файл бази даних порожній (0 байт).")
        print("Видаліть цей файл, він був випадково створений SQLite.")
        return

    with sqlite3.connect(db_path) as conn:
        print("✅ Базу знайдено. Завантаження даних...")
        applications, capacities = load_data(conn)

        print("Запуск алгоритму розподілу...")
        allocations, accepted = run_competition(applications, capacities)

        print("Розрахунок прохідних балів...")
        passing_scores = calculate_passing_scores(accepted)

        print("Збереження результатів...")
        save_results(conn, allocations, accepted, passing_scores)

    print("\n--- Статистика симуляції ---")
    print(f"Абітурієнтів у базі (з пріоритетами): {len(applications)}")
    print(f"Конкурсних пропозицій (напрямків): {len(capacities)}")
    print(f"Всього бюджетних місць: {sum(capacities.values())}")
    print(f"Рекомендовано до зарахування: {len(allocations)}")


if __name__ == "__main__":
    main()