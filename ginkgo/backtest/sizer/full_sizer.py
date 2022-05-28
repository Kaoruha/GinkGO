from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.backtest.events import SignalEvent
from ginkgo.backtest.enums import Direction
from ginkgo.backtest.postion import Position


class FullSizer(BaseSizer):
    """
    全仓，全买全卖
    """

    def cal_size(
        self, signal: SignalEvent, capital: int, positions: dict[str, Position]
    ) -> tuple:
        if signal.direction == Direction.BULL:
            if signal.last_price <= 0:
                r = (0, signal.last_price)
            else:
                r = (int(capital / signal.last_price / 100) * 100, signal.last_price)
        elif signal.direction == Direction.BEAR:
            code = signal.code
            if code in positions:
                r = (positions[code].avaliable_volume, signal.last_price)
            else:
                r = (0, signal.last_price)
        return r  # volume, price
