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
    ) -> float:
        if event.direction == Direction.BULL:
            if event.last_price <= 0:
                r = 0
            else:
                r = int(capital / event.last_price / 100) * 100
        elif event.direction == Direction.BEAR:
            code = event.code
            if code in positions:
                r = positions[code].volume
            else:
                r = 0
        return r
