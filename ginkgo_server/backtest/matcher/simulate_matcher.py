import random
from .base_matcher import BaseMatcher
from ginkgo_server.backtest.events import OrderEvent, FillEvent
from ginkgo_server.data.data_portal import data_portal
from ginkgo_server.backtest.enums import DealType
from ginkgo_server.backtest.postion import Position


class SimulateMatcher(BaseMatcher):
    def __init__(self,
                 stamp_tax_rate: float = .001,
                 fee_rate: float = .0000687,  
                 slide: float = .002):
        BaseMatcher.__init__(self, stamp_tax_rate=stamp_tax_rate, fee_rate=fee_rate)
        self.slide = slide # 滑点
        self.date = ''
        self.code = ''
        self.remain = 0 # 剩余资金
        self.source = ''
        self.deal = None
        self.position = None


    def try_match(self, event: OrderEvent, position: Position):
        self.date = event.date
        self.code = event.code
        self.deal = event.deal
        self.target_volume = event.target_volume
        self.position = position
        self.source = event.source
        
        if self.deal == DealType.BUY:
            self.remain = event.ready_capital
        elif self.deal == DealType.SELL:
            self.remain = 0
        

        # 如果是实盘就直接发下单信号
        self.get_result()

    def get_result(self):
        # 查询结果，如果是实盘需要开启一个线程ping到有结果
        # 模拟盘就直接返回Fill了
        df = data_portal.query_stock(code=self.code,
                                     start_date=self.date,
                                     end_date=self.date,
                                     frequency='d',
                                     adjust_flag=1)
        # 模拟成交,此处模拟按照开盘价购入
        price = df.iloc[0]['open']
        price = round(price, 2)
        # TODO 加入随机参数slider，让价格随机上下波动


        # 交易失败的情况
        fail_condition1 = abs(df.iloc[0]['turn']) >= 9.5
        if fail_condition1:
            fill = FillEvent(deal=self.deal,
            date=self.date,
            code=self.code,
            price=price,
            volume=self.target_volume,
            source=self.source,
            fee=0,
            remain=self.remain,
            done=False)
            self._engine.put(fill)
            return


        # TODO 交易成功的情况
        if self.deal == DealType.BUY:
            to_buy_volume = int(self.remain / (price * 100)) * 100
            total_price = to_buy_volume * price
            fee = total_price * self._fee_rate
            commission = total_price * self._commission_rate
            if commission < self._min_commission:
                commission = self._min_commission
            remain = self.remain - total_price - fee - commission

            # 如果扣掉各种税费，剩余的钱不够了那么就少买一手
            if self.remain <= 0:
                to_buy_volume = int(self.remain / (price * 100) - 1) * 100
                total_price = to_buy_volume * price
                fee = total_price * self._fee_rate
                commission = total_price * self._commission_rate
                if commission < self._min_commission:
                    commission = self._min_commission
                remain = self.remain - total_price - fee - commission
            
            fill = FillEvent(deal=DealType.BUY,
                             date=self.date,
                             code=self.code,
                             price=price,
                             source=self.source,
                             volume=to_buy_volume,
                             fee=fee + commission,
                             remain=remain,
                             done=True)
            self._engine.put(fill)
        elif self.deal == DealType.SELL:
            to_sell_volume = self.target_volume if self.target_volume <= self.position.freeze else self.position.freeze
            total_price = to_sell_volume * price # 得到卖出的总价
            stamp_tax = total_price * self._stamp_tax_rate # 计算印花税
            fee = total_price * self._fee_rate # 计算过户费
            commission = total_price * self._commission_rate # 计算交易佣金
            if commission < self._min_commission:
                commission = self._min_commission # 如果交易佣金不到最低佣金，则设置交易佣金为最低佣金
            remain = total_price - stamp_tax - fee - commission # 交完乱七八糟各种税以后的剩余资金
            fill = FillEvent(deal=DealType.SELL,
                             code=self.code,
                             date=self.date,
                             price=price,
                             source=self.source,
                             volume=to_sell_volume,
                             fee=stamp_tax + fee + commission,
                             remain=remain,
                             done=True)
            self._engine.put(fill)


