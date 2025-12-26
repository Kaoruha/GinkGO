import datetime
import uuid
from decimal import Decimal
from typing import Tuple, Optional


from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES
from ginkgo.libs import to_decimal
from ginkgo.data.containers import container


class FixedSizer(BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    """
    FixedSizer, set the volume for each order at a fixed amount.
    """
    __abstract__ = False

    def __init__(self, name: str = "FixedSizer", volume: str = "150", *args, **kwargs):
        """
        Args:
            volume(str): The volume of each order.
        """
        super(FixedSizer, self).__init__(name, *args, **kwargs)
        self._volume = self._convert_to_int(volume, 150)

    @property
    def volume(self) -> float:
        return self._volume

    def calculate_order_size(
        self, initial_size: int, last_price: Decimal, cash: Decimal, *args, **kwargs
    ) -> Tuple[int, Decimal]:
        """
        Calculate the order size.
        """
        size = initial_size
        while size > 0:
            last_price = to_decimal(last_price)
            planned_cost = last_price * size * Decimal("1.003")
            if cash >= planned_cost:
                return (size, planned_cost)
            size -= 100
        return (0, 0)

    def cal(self, portfolio_info, signal: Signal, *args, **kwargs) -> Optional[Order]:
        """
        Calculate the order size with improved error handling.
        """
        # 改进1：Signal验证
        if signal is None:
            self.log("ERROR", f"Sizer:{self.name} received None signal")
            return None
            
        if not signal.is_valid():
            self.log("ERROR", f"Sizer:{self.name} received invalid signal: {signal}")
            return None
        
        # 改进2：Portfolio信息验证
        if portfolio_info is None:
            self.log("ERROR", f"Sizer:{self.name} received None portfolio_info")
            return None
            
        required_fields = ["positions", "cash"]
        for field in required_fields:
            if field not in portfolio_info:
                self.log("ERROR", f"Sizer:{self.name} missing required portfolio field: {field}")
                return None
        
        self.log("DEBUG", f"Sizer:{self.name} processing signal for {signal.code}")
        
        try:
            code = signal.code
            direction = signal.direction

            # Check if the position exists
            if direction == DIRECTION_TYPES.SHORT and code not in portfolio_info["positions"].keys():
                self.log("DEBUG", f"Position {code} does not exist. Skip short signal. {self.get_time_provider().now()}")
                return None
        except Exception as e:
            self.log("ERROR", f"Sizer:{self.name} error processing signal: {e}")
            return None

        # 改进2：Order创建错误处理
        try:
            current_time = self.get_time_provider().now()
            if signal.direction == DIRECTION_TYPES.LONG:
                # If LONG, get the price info of last month, in case the data is not available, use yesterday's price
                last_month_day = current_time + datetime.timedelta(days=-30)
                yester_day = current_time + datetime.timedelta(days=-1)
                # 使用BarService的get方法
                result = container.bar_service().get(code=code, start_date=last_month_day, end_date=yester_day)
                if not result.success or len(result.data) == 0:
                    self.log(
                        "CRITICAL",
                        f"{code} has no data from {last_month_day} to {yester_day}.It should not happened. {current_time}",
                    )
                    return None
                # 转换为DataFrame
                past_price = result.data.to_dataframe()
                if past_price.shape[0] == 0:
                    self.log(
                        "CRITICAL",
                        f"{code} has no data from {last_month_day} to {yester_day}.It should not happened. {current_time}",
                    )
                    return None
                last_price = past_price.iloc[-1]["close"]
                last_price = to_decimal(last_price)
                cash = portfolio_info["cash"]
                planned_size, planned_cost = self.calculate_order_size(self._volume, last_price, cash)
                self.log("DEBUG", f"planned_size: {planned_size}, planned_cost: {planned_cost}.")

                if planned_size == 0:
                    self.log("DEBUG", f"No order generated. {current_time}")
                    return None

                o = Order(
                    portfolio_id=portfolio_info["portfolio_id"],
                    engine_id=self.engine_id,
                    run_id=portfolio_info.get("run_id", ""),
                    code=code,
                    direction=DIRECTION_TYPES.LONG,
                    order_type=ORDER_TYPES.MARKETORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=planned_size,
                    limit_price=0,
                    frozen_money=planned_cost,
                    transaction_price=0,
                    transaction_volume=0,
                    remain=planned_cost,
                    fee=0,
                    timestamp=current_time,
                )
            elif signal.direction == DIRECTION_TYPES.SHORT:
                pos = portfolio_info["positions"].get(code)

                if pos is None:
                    self.log("DEBUG", f"Position {code} does not exist. Skip short signal. {current_time}")
                    return None

                self.log("WARN", f"Try Generate SHORT ORDER. {current_time}")

                o = Order(
                    portfolio_id=portfolio_info["portfolio_id"],
                    engine_id=self.engine_id,
                    run_id=portfolio_info.get("run_id", ""),
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    order_type=ORDER_TYPES.MARKETORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=pos.volume,
                    limit_price=0,
                    frozen_money=0,
                    frozen_volume=0,
                    transaction_price=0,
                    transaction_volume=0,
                    remain=0,
                    fee=0,
                    timestamp=current_time,
                )
            return o
        except Exception as e:
            self.log("ERROR", f"Sizer:{self.name} failed to create order: {e}")
            return None
