import datetime
import numpy as np


def datetime_normalize(time: any) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    Support datetime
    Support int 19900101
    Support str "19900101" "1990-01-01" "1990-01-01 12:12:12"
    Support date
    """
    if time is None:
        return None

    if isinstance(time, datetime.datetime):
        return time

    if isinstance(time, datetime.date):
        return datetime.datetime.combine(time, datetime.datetime.min.time())

    if isinstance(time, np.datetime64):
        # numpy datetime64 to python datetime
        # Convert to pandas timestamp first, then to python datetime
        ts = time.astype('datetime64[us]').astype(datetime.datetime)
        return ts

    if isinstance(time, int):
        time = str(time)

    # Try different formats
    formats = [
        "%Y%m%d%H%M%S",
        "%Y-%m-%d %H:%M:%S", 
        "%Y-%m-%d",
        "%Y%m%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(time, fmt)
        except ValueError:
            continue
    
    # If no format worked, raise an exception
    raise ValueError(f"Unable to parse datetime from: {time}")
