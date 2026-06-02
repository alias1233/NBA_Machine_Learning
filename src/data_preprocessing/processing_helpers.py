from datetime import datetime

NBA_DATE_FORMAT = "%b %d, %Y"

def convert_to_datetime(date: str) -> datetime:
    return datetime.strptime(date, NBA_DATE_FORMAT)