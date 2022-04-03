"""
Author: Kaoru
Date: 2022-04-01 12:59:12
LastEditTime: 2022-04-01 12:59:13
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/sizer/full_sizer.py
What goes around comes around.
"""
from src.backtest.sizer.base_sizer import BaseSizer
from src.backtest.events import SignalEvent
from src.backtest.enums import Direction
from src.backtest.postion import Position


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
