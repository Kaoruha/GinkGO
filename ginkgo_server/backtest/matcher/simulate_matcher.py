import random
from ginkgo_server.backtest.matcher.base_matcher import BaseMatcher
from ginkgo_server.backtest.events import FillEvent
from ginkgo_server.backtest.enums import DealType
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.price import DayBar, Min5Bar


class SimulateMatcher(BaseMatcher):
    def __init__(
        self,
        *,
        stamp_tax_rate: float = 0.001,
        transfer_fee_rate: float = 0.0002,
        commission_rate: float = 0.0003,
        min_commission: float = 5,
        slippage: float = 0.02,
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

    def try_match(self, order, broker, price: DayBar):
        """
        尝试撮合
        """
        # 检查价格信息是否为空
        # 修改了Price的格式，好像不需要检查是否为空了
        # if price.shape[0] != 1:
        #     print(f"今日{order.code} 无价格信息，可能休市")
        #     return
        # 检查价格信息的日期是否在订单事件日期之后
        if str(price.data.date) <= str(order.date):
            print("需要在订单事件生成的第二天才可以进行撮合尝试")
            return order

        # 尝试成交
        if order.deal == DealType.BUY:
            p = float(price.data.open) * 1.1
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
            order.freeze_money(bussiness_volume + fee)
        elif order.deal == DealType.SELL:
            if order.code not in broker.position:
                print(f"未持有{order.code}")
            broker.position[order.code].per_sell(order.volume)
            order.volume = broker.position[order.code].freeze

        order.date = price.data.date
        order.source = f"{self._name} 通过初步校验，模拟发出下单命令，等待返回下单结果"

        self.send_order(order)

    def get_result(self, price):
        """
        尝试获取订单结果

        交易成功会返回FillEvent，交易失败会返回失败的FillEvent与日期更新后的Order
        """
        result = []
        price = price.data
        for i in self._match_list:
            # 休市或者停牌的处理
            # if price.shape[0] == 0:
            #     i.source = f"{price.date} 无价格信息，可能休市或停牌，模拟成交类重新推送"
            #     i.date = price.date
            #     f = FillEvent(
            #         deal=i.deal,
            #         date=price.date,
            #         code=i.code,
            #         price=0,
            #         volume=0,
            #         source="无价格信息",
            #         fee=0,
            #         remain=i.freeze if i.deal == DealType.BUY else i.volume,
            #         done=False,
            #     )
            #     result.append(f)
            #     result.append(i)
            #     continue

            pct_chg = float(price["pct_chg"])

            # 涨跌停处理
            if abs(pct_chg) >= 9.5:
                # 涨停处理
                if pct_chg > 0 and i.deal == DealType.BUY:
                    i.source = f"{price.date} {i.code} 涨停，无法购买，模拟成交类重新推送"
                    i.date = price.date
                    f = FillEvent(
                        deal=i.deal,
                        date=price.date,
                        code=i.code,
                        price=0,
                        volume=i.volume,
                        source=i.source,
                        fee=0,
                        remain=i.freeze,
                        freeze=i.freeze,
                        done=False,
                    )
                    result.append(f)
                    result.append(i)
                    return result
                # 跌停处理
                if pct_chg < 0 and i.deal == DealType.SELL:
                    i.source = f"{price.date} {i.code} 跌停，无法卖出，模拟成交类重新推送"
                    i.date = price.date
                    f = FillEvent(
                        deal=i.deal,
                        date=price.date,
                        code=i.code,
                        price=0,
                        volume=0,
                        source=i.source,
                        fee=0,
                        remain=i.freeze,
                        freeze=i.freeze,
                        done=False,
                    )
                    result.append(f)
                    result.append(i)
                    return result

            # 模拟成交处理
            # 目前在一天的价格内随机取一个作为成交价
            # 也可以考虑从开盘价出发，进行一定范围的滑动
            # r = (random.random() * 2 - 1) * self._slippage
            high = float(price.high)
            low = float(price.low)
            p = random.random() * (high - low) + low
            total = p * i.volume
            f = FillEvent(
                deal=i.deal,
                date=price.date,
                code=i.code,
                price=p,
                volume=i.volume,
                source=f"{price.date}模拟成交",
                fee=self.fee_cal(bussiness_volume=total, deal_type=i.deal),
                remain=(i.freeze - total) if i.deal == DealType.BUY else total,
                freeze=i.freeze,
                done=True,
            )
            result.append(f)

        return result
