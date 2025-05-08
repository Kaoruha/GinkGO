import datetime
import uuid
from decimal import Decimal
from typing import Tuple


from ginkgo.backtest.sizers.base_sizer import BaseSizer
from ginkgo.backtest.order import Order
from ginkgo.backtest.signal import Signal
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES
from ginkgo.libs import to_decimal
from ginkgo.data import get_bars


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
        self._volume = int(volume)

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
            planned_cost = last_price * size * Decimal("1.1")
            if cash >= planned_cost:
                return (size, planned_cost)
            size -= 100
        return (0, 0)

    def cal(self, portfolio_info, signal: Signal, *args, **kwargs) -> Order:
        """
        Calculate the order size.
        """
        self.log("DEBUG", f"Analyzer:{self.name} try generated order.")
        code = signal.code
        direction = signal.direction

        # Check if the position exists
        if direction == DIRECTION_TYPES.SHORT and code not in portfolio_info["positions"].keys():
            self.log("DEBUG", f"Position {code} does not exist. Skip short signal. {self.now}")
            return
        o = Order()
        self.log("DEBUG", "init order")
        if signal.direction == DIRECTION_TYPES.LONG:
            # If LONG, get the price info of last month, in case the data is not available, use yesterday's price
            last_month_day = self.now + datetime.timedelta(days=-30)
            yester_day = self.now + datetime.timedelta(days=-1)
            past_price = get_bars(code, start_date=last_month_day, end_date=yester_day, as_dataframe=True)
            if past_price.shape[0] == 0:
                self.log(
                    "CRITICAL",
                    f"{code} has no data from {last_month_day} to {yester_day}.It should not happened. {self.now}",
                )
                return
            last_price = past_price.iloc[-1]["close"]
            last_price = to_decimal(last_price)
            cash = portfolio_info["cash"]
            planned_size, planned_cost = self.calculate_order_size(self._volume, last_price, cash)
            self.log("DEBUG", f"planned_size: {planned_size}, planned_cost: {planned_cost}.")

            if planned_size == 0:
                self.log("DEBUG", f"No order generated. {self.now}")
                return None

            o.set(
                code,
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=planned_size,
                limit_price=0,
                frozen=planned_cost,
                transaction_price=0,
                transaction_volume=0,
                remain=0,
                fee=0,
                timestamp=self.now,
                order_id=uuid.uuid4().hex,
                portfolio_id=portfolio_info["portfolio_id"],
                engine_id=self.engine_id,
            )
        elif signal.direction == DIRECTION_TYPES.SHORT:
            pos = portfolio_info["positions"].get(code)

            if pos is None:
                self.log("DEBUG", f"Position {code} does not exist. Skip short signal. {self.now}")
                return

            self.log("WARN", "Try Generate SHORT ORDER. {self.now}")

            o.set(
                code,
                direction=DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=pos.volume,
                limit_price=0,
                frozen=0,
                transaction_price=0,
                transaction_volume=0,
                remain=0,
                fee=0,
                timestamp=self.now,
                order_id="",
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
            )
        return o
