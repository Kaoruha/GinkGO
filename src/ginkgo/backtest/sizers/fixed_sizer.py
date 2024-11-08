from ginkgo.backtest.sizers.base_sizer import BaseSizer
from ginkgo.backtest.order import Order
from ginkgo.backtest.signal import Signal
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.ginkgo_data import GDATA


class FixedSizer(BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "FixedSizer", volume: str = "150", *args, **kwargs):
        super(FixedSizer, self).__init__(name, *args, **kwargs)
        self._volume = int(volume)

    @property
    def volume(self) -> float:
        return self._volume

    def cal(self, signal: Signal):
        code = signal.code
        df = GDATA.get_daybar_df(code, signal.timestamp, signal.timestamp)
        if df.shape[0] == 0:
            return
        close = df.loc[0].close
        max_price = close * 1.1
        o = Order()
        v = 0
        if signal.direction == DIRECTION_TYPES.LONG:
            o.set(
                signal.code,
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                volume=self._volume,
                limit_price=0,
                frozen=round(max_price * self._volume, 4),
                transaction_price=0,
                remain=0,
                fee=0,
                timestamp=self.now,
            )
        elif signal.direction == DIRECTION_TYPES.SHORT:
            # pos = self.portfolio.get_position(code)
            if pos is None:
                return
            GLOG.WARN("Try Generate SHORT ORDER.")
            o.set(
                signal.code,
                DIRECTION_TYPES.SHORT,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.NEW,
                volume=pos.volume,
                limit_price=0,
                frozen=0,
                transaction_price=0,
                remain=0,
                fee=0,
                timestamp=self.now,
            )
        return o
