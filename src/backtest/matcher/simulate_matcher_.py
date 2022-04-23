import random
from src.backtest.matcher.base_matcher import BaseMatcher
from src.backtest.events import FillEvent
from src.backtest.enums import Direction
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.backtest.price import Bar


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

    def try_match(self, order, broker, last_price):
        """
        尝试撮合
        """
        # 尝试成交
        if order.code not in last_price.keys():
            print("目前已知价格中没有 {order.code} 相关价格, 请检查代码")
            return
        date = last_price[order.code].data.date
        if order.deal == Direction.BUY:
            p = float(last_price[order.code].data.open) * 1.1
            bussiness_volume = p * order.volume
            fee = self.fee_cal(bussiness_volume=bussiness_volume, deal_type=order.deal)
            if broker.capital <= (bussiness_volume + fee):
                # 当前现金小于预计成交量与税费，调整Order内的Volume后再尝试成交
                gap = bussiness_volume + fee - broker.capital
                order.adjust_volume(-(gap / p))
                bussiness_volume = p * order.volume
            print(
                f"{date} 预计成交量：{order.volume}，预计成交金额：{bussiness_volume}，税费：{fee}，当前现金：{broker.capital}"
            )
            broker.freeze_money(bussiness_volume + fee)
            order.freeze_money(bussiness_volume + fee)
        elif order.deal == Direction.SELL:
            if order.code not in broker.position:
                print(f"{date} 未持有{order.code}")
                return
            p = broker.position[order.code]
            if p.volume >= order.volume:
                p.per_sell(order.volume)
                order.volume = p.freeze
            else:
                print(f"{date} {order.code} 持有量小于预计卖出量，丢弃该订单事件")
                return

        order.date = last_price[order.code].data.date
        order.source = f"{self._name} 通过初步校验，模拟发出下单命令，等待返回下单结果"

        self.send_order(order)

    def get_result(self, last_price):
        """
        尝试获取订单结果

        交易成功会返回FillEvent，交易失败会返回失败的FillEvent与日期更新后的Order
        """
        result = []
        for i in self._match_list:
            if i.code not in last_price.keys():
                print("未持有订单标的的价格数据，请检查代码")
                continue
            if isinstance(last_price[i.code], DayBar):
                p = last_price[i.code].data
                pct_chg = float(p["pct_chg"])

                # 涨跌停处理
                if abs(pct_chg) >= 9.5:
                    # 涨停处理
                    if pct_chg > 0 and i.deal == Direction.BUY:
                        i.source = f"{p.date} {i.code} 涨停，无法购买，模拟成交类重新推送"
                        i.date = p.date
                        f = FillEvent(
                            deal=i.deal,
                            date=p.date,
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
                        continue
                    # 跌停处理
                    if pct_chg < 0 and i.deal == Direction.SELL:
                        i.source = f"{p.date} {i.code} 跌停，无法卖出，模拟成交类重新推送"
                        i.date = p.date
                        f = FillEvent(
                            deal=i.deal,
                            date=p.date,
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
                        continue

                # 模拟成交处理
                # 目前在一天的价格内随机取一个作为成交价
                # 也可以考虑从开盘价出发，进行一定范围的滑动
                high = float(p.high)
                low = float(p.low)
                p_random = random.random() * (high - low) + low
                total = p_random * i.volume
                fee = self.fee_cal(bussiness_volume=total, deal_type=i.deal)
                f = FillEvent(
                    deal=i.deal,
                    date=p.date,
                    code=i.code,
                    price=p_random,
                    volume=i.volume,
                    source=f"{p.date} 模拟成交",
                    fee=fee,
                    remain=(i.freeze - total - fee)
                    if i.deal == Direction.BUY
                    else (total - fee),
                    freeze=i.freeze,
                    done=True,
                )
                result.append(f)

            if isinstance(last_price[i.code], Min5Bar):
                print("Min5数据的处理，TODO")
                pass
            if isinstance(last_price[i.code], CurrentPrice):
                print("即时数据处理，TODO")
                pass
        self.clear_match_list()
        return result
