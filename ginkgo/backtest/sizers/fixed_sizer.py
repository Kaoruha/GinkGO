from ginkgo.backtest.sizers.base_sizer import BaseSizer
from ginkgo.backtest.order import Order
from ginkgo.backtest.signal import Signal
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES


class FixedSizer(BaseSizer):
    def __init__(self, volume: int = 100, *args, **kwargs):
        super(FixedSizer, self).__init__(*args, **kwargs)
        self._volume = volume

    @property
    def volume(self) -> float:
        return self._volume

    def cal(self, signal: Signal):
        now = signal.timestamp
        code = signal.code
        df = self.feed.get_history(code, now)
        if df.shape[0] == 0:
            return
        close = df.loc[0].close
        max_price = close * 1.1
        o = Order()
        v = 0
        if signal.direction == DIRECTION_TYPES.LONG:
            o.set(
                signal.code,
                signal.direction,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                volume=self._volume,
                limit_price=0,
                frozen=max_price * self._volume,
                transaction_price=0,
                remain=0,
                fee=0,
                timestamp=now,
            )
        elif signal.direction == DIRECTION_TYPES.SHORT:
            pos = self.portfolio.get_position(code)
            o.set(
                signal.code,
                signal.direction,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                volume=pos.volume,
                limit_price=0,
                frozen=0,
                transaction_price=0,
                remain=0,
                fee=0,
                timestamp=now,
            )
        return o
