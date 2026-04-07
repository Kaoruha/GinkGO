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

