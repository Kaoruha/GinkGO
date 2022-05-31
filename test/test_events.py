import unittest
from src.backtest.events import MarketEvent, SignalEvent, OrderEvent, FillEvent
from src.backtest.enums import (
    Direction,
    OrderStatus,
    OrderType,
    Source,
    MarketEventType,
)
from src.libs import GINKGOLOGGER as gl


class EventsTest(unittest.TestCase):
    """
    事件类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventsTest, self).__init__(*args, **kwargs)

    def test_MarketEventInit_OK(self):
        print("")
        gl.logger.critical("MarketEvent初始化测试开始.")
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
                datetime=i[0], code=i[2], source=i[1], raw=i[3], markert_event_type=i[4]
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
        gl.logger.critical("MarketEvent初始化测试完成.")

    def test_SignalEventInit_OK(self):
        print("")
        gl.logger.critical("SignalEvent初始化测试开始.")
        param = [
            # 0date, 1code, 2direction, 3source
            ("2020-01-02", "testsignal", Direction.BULL, Source.BACKTEST),
            ("2020-11-02", "testsignal2", Direction.BEAR, Source.SHLIVE),
        ]
        for i in param:
            e = SignalEvent(datetime=i[0], code=i[1], direction=i[2], source=i[3])
            gl.logger.debug(e)
            self.assertEqual(
                first={"date": i[0], "code": i[1], "direction": i[2], "source": i[3]},
                second={
                    "date": e.datetime.strftime("%Y-%m-%d"),
                    "code": e.code,
                    "direction": e.direction,
                    "source": e.source,
                },
            )
        gl.logger.critical("SignalEvent初始化测试完成.")

    def test_OrderEventInit_OK(self):
        print("")
        gl.logger.critical("OrderEvent初始化测试开始.")
        param = [
            # 0date, 1code, 2direction, 3source, 4type, 5price, 6volume
            (
                "2020-01-01",
                "testorder:sh.600001",
                Direction.BULL,
                Source.BACKTEST,
                OrderType.LIMIT,
                2.2,
                1000,
            ),
            (
                "2020-01-02",
                "testorder:sh.600002",
                Direction.BEAR,
                Source.STRATEGY,
                OrderType.LIMIT,
                2.2,
                1000,
            ),
        ]
        for i in param:
            e = OrderEvent(
                datetime=i[0],
                code=i[1],
                direction=i[2],
                source=i[3],
                order_type=i[4],
                price=i[5],
                volume=i[6],
            )
            gl.logger.info(e)
            self.assertEqual(
                first={
                    "date": i[0],
                    "code": i[1],
                    "dir": i[2],
                    "source": i[3],
                    "type": i[4],
                    "price": i[5],
                    "volume": i[6],
                    "status": OrderStatus.CREATED,
                },
                second={
                    "date": e.datetime.strftime("%Y-%m-%d"),
                    "code": e.code,
                    "dir": e.direction,
                    "source": e.source,
                    "type": e.order_type,
                    "price": e.price,
                    "volume": e.volume,
                    "status": e.status,
                },
            )
        gl.logger.critical("OrderEvent初始化测试完成.")

    def test_FillEventInit_OK(self):
        print("")
        gl.logger.critical("FillEvent初始化测试开始.")
        param = [
            # 0date, 1code, 2direction, 3price, 4volume, 5source, 6fee
            ("2000-01-01", "testfill", Direction.BULL, 2.0, 100, Source.BACKTEST, 11.2),
        ]
        for i in param:
            e = FillEvent(
                datetime=i[0],
                code=i[1],
                direction=i[2],
                price=i[3],
                volume=i[4],
                source=i[5],
                fee=i[6],
            )
            gl.logger.info(e)
            self.assertEqual(
                first={
                    "date": i[0],
                    "code": i[1],
                    "direction": i[2],
                    "price": i[3],
                    "volume": i[4],
                    "source": i[5],
                    "fee": i[6],
                },
                second={
                    "date": e.datetime.strftime("%Y-%m-%d"),
                    "code": e.code,
                    "direction": e.direction,
                    "price": e.price,
                    "volume": e.volume,
                    "source": e.source,
                    "fee": e.fee,
                },
            )
        gl.logger.critical("FillEvent初始化测试完成.")
