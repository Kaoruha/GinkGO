import datetime


def datetime_normalize(time) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    """
    if isinstance(time, datetime.datetime):
        return time
    elif isinstance(time, str):
        t = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        return t
