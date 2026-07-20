import time


def fetch_with_retry(
    func,
    *args,
    max_retries=50,
    delay=3,
    **kwargs
):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            print(
                f"Помилка під час {func.__name__}: "
                f"{e}. "
                f"Спроба {attempt + 1}/{max_retries}"
            )

            time.sleep(delay)

    raise Exception(
        f"Не вдалося виконати {func.__name__}"
    )