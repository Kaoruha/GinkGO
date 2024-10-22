from decimal import Decimal

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs.ginkgo_number import Number, to_decimal


def cal_fee(direction: DIRECTION_TYPES, price: Number, tax_rate: Number) -> Decimal:
    price = to_decimal(price)
    tax_rate = to_decimal(tax_rate)
    # 佣金
    fee = price * tax_rate
    if fee < Decimal("5"):
        fee = Decimal("5")
    # 印花税
    fee += price * Decimal("0.001")
    # 过户费
    if direction == DIRECTION_TYPES.SHORT:
        fee += price * Decimal("0.00002")
    return fee
