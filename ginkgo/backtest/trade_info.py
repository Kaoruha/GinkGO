"""
交易记录类
"""
import uuid


class TradeInfo(object):
    # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
    def __init__(self, code, date, price, amount, order_id):
        self.code = code
        self.date = date
        self.price = price
        self.amount = amount
        self.order_id = order_id
        self.trade_id = self.trade_id_generator()

    def trade_id_generator(self):
        """
        交易ID生成
        """
        tuuid = uuid.uuid3(uuid.NAMESPACE_DNS,
                       f'{self.code}.{self.date}.{self.order_id}')
        result = str(tuuid).replace('-', '')
        return result


# ti = TradeInfo(code='sh.600000',
#                date='2020-08-12',
#                price='6.25',
#                amount=1000,
#                order_id=12)
# print(ti.trade_id)
