import datetime
import numpy as np


def datetime_normalize(time: any) -> datetime.datetime:
    """
    Convert str or datetime into datetime "%Y-%m-%d %H:%M:%S"
    Support datetime
    Support int 19900101 or Unix timestamp (e.g., 1672531200)
    Support float Unix timestamp (e.g., 1672531200.123456)
    Support str "19900101" "1990-01-01" "1990-01-01 12:12:12" "1990-01-01 12:12"
    Support ISO 8601 formats "2023-12-31T23:59:59" "2023-12-31T23:59:59.123456" "2023-12-31T23:59"
    Support forward slash formats "2023/12/31" "2023/12/31 23:59:59" "2023/12/31 23:59"
    Support compact formats "20231231" "20231231235959" "202312312359"
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
        # Handle Unix timestamp (seconds since epoch) for integers
        if time > 99999999:  # Reasonable threshold for Unix timestamp (after 1973)
            try:
                return datetime.datetime.fromtimestamp(time)
            except (ValueError, OSError):
                # If timestamp conversion fails, treat as string format
                pass
        time = str(time)

    if isinstance(time, float):
        # Handle Unix timestamp (seconds since epoch) for floats
        try:
            return datetime.datetime.fromtimestamp(time)
        except (ValueError, OSError):
            # If timestamp conversion fails, continue to string parsing
            time = str(time)

    # Try different formats (ordered by common usage for efficiency)
    formats = [
        "%Y-%m-%d %H:%M:%S",        # Standard format with space: "2023-12-31 23:59:59"
        "%Y-%m-%d %H:%M:%S.%f",     # Standard format with microseconds: "2023-12-31 23:59:59.123456"
        "%Y-%m-%d %H:%M",           # Without seconds: "2023-12-31 23:59"
        "%Y-%m-%dT%H:%M:%S",        # ISO 8601 with T: "2023-12-31T23:59:59"
        "%Y-%m-%dT%H:%M:%S.%f",     # ISO 8601 with T and microseconds: "2023-12-31T23:59:59.123456"
        "%Y-%m-%dT%H:%M",           # ISO 8601 without seconds: "2023-12-31T23:59"
        "%Y/%m/%d %H:%M:%S",        # Forward slash with time: "2023/12/31 23:59:59"
        "%Y/%m/%d %H:%M",           # Forward slash without seconds: "2023/12/31 23:59"
        "%Y/%m/%d",                 # Forward slash date only: "2023/12/31"
        "%Y%m%d%H%M%S",             # Compact format: "20231231235959"
        "%Y%m%d%H%M",               # Compact format without seconds: "202312312359"
        "%Y%m%dT%H%M%S",            # Compact ISO format: "20231231T235959"
        "%Y%m%dT%H%M",              # Compact ISO format without seconds: "20231231T2359"
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
        "2023-12-31 23:59:59", "2023-12-31 23:59:59.123456", "2023-12-31 23:59",
        "2023-12-31T23:59:59", "2023-12-31T23:59:59.123456", "2023-12-31T23:59",
        "2023/12/31 23:59:59", "2023/12/31 23:59", "2023/12/31",
        "20231231235959", "202312312359", "20231231T235959", "20231231T2359",
        "2023-12-31", "20231231"
    ]
    raise ValueError(f"Unable to parse datetime from: {time}. Supported formats: {supported_formats}")
