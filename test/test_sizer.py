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
        print("")
        gl.logger.critical("FullSizer初始化测试开始.")
        param = [("testfullsizer0",), ("testfullsizer1",)]
        for i in param:
            s = FullSizer(name=i[0])
            gl.logger.info(s)
            self.assertEqual(first={"name": i[0]}, second={"name": s.name})
        gl.logger.critical("FullSizer初始化测试完成.")

    def test_FullSizerCalSize_OK(self):
        print("")
        gl.logger.critical("FullSizer仓位计算测试开始.")
        s = FullSizer(name="testfullsizer")
        p = {"testposition": Position(code="testposition", price=10, volume=1000)}
        for i in p:
            p[i].unfreeze_t1()
        param = [
            # 0signal, 1positions, 2capital, 3 size=(volume,price)
            (
                SignalEvent(
                    code="testposition", direction=Direction.BULL, last_price=12
                ),
                p,
                10000,
                (800, 12),
            ),
            (
                SignalEvent(
                    code="testposition1", direction=Direction.BULL, last_price=12
                ),
                p,
                10000,
                (800, 12),
            ),
            (
                SignalEvent(
                    code="testposition", direction=Direction.BEAR, last_price=12
                ),
                p,
                10000,
                (1000, 12),
            ),
            (
                SignalEvent(
                    code="testposition1", direction=Direction.BEAR, last_price=12
                ),
                p,
                10000,
                (0, 12),
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
