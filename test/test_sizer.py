"""
Author: Kaoru
Date: 2022-03-22 22:14:51
LastEditTime: 2022-04-03 00:11:12
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/test/done/test_sizer.py
What goes around comes around.
"""


import unittest
from src.backtest.sizer.base_sizer import BaseSizer
from src.backtest.sizer.full_sizer import FullSizer
from src.backtest.postion import Position
from src.backtest.events import SignalEvent
from src.backtest.enums import *
from src.libs import GINKGOLOGGER as gl


class SizerTest(unittest.TestCase):
    """
    仓位控制类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SizerTest, self).__init__(*args, **kwargs)

    def test_FullSizerInit_OK(self):
        gl.logger.critical("FullSizer初始化测试开始.")
        param = [("testfullsizer0",), ("testfullsizer1",)]
        for i in param:
            s = FullSizer(name=i[0])
            gl.logger.info(s)
            self.assertEqual(first={"name": i[0]}, second={"name": s.name})
        gl.logger.critical("FullSizer初始化测试完成.")

    def test_FullSizerCalSize_OK(self):
        gl.logger.critical("FullSizer仓位计算测试开始.")
        s = FullSizer(name="testfullsizer")
        p = {"testposition": Position(code="testposition", cost=10, volume=1000)}
        param = [
            # 0signal, 1positions, 2capital, 3 size
            (
                SignalEvent(
                    code="testposition", direction=Direction.BULL, last_price=12
                ),
                p,
                10000,
                800,
            ),
            (
                SignalEvent(
                    code="testposition1", direction=Direction.BULL, last_price=12
                ),
                p,
                10000,
                800,
            ),
            (
                SignalEvent(
                    code="testposition", direction=Direction.BEAR, last_price=12
                ),
                p,
                10000,
                1000,
            ),
            (
                SignalEvent(
                    code="testposition1", direction=Direction.BEAR, last_price=12
                ),
                p,
                10000,
                0,
            ),
        ]
        for i in param:
            gl.logger.info(i[0])
            self.assertEqual(
                first={
                    "size": i[3],
                },
                second={"size": s.cal_size(i[0], i[2], i[1])},
            )
        gl.logger.critical("FullSizer仓位计算测试完成.")
