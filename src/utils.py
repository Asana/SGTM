from datetime import datetime

STR_FMT = "%Y-%m-%dT%H:%M:%SZ"


def parse_date_string(date_string: str) -> datetime:
    return datetime.strptime(date_string, STR_FMT)
