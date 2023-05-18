def cal_fee(self, direction: DIRECTION_TYPES, price: float) -> float:
    # 佣金
    fee = price * self.tax_rate
    if fee < 5:
        fee = 5
    # 印花税
    fee += price * 0.001
    # 过户费
    if direction == DIRECTION_TYPES.SHORT:
        fee += price * 0.00002
    return fee
