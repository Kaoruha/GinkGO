import time
import queue
from ginkgo.backtest.price import Bar
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.matcher.base_matcher import BaseMatcher
from ginkgo.backtest.enums import Direction, OrderStatus, OrderType, Source
from ginkgo.backtest.events import Event, FillEvent, OrderEvent


class SimulateMatcher(BaseMatcher):
    """
    模拟成交
    """
    # 获取订单 -> 存入DictOrder

    # 获取Bar价格信息 -> 查询DictOrder内相关的所有订单 -> 尝试撮合TryMatch
    # 尝试撮合TryMatch -> 发送DictOrder内所有订单 -> 模拟成交SimMatch
    # 模拟成交SimMatch -> 计算得到成交结果 -> 把结果放到DictMatch里

    # 获取交易结果GetResult -> 从DictMatch里获取成交事件 -> 向Result里存入不重复的
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
        s = f"回测模拟成交，当前印花税：「{stamp}」，"
        s += f"过户费：「{trans}」，交易佣金：「{comm}」，最小交易佣金：「{min_comm}」"
        return s

    def get_bar(self, bar: Bar):
        """
        获取到新的Bar
        """
        # TODO 日期校验，只允许往后
        # 获取到最新的价格信息，遍历orderlist，尝试撮合
        if bar.code in self.order_list:
            self.try_match(bar=bar)
            gl.logger.info(
                f"{self.datetime} 尝试撮合「{len(self.order_list[bar.code])}」个「{bar.code}」订单"
            )
        else:
            gl.logger.debug(f"{self.datetime} 不存在 「{bar.code}」订单，请检查代码")

    def send_order(self, order: OrderEvent) -> bool:
        """
        将Order发送到指定券商
        return: 发送订单的结果，成功与否
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
                if self.send_order(i):
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
        模拟订单匹配
        return: 返回一个成交事件
        """
        # TODO 日期校验
        order.status = OrderStatus.ACCEPTED
        if order.code != bar.code:
            gl.logger.error(
                f"{self.datetime} {self.name} {order.code} {bar.code} 撮合失败，订单与价格信息代码不符"
            )
            return
        # 1. 当出现涨停or跌停时，对应的买单与买单全部失败，存入result，修改Order状态推送回engine
        if order.order_type == OrderType.LIMIT:
            p,v = self.cal_price_limit()
        elif order.order_type == OrderType.MARKET:
            p,v = self.cal_price_market()

        if p ==0 or v ==0:
            order.status = OrderStatus.REJECTED
            fill = self.gen_fillevent(order=order, is_complete=False)
            self.match_list[order.uuid] = fill
            return fill

        fill = self.gen_fillevent(order=order, is_complete=True, price=p, volume=v)
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
        code:str,
        is_bull: bool,
        target_volume: int,
        open_: float,
        close: float,
        high: float,
        low: float,
    ) -> tuple:
        """
        计算市价委托的成交结果

        return: tuple（成交价，成交量）
        """
        p = 0
        v = 0
        # 涨停且想买入
        limit_up_condition = is_bull and (close - open_) / open_ >= 0.096
        # 跌停且想出
        limit_down_condition = (not is_bull) and (close - open_) / open_ <= -0.096
        # 如果涨停的情况下想买，或跌停的情况下想卖，直接返回失败
        if limit_up_condition:
            info = f"{self.datetime} {code}价格涨停，市价买入撮合失败"
        if limit_down_condition:
            info = f"{self.datetime} {code}价格跌停，市价卖出撮合失败"
        if limit_up_condition or limit_down_condition:
            gl.logger.error(info)
            return (p, v)

        # 否则交易成功
        # TODO 现在成交金额是按照最高价与开盘收盘价的均价的均价，后面需要调整
        p = (high + open_ / 2 + close / 2) / 2
        # TODO 之后需要做一个成交量的计算
        v = target_volume
        return (round(p, 2), v)

    def cal_price_limit(
        self,
        code:str,
        is_bull: bool,
        target_price: float,
        target_volume: float,
        open_: float,
        close: float,
        high: float,
        low: float,
    ) -> tuple:
        """
        计算限价委托的成交结果

        return: tuple（成交价，成交量）
        """
        p = 0
        v = 0
        # 涨停且想买入
        str_dir = "买入" if is_bull else "卖出"
        limit_up_condition = is_bull and (close - open_) / open_ >= 0.096
        # 跌停且想卖出
        limit_down_condition = (not is_bull) and (close - open_) / open_ <= -0.096

        # 目标价格高于最高价
        price_higher_than_high = is_bull and target_price > high
        # 目标价格低于最低价
        price_lower_than_low = not is_bull and target_price < low

        if limit_up_condition:
            info = f"{self.datetime} {code}价格涨停，限价{str_dir}撮合失败"
        if limit_down_condition:
            info = f"{self.datetime} {code}价格涨停，限价{str_dir}撮合失败"
        if price_higher_than_high:
            info = f"{self.datetime} {code}目标价格高于最高价，限价{str_dir}撮合失败"
        if price_lower_than_low:
            info = f"{self.datetime} {code}目标价格低于最低价，限价{str_dir}撮合失败"
        if (
            limit_up_condition
            or limit_down_condition
            or price_higher_than_high
            or price_lower_than_low
        ):
            gl.logger.error(info)
            return (p, v)

        # 成交
        # 当委托价格小于K线均价时，成交价即为委托价。
        # 当委托价格高于K线均价时，成交价判定为（委托价+K线均价）/2.
        
        # TODO K线均价现在使用的是开盘价与收盘价的平均数，后面需要优化
        
        avg = (open_ + close) / 2

        # 采用比较保守的成交策略，会提高买价，降低卖价
        if is_bull:
            # 买入的话，如果高于今日均价，就按目标价成交
            # 如果低于今日均价则按均价与目标价的均值成交，会提高买价
            if target_price > avg:
                p = target_price
            else:
                p = (target_price + avg) / 2
            v = target_volume  # TODO 成交数量根据当天成交量的三角分布模型判定。
        else:
            # 卖出的话，如果低于今日均价，就按目标价成交
            # 如果高于今日均价则按均价与目标价的均值成交，会降低卖价
            print(111)
            if target_price < avg:
                p = target_price
            else:
                p = (target_price + avg) / 2
            v = target_volume  # TODO 成交数量根据当天成交量的三角分布模型判定。

        return (p, v)
