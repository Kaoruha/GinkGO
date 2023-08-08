from ginkgo.backtest.sizers.base_sizer import BaseSizer
from ginkgo.backtest.order import Order
from ginkgo.backtest.signal import Signal
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES


class FixedSizer(BaseSizer):
    def __init__(self, ratio: float = 1, *args, **kwargs):
        super(FixedSizer, self).__init__(*args, **kwargs)
        self._ratio = ratio

    @property
    def ratio(self) -> float:
        return self._ratio

    def cal(self, signal: Signal):
        # TODO Just for test,
        # TODO Need to be overwrite
        # TODO Need to be overwrite
        # TODO Need to be overwrite
        # TODO Need to be overwrite
        o = Order()
        o.set(
            signal.code,
            signal.direction,
            ORDER_TYPES.MARKETORDER,
            ORDERSTATUS_TYPES.NEW,
            volume=1000,
            limit_price=0,
            frozen=50000,
            transaction_price=0,
            remain=0,
            fee=0,
            timestamp=self.portfolio.now,
        )
        return o
