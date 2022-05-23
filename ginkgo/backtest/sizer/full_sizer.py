from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.backtest.events import SignalEvent
from ginkgo.backtest.enums import Direction
from ginkgo.backtest.postion import Position


class FullSizer(BaseSizer):
    """
    全仓，全买全卖
    """

    def cal_size(
        self, event: SignalEvent, capital: int, positions: dict[str, Position]
    ) -> tuple:
        if event.direction == Direction.BULL:
            if event.last_price <= 0:
                r = (0, event.last_price)
            else:
                r = (int(capital / event.last_price / 100) * 100, event.last_price)
        elif event.direction == Direction.BEAR:
            code = event.code
            if code in positions:
                r = (positions[code].volume, event.last_price)
            else:
                r = (0, event.last_price)
        return r
