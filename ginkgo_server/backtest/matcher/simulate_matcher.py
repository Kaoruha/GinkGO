import random
from ginkgo_server.backtest.matcher.base_matcher import BaseMatcher
from ginkgo_server.backtest.events import DealType, FillEvent
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm


class SimulateMatcher(BaseMatcher):
    def __init__(
        self,
        *,
        stamp_tax_rate=0.001,
        transfer_fee_rate=0.0002,
        commission_rate=0.0003,
        min_commission=5,
        slippage=0.02,
    ):
        super(SimulateMatcher, self).__init__(
            name="回测模拟成交",
            stamp_tax_rate=stamp_tax_rate,
            transfer_fee_rate=transfer_fee_rate,
            commission_rate=commission_rate,
            min_commission=min_commission,
        )
        self._slippage = slippage

    def __repr__(self):
        stamp = self._stamp_tax_rate
        trans = self._transfer_fee_rate
        comm = self._commission_rate
        min_comm = self._min_commission
        s = f"回测模拟成交，当前印花税：「{stamp}」，过户费：「{trans}」，交易佣金：「{comm}」，最小交易佣金：「{min_comm}」"
        return s

    def send_order(self, order):
        self._match_list.append(order)

    def try_match(self, order, broker, price):
        """
        尝试撮合
        """
        # 检查价格信息是否为空
        if price.shape[0] != 1:
            print(f"今日{order.code} 无价格信息，可能休市")
            return
        # 检查价格信息的日期是否在订单事件日期之后
        if str(price.loc[0].date) <= str(order.date):
            print("需要在订单事件生成的第二天才可以进行撮合尝试")
            return order

        # 尝试成交
        if order.deal == DealType.BUY:
            p = float(price.loc[0].open)
            bussiness_volume = p * order.volume
            fee = self.fee_cal(bussiness_volume=bussiness_volume, deal_type=order.deal)
            if broker._capitial <= (bussiness_volume + fee):
                # 当前现金小于预计成交量与税费，调整Order内的Volume后再尝试成交
                gap = bussiness_volume + fee - broker._capitial
                order.adjust_volume(-(gap / p))
                bussiness_volume = p * order.volume
            print(
                f"预计成交量：{order.volume}，预计成交金额：{bussiness_volume}，税费：{fee}，当前现金：{broker._capitial}"
            )
            broker.freeze_money(bussiness_volume + fee)
        elif order.deal == DealType.SELL:
            if order.code not in broker.position:
                print(f"未持有{order.code}")
            broker.position[order.code].per_sell(order.volume)
            order.volume = broker.position[order.code].freeze

        order.date = price.loc[0].date

        self.send_order(order)

    def get_result(self):
        print("尝试获取结果")
        result = []
        for i in self._match_list:
            r = (random.random() * 2 - 1) * self._slippage
            p_df = gm.get_dayBar_by_mongo(
                code=i.code, start_date=i.date, end_date=i.date
            )
            p = float(p_df.loc[0].open) * (1 + r)
            # TODO 需要考虑涨跌停
            print(p)
