import time


import time


def fetch_with_retry(
    func,
    *args,
    max_retries=50,
    delay=3,
    **kwargs
):
    url = args[0] if args else "N/A"

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            print(
                f"[{func.__name__}] "
                f"{url} "
                f"ERROR {attempt + 1}/{max_retries}: {e}"
            )

            time.sleep(delay)

    raise Exception(
        f"Не вдалося виконати {func.__name__}: {url}"
    )