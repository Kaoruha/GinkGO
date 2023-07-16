import datetime


def datetime_normalize(time: str or datetime.datetime) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    """
    t = datetime.datetime.now()

    if isinstance(time, datetime.datetime):
        return time

    if isinstance(time, int):
        time = str(time)

    try:
        t = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    try:
        t = datetime.datetime.strptime(time, "%Y-%m-%d")
    except ValueError:
        pass

    try:
        t = datetime.datetime.strptime(time, "%Y%m%d")
    except ValueError:
        pass

    return t
