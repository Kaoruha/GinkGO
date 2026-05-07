# Upstream: math模块(cal_fee)、logger模块(日志类型支持)、normalize模块
# Downstream: numpy, Decimal
# Role: 数字类型工具，定义Number类型别名(float/int/Decimal)和to_decimal转换函数






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


def convert_to_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    return default


def convert_to_int(value, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    return default


def convert_to_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        return default
    return default

