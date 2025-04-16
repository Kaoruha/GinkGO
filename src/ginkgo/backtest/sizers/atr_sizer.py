from ginkgo.backtest.sizers.base_sizer import BaseSizer
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.backtest.order import Order
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.indices.average_true_range import AverageTrueRange as ATR
from ginkgo.data import get_bars

import datetime


class ATRSizer(BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self, name: str = "ATRSizer", period: int = 14, risk: float = 0.01, risk_ratio: float = 2, *args, **kwargs
    ):
        super(ATRSizer, self).__init__(name, *args, **kwargs)
        self.period = period
        self.risk = risk
        self.risk_ratio = risk_ratio

    def set_risk(self, risk: float):
        self.risk = risk

    def cal(self, signal: Signal) -> Order:
        code = signal.code
        o = Order()
        if signal.direction == DIRECTION_TYPES.SHORT:
            # pos = self.portfolio.get_position(code)
            if pos is None:
                return None
            o.set(
                signal.code,
                direction=signal.direction,
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
                portfolio_id=self.portfolio_id,
                engine_id=self.engine_id,
            )
        if signal.direction == DIRECTION_TYPES.LONG:
            if self.now is None:
                self.log("WARN", "ATRSizer: now is None, passing the signal")
                return None
            start_date = self.now - datetime.timedelta(days=self.period + 7)
            end_date = self.now
            df = get_bars(code, start_date, end_date)
            print(df)
            atr = ATR("atr", self.period).cal(df) * self.risk_ratio
            if atr == 0:
                return None
            # max_money = self.portfolio.cash * self.risk
            max_shares = int((max_money / atr) / 100) * 100
            price = df.iloc[-1]["close"] * 1.1
            o.set(
                signal.code,
                direction=signal.direction,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=max_shares,
                limit_price=0,
                frozen=round(price * max_shares, 4),
                transaction_price=0,
                transaction_volume=0,
                remain=0,
                fee=0,
                timestamp=self.now,
                order_id="",
                portfolio_id=self.portfolio_id,
                engine_id=self.engine_id,
            )
            print("Order Generated.")
            print(o)
            o.set_source(SOURCE_TYPES.SIZER)
        return o
