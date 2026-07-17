import sqlite3
import heapq
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Використовуємо slots для суттєвої економії пам'яті при великій кількості об'єктів
@dataclass(slots=True)
class Application:
    applicant_id: int
    direction_id: int
    priority: int
    score: float


def load_data(conn) -> Tuple[Dict[int, List[Application]], Dict[int, int]]:
    cur = conn.cursor()

    cur.execute("""
        SELECT applicant_id, direction_id, priority, score
        FROM applications
        ORDER BY applicant_id, priority
    """)

    applications = defaultdict(list)
    for row in cur.fetchall():
        app = Application(*row)
        applications[row[0]].append(app)

    cur.execute("SELECT id, budget_places FROM directions")
    capacities = {row[0]: row[1] for row in cur.fetchall()}

    return applications, capacities


def run_competition(
        applications: Dict[int, List[Application]],
        capacities: Dict[int, int]
) -> Tuple[Dict[int, dict], Dict[int, List[Application]]]:
    next_choice = {applicant_id: 0 for applicant_id in applications}
    # Зберігаємо купу (Min-Heap) для кожного напрямку.
    # Формат елемента купи: (score, applicant_id, application_obj)
    accepted_heap = defaultdict(list)
    free_applicants: Set[int] = set(applications.keys())

    while free_applicants:
        applicant_id = free_applicants.pop()
        applicant_apps = applications[applicant_id]
        choice_idx = next_choice[applicant_id]

        # Якщо всі пріоритети вичерпано
        if choice_idx >= len(applicant_apps):
            continue

        application = applicant_apps[choice_idx]
        next_choice[applicant_id] += 1

        direction_id = application.direction_id
        capacity = capacities.get(direction_id, 0)

        # Якщо місць на напрямку немає взагалі
        if capacity == 0:
            free_applicants.add(applicant_id)
            continue

        # Елемент купи. Якщо score однакові, порівнюється applicant_id (детермінованість)
        heap_element = (application.score, applicant_id, application)
        direction_heap = accepted_heap[direction_id]

        if len(direction_heap) < capacity:
            heapq.heappush(direction_heap, heap_element)
        else:
            # direction_heap[0] — це заявка з НАЙМЕНШИМ балом (і найменшим ID при рівності)
            lowest_accepted = direction_heap[0]

            if heap_element > lowest_accepted:
                # Нова заявка краща за найгіршу прийняту. Виштовхуємо найгіршу.
                rejected_element = heapq.heappushpop(direction_heap, heap_element)
                rejected_applicant_id = rejected_element[1]
                free_applicants.add(rejected_applicant_id)
            else:
                # Нова заявка гірша, абітурієнт йде на наступний пріоритет
                free_applicants.add(applicant_id)

    # Формуємо фінальні результати у зручному вигляді
    allocations = {}
    accepted = defaultdict(list)

    for direction_id, heap in accepted_heap.items():
        # Сортуємо фінальний список для коректного збереження/відображення
        sorted_heap = sorted(heap, key=lambda x: x[0], reverse=True)
        for score, app_id, app in sorted_heap:
            accepted[direction_id].append(app)
            allocations[app_id] = {
                "direction_id": direction_id,
                "priority": app.priority,
                "score": app.score
            }

    return allocations, accepted


def calculate_passing_scores(accepted: Dict[int, List[Application]]) -> Dict[int, float]:
    result = {}
    for direction_id, apps in accepted.items():
        if apps:
            result[direction_id] = min(app.score for app in apps)
    return result


def save_results(source_conn, allocations, accepted, passing_scores):
    result_db = Path(__file__).resolve().parent.parent / "competition.db"
    conn = sqlite3.connect(result_db)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS allocations;
        DROP TABLE IF EXISTS directions_results;

        CREATE TABLE allocations (
            applicant_id INTEGER PRIMARY KEY,
            direction_id INTEGER NOT NULL,
            priority INTEGER NOT NULL,
            score REAL NOT NULL
        );

        CREATE TABLE directions_results (
            direction_id INTEGER PRIMARY KEY,
            university_name TEXT NOT NULL,
            direction_name TEXT NOT NULL,
            budget_places INTEGER NOT NULL,
            allocated_count INTEGER NOT NULL,
            passing_score REAL
        );
    """)

    cur.executemany(
        """
        INSERT INTO allocations (applicant_id, direction_id, priority, score)
        VALUES (?, ?, ?, ?)
        """,
        [(app_id, data["direction_id"], data["priority"], data["score"])
         for app_id, data in allocations.items()]
    )

    src_cur = source_conn.cursor()
    src_cur.execute("""
        SELECT d.id, d.name, d.budget_places, u.name
        FROM directions d
        JOIN universities u ON u.id = d.university_id
    """)

    rows = [
        (
            direction_id,
            university_name,
            direction_name,
            budget_places,
            len(accepted.get(direction_id, [])),
            passing_scores.get(direction_id)
        )
        for direction_id, direction_name, budget_places, university_name in src_cur.fetchall()
    ]

    cur.executemany(
        """
        INSERT INTO directions_results (
            direction_id, university_name, direction_name, 
            budget_places, allocated_count, passing_score
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    conn.commit()
    conn.close()


def main():
    db_path = Path(__file__).resolve().parent.parent / "vstup3.db"
    with sqlite3.connect(db_path) as conn:
        applications, capacities = load_data(conn)

        allocations, accepted = run_competition(applications, capacities)
        passing_scores = calculate_passing_scores(accepted)

        save_results(conn, allocations, accepted, passing_scores)

    print(f"Applicants: {len(applications)}")
    print(f"Directions: {len(capacities)}")
    print(f"Budget places: {sum(capacities.values())}")
    print(f"Allocated: {len(allocations)}")

    # Виводимо топ-10 напрямків з найвищим прохідним балом
    print("\nТоп-10 прохідних балів:")
    top_scores = sorted(passing_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    for direction_id, score in top_scores:
        print(f"ID {direction_id}: {score}")


if __name__ == "__main__":
    main()