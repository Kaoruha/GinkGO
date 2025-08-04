import datetime
import numpy as np


def datetime_normalize(time: any) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    Support datetime
    Support int 19900101
    Support str "19900101" "1990-01-01" "1990-01-01 12:12:12"
    Support ISO 8601 formats "2023-12-31T23:59:59" "2023-12-31T23:59:59.123456"
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

    # Try different formats (ordered by common usage for efficiency)
    formats = [
        "%Y-%m-%d %H:%M:%S",        # Standard format with space: "2023-12-31 23:59:59"
        "%Y-%m-%dT%H:%M:%S",        # ISO 8601 with T: "2023-12-31T23:59:59"
        "%Y-%m-%dT%H:%M:%S.%f",     # ISO 8601 with T and microseconds: "2023-12-31T23:59:59.123456"
        "%Y%m%d%H%M%S",             # Compact format: "20231231235959"
        "%Y%m%dT%H%M%S",            # Compact ISO format: "20231231T235959"
        "%Y-%m-%d",                 # Date only: "2023-12-31"
        "%Y%m%d"                    # Compact date: "20231231"
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(time, fmt)
        except ValueError:
            continue
    
    # If no format worked, raise an exception with supported formats
    supported_formats = [
        "2023-12-31 23:59:59", "2023-12-31T23:59:59", "2023-12-31T23:59:59.123456",
        "20231231235959", "20231231T235959", "2023-12-31", "20231231"
    ]
    raise ValueError(f"Unable to parse datetime from: {time}. Supported formats: {supported_formats}")
