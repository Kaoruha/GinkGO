import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.event.price_update import EventPriceUpdate
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick


class EventPriceUpdateTest(unittest.TestCase):
    """
    UnitTest for Event Price Update.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventPriceUpdateTest, self).__init__(*args, **kwargs)

    def test_PriceUpdateInit_OK(self) -> None:
        print("")
        gl.logger.warn("PriceUpdate初始化 测试开始.")
        bars = [
            {
                "datetime": "2020-01-01 12:32:11",
                "code": "testcode",
                "o": 10.1,
                "h": 11,
                "l": 9.64,
                "c": 10.1,
                "v": 10000000,
            }
        ]
        ticks = [
            {
                "datetime": "2020-01-01 12:32:11",
                "code": "testcode",
                "price": 10.1,
                "v": 1000,
            }
        ]
        for bar in bars:
            b = Bar(
                bar["code"],
                bar["o"],
                bar["h"],
                bar["l"],
                bar["c"],
                bar["v"],
                bar["datetime"],
            )
            e = EventPriceUpdate(b)
            print(e)

        for tick in ticks:
            t = Tick(tick["code"], tick["price"], tick["v"], tick["datetime"])
            e = EventPriceUpdate(t)
            print(e)

        gl.logger.warn("PriceUpdate初始化 测试完成.")
