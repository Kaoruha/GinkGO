"""
Author: Kaoru
Date: 2022-03-23 21:23:27
LastEditTime: 2022-04-16 02:54:36
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/matcher/simulate_matcher.py
What goes around comes around.
"""
import time
import queue
from src.backtest.price import Bar
from src.libs import GINKGOLOGGER as gl
from src.backtest.matcher.base_matcher import BaseMatcher
from src.backtest.enums import Direction, OrderStatus, OrderType, Source
from src.backtest.events import Event, FillEvent, OrderEvent


class SimulateMatcher(BaseMatcher):
    def __init__(
        self,
        stamp_tax_rate: float = 0.001,  # 设置印花税，默认千1
        transfer_fee_rate: float = 0.0002,  # 设置过户费,默认万2
        commission_rate: float = 0.0003,  # 交易佣金，按最高千3计算了，一般比这个低
        min_commission: float = 5,  # 最低交易佣金，交易佣金的起步价
        slippage: float = 0.02,  # 滑点
        *args,
        **kwargs,
    ):
        super(SimulateMatcher, self).__init__(
            name="回测模拟撮合",
            stamp_tax_rate=stamp_tax_rate,
            transfer_fee_rate=transfer_fee_rate,
            commission_rate=commission_rate,
            min_commission=min_commission,
            args=args,
            kwargs=kwargs,
        )
        self._slippage = slippage
        self.match_list = {}  # 撮合结果队列

    def __repr__(self):
        stamp = self._stamp_tax_rate
        trans = self._transfer_fee_rate
        comm = self._commission_rate
        min_comm = self._min_commission
        s = f"回测模拟成交，当前印花税：「{stamp}」，过户费：「{trans}」，交易佣金：「{comm}」，最小交易佣金：「{min_comm}」"
        return s

    def get_bar(self, bar: Bar):
        """
        获取到新的Bar
        """
        # TODO 1 日期校验，只允许往后
        # 2 try match
        if bar.code in self.order_list:
            self.try_match(bar=bar)
            gl.logger.info(
                f"{self.datetime} 尝试撮合「{len(self.order_list[bar.code])}」个「{bar.code}」订单"
            )
        else:
            gl.logger.debug(f"{self.datetime} 不存在 「{bar.code}」订单，请检查代码")

    def send_order(self, order: OrderEvent) -> bool:
        """
        发送订单
        """
        code = order.code
        if order.status == OrderStatus.CREATED:
            order.status = OrderStatus.SUBMITED
            gl.logger.info(f"提交订单 {code} {order.direction}")
            return True
        else:
            gl.logger.error(f"{code} 状态异常，提交失败")
            order.status = OrderStatus.REJECTED
            return False

    def try_match(self, bar: Bar):
        """
        尝试撮合
        """
        # 从orderlist中取出order，尝试发送
        send_count = 0
        for v in self.order_list.values():
            for i in v:
                if i.status == OrderStatus.CREATED:
                    self.send_order(i)
                    send_count += 1
        gl.logger.debug(f"{self.name} 共计发出「{send_count}」个订单请求")
        # 模拟成交
        code = bar.code
        if code not in self.order_list:
            return

        count = 0
        for i in self.order_list[code]:
            gl.logger.info(f"尝试撮合「{i.uuid}」")
            if i.status == OrderStatus.SUBMITED:
                self.sim_match_order(order=i, bar=bar)
                self.order_count += 1
                count += 1
        gl.logger.info(f"{self.datetime} 尝试撮合「{count}」个「{code}」订单")

    def sim_match_order(self, order: OrderEvent, bar: Bar) -> FillEvent:
        """
        匹配
        """
        # TODO 日期校验
        order.status = OrderStatus.ACCEPTED
        if order.code != bar.code:
            gl.logger.error(
                f"{self.datetime} {self.name} {order.code} {bar.code} 撮合失败，订单与价格信息代码不符"
            )
            return
        # 1. 当出现涨停or跌停时，对应的买单与买单全部失败，存入result，修改Order状态推送回engine
        limit_up_condition = order.direction == Direction.BULL and bar.pct_change >= 9.7
        limit_down_condition = (
            order.direction == Direction.BEAR and bar.pct_change <= -9.7
        )
        info = ""
        if limit_up_condition:
            info = f"{self.datetime} {order.code}价格涨停，订单买入撮合失败"
        if limit_down_condition:
            info = f"{self.datetime} {order.code}价格跌停，订单卖出撮合失败"
        if limit_up_condition or limit_down_condition:
            gl.logger.info(info)
            order.status = OrderStatus.REJECTED
            fill = self.gen_fillevent(order=order, is_complete=False)
            self.match_list[order.uuid] = fill
            return fill

        # 2. 如果是限价委托
        p = 0
        v = 0
        avg = (bar.open_price + bar.close_price) / 2
        if order.order_type == OrderType.LIMIT:
            # 2.1. 以买入委托为例，当委托买价高于当日最低价时，则判定发生成交。
            if order.direction == Direction.BULL:
                if order.price < bar.low_price:
                    order.status = OrderStatus.REJECTED
                    fill = self.gen_fillevent(order=order, is_complete=False)
                # 当委托价格小于K线均价时，成交价即为委托价。当委托价格高于K线均价时，成交价判定为（委托价+K线均价）/2.
                else:
                    if order.price < avg:
                        p = order.price
                    else:
                        p = (order.price + avg) / 2
                    # TODO 成交数量根据当天成交量的三角分布模型判定。
                    v = order.volume
                    order.status = OrderStatus.COMPLETED
                    fill = self.gen_fillevent(
                        order=order, is_complete=True, price=p, volume=v
                    )
            # 2.2. 以卖出委托为例，当委托卖价低于当日最高价时，则判定发生成交。
            elif order.direction == Direction.BEAR:
                if order.price > bar.high_price:
                    order.status = OrderStatus.REJECTED
                    fill = self.gen_fillevent(order=order, is_complete=False)
                else:
                    p = order.price
                    # TODO 成交数量根据当天成交量的三角分布模型判定。
                    v = order.volume
                    order.status = OrderStatus.COMPLETED
                    fill = self.gen_fillevent(
                        order=order, is_complete=True, price=p, volume=v
                    )
        # 3.1. 如果是市价委托，当委托价格低于K线均价时，以委托价成交，?
        elif order.order_type == OrderType.MARKET:
            p = (bar.high_price + avg) / 2
            v = order.volume
            order.status = OrderStatus.COMPLETED
            fill = self.gen_fillevent(order=order, is_complete=True, price=p, volume=v)
        # 当委托价格高于K线均价时，（当日K线最高价+当日K线均价）/2。成交数量依然根据当天成交量的三角分布模型判定?
        self.match_list[order.uuid] = fill
        return fill

    def get_result(self) -> list:
        """
        尝试获取订单结果

        交易成功会返回FillEvent，交易失败会返回失败的FillEvent与日期更新后的Order
        """
        # 1、循环查看已提交订单的结果
        retry_count = 2
        interval = 0.1
        for v in self.order_list.values():
            for k in v:
                if k.status == OrderStatus.SUBMITED:
                    i = 0
                    while i < retry_count:
                        if k.uuid in self.match_list:
                            self.result_list.append(self.match_list[k.uuid])
                            k.status = OrderStatus.COMPLETED
                            i == retry_count
                        else:
                            i += 1
                            time.sleep(interval)
                            gl.logger.info(f"{self.datetime} 尝试获取「{k}」结果，次数「{i}」")
                else:
                    pass  # TODO bug here
        return self.result_list

    def send_to_engine(self, event: Event):
        if self.engine:
            self.engine.put(event)
        else:
            gl.logger.critical(f"{self.name} 引擎未注册")

    def clear(self):
        super().clear()
        for k, v in self.order_list:
            for i in v:
                if i.status != OrderStatus.COMPLETED:
                    i.status = OrderStatus.EXPIRED
        self.order_list = {}
        self.match_list = {}
        self.result_list = []

    def cal_price_market(
        self,
        is_bull: bool,
        target_volume: int,
        open: float,
        close: float,
        high: float,
        low: float,
    ) -> tuple:
        """
        计算市价委托的成交
        """
        p = 0
        v = 0
        limit_up_condition = is_bull and (close - open) / open >= 9.6
        limit_down_condition = (not is_bull) and (close - open) / open <= -9.6
        if limit_up_condition or limit_down_condition:
            return (p, v)

        p = (high + open / 2 + close / 2) / 2
        v = target_volume
        return (round(p, 2), v)

    def cal_price_limit(
        self,
        is_bull: bool,
        target_price: float,
        target_volume: float,
        open: float,
        close: float,
        high: float,
        low: float,
    ) -> tuple:
        """
        计算限价委托的成交
        """
        p = 0
        v = 0
        limit_up_condition = is_bull and (close - open) / open >= 9.6
        limit_down_condition = (not is_bull) and (close - open) / open <= -9.6

        price_higher_than_high = is_bull and target_price > high
        price_lower_than_low = not is_bull and target_price < low
        if (
            limit_up_condition
            or limit_down_condition
            or price_higher_than_high
            or price_lower_than_low
        ):
            return (p, v)

        # 2.1. 以买入委托为例，当委托买价高于当日最低价时，则判定发生成交。
        # 当委托价格小于K线均价时，成交价即为委托价。当委托价格高于K线均价时，成交价判定为（委托价+K线均价）/2.
        # TODO K线均价现在使用的是开盘价与收盘价的平均数，后面需要优化
        avg = (open + close) / 2
        if is_bull:
            if target_price < avg:
                p = target_price
            else:
                p = (target_price + avg) / 2
            v = target_volume  # TODO 成交数量根据当天成交量的三角分布模型判定。
        else:
            p = target_price
            v = target_volume  # TODO 成交数量根据当天成交量的三角分布模型判定。

        return (p, v)

>>>>>>> 2f8a7f13d74e950f3193f1d37d907c64d17c5147
