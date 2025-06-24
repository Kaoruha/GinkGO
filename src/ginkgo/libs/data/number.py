import numpy as np
from typing import Union
from decimal import Decimal, InvalidOperation

Number = Union[float, int, Decimal]


def to_decimal(value: Number) -> Decimal:
    if isinstance(value, Decimal):
        return value
    
    if value is None:
        raise TypeError("Cannot convert None to Decimal")
    
    try:
        return Decimal(str(value))
    except InvalidOperation as e:
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")
