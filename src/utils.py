from datetime import datetime
from typing import Callable

STR_FMT = "%Y-%m-%dT%H:%M:%S%z"


def parse_date_string(date_string: str) -> datetime:
    return datetime.strptime(date_string, STR_FMT)


def memoize(func: Callable) -> Callable:
    memo = {}

    def inner(*args):
        if args in memo:
            return memo[args]
        result = func(*args)
        memo[args] = result
        return result

    return inner
