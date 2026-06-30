# Upstream: PortfolioBase, ComponentFactoryService
# Downstream: BaseSizer, Signal, Order, DIRECTION_TYPES, to_decimal, _data_feeder
# Role: 比例仓位管理器，按资金比例动态计算订单仓位



import datetime
from decimal import Decimal
from typing import Tuple, Optional


from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.entities import Order, Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import to_decimal, GLOG


class RatioSizer(BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    """
    RatioSizer, dynamically calculate order size based on cash ratio.
    """
    __abstract__ = False

    def __init__(
        self,
        name: str = "RatioSizer",
        ratio: str = "0.1",
        commission_rate: float = 0.0003,
        commission_min: float = 5,
        stamp_tax: float = 0.001,
        *args,
        **kwargs,
    ):
        """
        Args:
            ratio(str): Ratio of available cash to use for each order (e.g. "0.1" = 10%).
            commission_rate(float): 手续费率，默认对齐 SimBroker (0.0003)。
            commission_min(float): 最小手续费（元），默认对齐 SimBroker (5)。
            stamp_tax(float): 印花税率（仅卖出收取），默认 0.001；买入估算不计。
        """
        super().__init__(name, *args, **kwargs)
        self._ratio = float(ratio)
        self._commission_rate = Decimal(str(commission_rate))
        self._commission_min = Decimal(str(commission_min))
        self._stamp_tax = Decimal(str(stamp_tax))

    @property
    def ratio(self) -> float:
        return self._ratio

    def _estimate_cost(self, last_price: Decimal, size: int) -> Decimal:
        """
        估算订单资金占用：成交额 + 手续费（与 SimBroker sim_broker.py:456-457 一致）。

        手续费 = max(成交额 × commission_rate, commission_min)；
        印花税仅在卖出收取，买入（LONG）估算不计（stamp_tax 预留给卖出场景）。
        """
        price = to_decimal(last_price)
        transaction_money = price * size
        commission = transaction_money * self._commission_rate
        if commission < self._commission_min:
            commission = self._commission_min
        return transaction_money + commission

    def calculate_order_size(
        self, ratio: float, last_price: Decimal, cash: Decimal, *args, **kwargs
    ) -> Tuple[int, Decimal]:
        """
        Calculate the order size based on cash ratio.
        """
        budget = to_decimal(cash) * Decimal(str(ratio))
        # 粗估可买股数上限（忽略手续费，偏大），后续循环按真实成本递减校正
        size = int(budget / to_decimal(last_price))
        size = (size // 100) * 100  # round down to nearest 100 (A-share lot size)
        while size > 0:
            planned_cost = self._estimate_cost(last_price, size)
            if budget >= planned_cost:
                return (size, planned_cost)
            size -= 100
        return (0, 0)

    def cal(self, portfolio_info, signal: Signal, *args, **kwargs) -> Optional[Order]:
        """
        Calculate the order size based on cash ratio.
        """
        if signal is None or not signal.is_valid():
            GLOG.ERROR(f"Sizer:{self.name} received invalid signal")
            return None

        if portfolio_info is None or "positions" not in portfolio_info or "cash" not in portfolio_info:
            GLOG.ERROR(f"Sizer:{self.name} received invalid portfolio_info")
            return None

        try:
            code = signal.code
            direction = signal.direction

            if direction == DIRECTION_TYPES.SHORT and code not in portfolio_info["positions"]:
                GLOG.DEBUG(f"Position {code} does not exist. Skip short signal.")
                return None

            current_time = self.get_time_provider().now()

            if direction == DIRECTION_TYPES.LONG:
                # 组件边界单向流动（Selector→Strategy→Sizer→Risk）：Sizer 不直访 data 层，
                # 经注入的 _data_feeder 取价（对齐 FixedSizer 范式，#3877）。
                if self._data_feeder is None:
                    GLOG.ERROR(f"Sizer:{self.name} has no data_feeder bound")
                    return None
                last_month_day = current_time + datetime.timedelta(days=-30)
                yester_day = current_time + datetime.timedelta(days=-1)
                past_price = self._data_feeder.get_historical_data(
                    symbols=[code], start_time=last_month_day, end_time=yester_day,
                )
                if past_price is None or past_price.shape[0] == 0:
                    GLOG.CRITICAL(f"{code} has no data from {last_month_day} to {yester_day}. {current_time}")
                    return None
                last_price = to_decimal(past_price.iloc[-1]["close"])
                cash = portfolio_info["cash"]
                planned_size, planned_cost = self.calculate_order_size(self._ratio, last_price, cash)

                if planned_size == 0:
                    GLOG.DEBUG(f"No order generated. Budget insufficient. {current_time}")
                    return None

                o = self.create_order(
                    code=code,
                    direction=DIRECTION_TYPES.LONG,
                    volume=planned_size,
                    limit_price=0,
                    frozen_money=planned_cost,
                    transaction_price=0,
                    transaction_volume=0,
                    remain=planned_cost,
                    fee=0,
                    timestamp=current_time,
                    business_timestamp=signal.business_timestamp if hasattr(signal, 'business_timestamp') else current_time,
                )
            elif direction == DIRECTION_TYPES.SHORT:
                pos = portfolio_info["positions"].get(code)
                if pos is None:
                    GLOG.DEBUG(f"Position {code} does not exist. Skip short signal. {current_time}")
                    return None

                o = self.create_order(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    volume=pos.volume,
                    limit_price=0,
                    frozen_money=0,
                    frozen_volume=0,
                    transaction_price=0,
                    transaction_volume=0,
                    remain=0,
                    fee=0,
                    timestamp=current_time,
                    business_timestamp=signal.business_timestamp if hasattr(signal, 'business_timestamp') else current_time,
                )
            else:
                return None

            return o
        except Exception as e:
            GLOG.ERROR(f"Sizer:{self.name} failed to create order: {e}")
            return None
