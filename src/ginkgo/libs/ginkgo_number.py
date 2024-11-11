import numpy as np
from typing import Union
from decimal import Decimal

Number = Union[float, int, Decimal]


def to_decimal(value: Number) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
