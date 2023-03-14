import unittest
from ginkgo.backtest.events import MarketEvent, SignalEvent, OrderEvent, FillEvent
from ginkgo.backtest.enums import (
    Direction,
    OrderStatus,
    OrderType,
    Source,
    MarketEventType,
)
from ginkgo.libs import GINKGOLOGGER as gl


class BarTest(unittest.TestCase):
    """
    UnitTest for bar.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventsTest, self).__init__(*args, **kwargs)

    def test_BarInit_OK(self):
        print("")
        gl.logger.warn("MarketEvent初始化测试开始.")
        param = [
            # 0datetime, 1source, 2code, 3raw, 4marketeventtype
            (
                "2020-01-02",
                Source.BACKTEST,
                "testmarket",
                "this is unitest",
                MarketEventType.NEWS,
            ),
        ]
        for i in param:
            e = MarketEvent(
                datetime=i[0], code=i[2], source=i[1], raw=i[3], market_event_type=i[4]
            )
            gl.logger.info(e)
            self.assertEqual(
                first={
                    "ismarket": True,
                    "date": i[0],
                    "code": i[2],
                    "source": i[1],
                    "raw": i[3],
                    "type": i[4],
                },
                second={
                    "ismarket": isinstance(e, MarketEvent),
                    "date": e.datetime.strftime("%Y-%m-%d"),
                    "code": e.code,
                    "source": e.source,
                    "raw": e.raw,
                    "type": e.market_event_type,
                },
            )
        gl.logger.warn("MarketEvent初始化测试完成.")
