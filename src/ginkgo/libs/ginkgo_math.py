from src.ginkgo.enums import DIRECTION_TYPES


def cal_fee(direction: DIRECTION_TYPES, price: float, tax_rate: float) -> float:
    # 佣金
    fee = price * tax_rate
    if fee < 5:
        fee = 5
    # 印花税
    fee += price * 0.001
    # 过户费
    if direction == DIRECTION_TYPES.SHORT:
        fee += price * 0.00002
    return fee
