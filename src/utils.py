import asana  # type: ignore

from datetime import datetime
from typing import Callable, Dict, Any
from src.logger import logger


def parse_date_string(date_string: str) -> datetime:
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")


def create_date_string(from_datetime: datetime) -> str:
    return from_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def memoize(func: Callable) -> Callable:
    memo: Dict[Any, Any] = {}

    def inner(*args):
        if args in memo:
            return memo[args]
        result = func(*args)
        memo[args] = result
        return result

    return inner

def safe_asana_api_request(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
        except asana.error.InvalidRequestError as ire:
            logger.error(f"asana.error.InvalidRequestError: {ire}")

    return wrapper