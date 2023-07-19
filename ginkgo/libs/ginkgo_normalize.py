import datetime


def datetime_normalize(time: any) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    Support datetime
    Support int 19900101
    Support str "19900101" "1990-01-01" "1990-01-01 12:12:12"
    """
    t = datetime.datetime.now()

    if time is None:
        return time

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
