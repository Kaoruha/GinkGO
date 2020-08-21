import random
from .base_matcher import BaseMatcher
from ginkgo.backtest.event import OrderEvent, FillEvent
from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.enums import DealType
from ginkgo.backtest.postion import Position


class SimulateMatcher(BaseMatcher):
    def __init__(self,
                 stamp_tax: float = .001,
                 fee: float = .0000687,
                 slide: float = .002):
        BaseMatcher.__init__(self, stamp_tax=stamp_tax, fee=fee)
        self.slide = slide
        self.date = ''
        self.code = ''
        self.capital = 0
        self.deal = None
        self.position = None

    def get_result(self):
        # 查询结果，如果是实盘需要开启一个线程ping到有结果
        # 模拟盘就直接返回Fill了
        df = data_portal.query_stock(code=self.code,
                                     start_date=self.date,
                                     end_date=self.date,
                                     frequency='d',
                                     adjust_flag=3)
        # 模拟成交价
        price = df.iloc[0]['open'] + (
            (random.random() * 2 - 1) * self.slide + 1)
        price = round(price, 2)
        if self.deal == DealType.BUY:
            target_volume = int(self.capital / price / 100) * 100
            if target_volume == 0:
                return  # TODO 回头要找到0被传进来到原因
            total_price = target_volume * price
            fee = total_price * self._fee
            commission = total_price * self._commission
            remain = self.capital - total_price - fee - commission
            if remain < 0:
                target_volume = int(self.capital / price / 100 - 1) * 100
                total_price = target_volume * price
                fee = total_price * self._fee
                commission = total_price * self._commission
                if commission < self._min_commission:
                    commission = self._min_commission
                remain = self.capital - total_price - fee - commission

            fill = FillEvent(deal=DealType.BUY,
                             code=self.code,
                             price=price,
                             volume=target_volume,
                             fee=fee + commission,
                             remain=remain)
            self._engine.put(fill)
        elif self.deal == DealType.SELL:
            target_volume = self.position.volume
            if target_volume == 0:
                return  # TODO 回头要找到0被传进来到原因
            total_price = target_volume * price
            stamp_tax = total_price * self._stamp_tax
            fee = total_price * self._fee
            commission = total_price * self._commission
            if commission < self._min_commission:
                commission = self._min_commission
            remain = total_price - stamp_tax - fee - commission
            fill = FillEvent(deal=DealType.SELL,
                             code=self.code,
                             price=price,
                             volume=target_volume,
                             fee=stamp_tax + fee + commission,
                             remain=remain)
            self._engine.put(fill)

    def try_match(self, event: OrderEvent, position: Position):
        self.date = event.date
        self.code = event.code
        self.deal = event.deal
        self.position = position
        self.capital = event.capital

        # 如果是实盘就直接发下单信号
        self.get_result()
