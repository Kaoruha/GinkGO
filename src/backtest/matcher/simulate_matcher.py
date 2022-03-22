import random
import queue
import time
from src.libs.ginkgo_logger import ginkgo_logger as gl
from src.backtest.matcher.base_matcher import BaseMatcher
from src.backtest.events import FillEvent
from src.backtest.enums import Direction
from src.backtest.price import DayBar
from src.backtest.events import OrderEvent


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

    def send_order(self, order: OrderEvent):
        """
        发送订单，模拟成交直接向匹配列表里添加，如果是实盘则是向券商服务发起下单API，待返回后向匹配列表添加订单
        """
        self.match_list.put(order)

    def try_match(self, order: OrderEvent):
        """
        尝试撮合
        """
        while True:
            try:
                o = self.match_list.get(block=False)
                self.match_order(o)
                self.order_count += 1
            except queue.Empty():
                break

    def match_order(self, order: OrderEvent):
        """
        匹配
        """
        # 1 拿到订单的Code
        code = order.code
        # TODO 日期校验
        # 2 找引擎要当天的日线信息
        daybar = self.engine.get_price(code=code, date=date)
        # 3 如果涨停则买入失败，直接返回失败的FillEvent
        # 4 如果跌停则卖出失败，直接返回失败的FillEvent
        # 5 其他情况则模拟交易成功，随机取开盘价与收盘价之间的一个价格，返回成功的FillEvent
        pass

    def get_result(self):
        """
        尝试获取订单结果

        交易成功会返回FillEvent，交易失败会返回失败的FillEvent与日期更新后的Order
        """
        # 1、循环拿结果队列的结果
        while True:
            try:
                r = self.result_list.get(block=False)
                # 2、构成FIllEvent推入引擎
                self.engine.put(r)
                # 3、OrderCount -1
                self.order_count -= 1
            except queue.Empty():
                # 3、如果结果队列为空，则看OrderCount数量
                # 4、如果OrderCount为0，则完成此次匹配
                if self.order_count == 0:
                    gl.info(f"{self.today} 待成交队列已空，完成今天的匹配")
                    break
                # 5、如果OrderCount不为0，就休眠5s，重复1的步骤
                elif self.order_count > 0:
                    time.sleep(5)
                    gl.info(
                        f"{self.today} 待成交队列还有{self.result_list.qsize()}个，休眠5s后重新尝试获取结果"
                    )
                elif self.order_count < 0:
                    gl.error(f"{self.today} 待成交订单数据异常，回测结果有误，请检查代码")
                    break
