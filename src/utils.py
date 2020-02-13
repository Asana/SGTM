from datetime import datetime
from typing import Callable


def parse_date_string(date_string: str) -> datetime:
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")


def create_date_string(from_datetime: datetime) -> str:
    return from_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def memoize(func: Callable) -> Callable:
    memo = {}

    def inner(*args):
        if args in memo:
            return memo[args]
        result = func(*args)
        memo[args] = result
        return result

    return inner
