# Upstream: PortfolioBase, ComponentFactoryService
# Downstream: BaseSizer, Signal, Order, DIRECTION_TYPES, container, to_decimal
# Role: 比例仓位管理器，按资金比例动态计算订单仓位



import datetime
from decimal import Decimal
from typing import Tuple, Optional


from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.entities import Order, Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import to_decimal, GLOG
from ginkgo.data.containers import container


class RatioSizer(BaseSizer):
The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    """
    RatioSizer, dynamically calculate order size based on cash ratio.
    """
    __abstract__ = False

    def __init__(self, name: str = "RatioSizer", ratio: str = "0.1", *args, **kwargs):
        """
        Args:
            ratio(str): Ratio of available cash to use for each order (e.g. "0.1" = 10%).
        """
        super().__init__(name, *args, **kwargs)
        self._ratio = float(ratio)

    @property
    def ratio(self) -> float:
        return self._ratio

    def calculate_order_size(
        self, ratio: float, last_price: Decimal, cash: Decimal, *args, **kwargs
    ) -> Tuple[int, Decimal]:
        """
        Calculate the order size based on cash ratio.
        """
        budget = cash * Decimal(str(ratio))
        size = int(budget / (last_price * Decimal("1.003")))
        size = (size // 100) * 100  # round down to nearest 100 (A-share lot size)
        while size > 0:
            planned_cost = last_price * size * Decimal("1.003")
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
                last_month_day = current_time + datetime.timedelta(days=-30)
                yester_day = current_time + datetime.timedelta(days=-1)
                result = container.bar_service().get(code=code, start_date=last_month_day, end_date=yester_day)
                if not result.success or len(result.data) == 0:
                    GLOG.CRITICAL(f"{code} has no data from {last_month_day} to {yester_day}. {current_time}")
                    return None
                past_price = result.data.to_dataframe()
                if past_price.shape[0] == 0:
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
