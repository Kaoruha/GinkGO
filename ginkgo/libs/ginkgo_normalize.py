import datetime


def datetime_normalize(time: str or datetime.datetime) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    """
    if isinstance(time, datetime.datetime):
        return time
    elif isinstance(time, str):
        try:
            t = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            t = datetime.datetime.strptime(time, "%Y-%m-%d")
        return t
