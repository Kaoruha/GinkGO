"""
Author: Kaoru
Date: 2022-03-22 02:09:59
LastEditTime: 2022-03-22 02:10:00
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/trade.py
What goes around comes around.
"""
from src.backtest.enums import TradeStatus


class Trade(object):
    """ """

    def __init__(self, trade_status: TradeStatus) -> None:
        self.trade_status = trade_status
