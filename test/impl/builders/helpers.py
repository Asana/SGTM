from uuid import uuid4
from datetime import datetime
from typing import Union

from src.utils import create_date_string


def transform_datetime(input_datetime: Union[str, datetime]) -> str:
    if isinstance(input_datetime, datetime):
        return create_date_string(input_datetime)
    return input_datetime


def create_uuid() -> str:
    return uuid4().hex
