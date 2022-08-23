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


class EventsTest(unittest.TestCase):
    """
    事件类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventsTest, self).__init__(*args, **kwargs)

    def test_MarketEventInit_OK(self):
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

    def test_SignalEventInit_OK(self):
        print("")
        gl.logger.warn("SignalEvent初始化测试开始.")
        param = [
            # 0date, 1code, 2direction, 3source
            ("2020-01-02", "testsignal", Direction.LONG, Source.BACKTEST),
            ("2020-11-02", "testsignal2", Direction.SHORT, Source.SHLIVE),
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
        gl.logger.warn("SignalEvent初始化测试完成.")

    def test_OrderEventInit_OK(self):
        print("")
        gl.logger.warn("OrderEvent初始化测试开始.")
        param = [
            # 0date, 1code, 2direction, 3source, 4type, 5price, 6volume
            (
                "2020-01-01",
                "testorder:sh.600001",
                Direction.LONG,
                Source.BACKTEST,
                OrderType.LIMIT,
                2.2,
                1000,
            ),
            (
                "2020-01-02",
                "testorder:sh.600002",
                Direction.SHORT,
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
                quantity=i[6],
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
                    "quantity": i[6],
                    "status": OrderStatus.CREATED,
                },
                second={
                    "date": e.datetime.strftime("%Y-%m-%d"),
                    "code": e.code,
                    "dir": e.direction,
                    "source": e.source,
                    "type": e.order_type,
                    "price": e.price,
                    "quantity": e.quantity,
                    "status": e.status,
                },
            )
        gl.logger.warn("OrderEvent初始化测试完成.")

    def test_FillEventInit_OK(self):
        print("")
        gl.logger.warn("FillEvent初始化测试开始.")
        param = [
            # 0date, 1code, 2direction, 3price, 4quantity, 5source, 6commision, 7money_remain
            ("2000-01-01", "testfill", Direction.LONG, 2.0, 100, Source.BACKTEST, 11.2),
        ]
        for i in param:
            e = FillEvent(
                datetime=i[0],
                code=i[1],
                direction=i[2],
                price=i[3],
                quantity=i[4],
                source=i[5],
                commision=i[6],
            )
            gl.logger.info(e)
            self.assertEqual(
                first={
                    "date": i[0],
                    "code": i[1],
                    "direction": i[2],
                    "price": i[3],
                    "quantity": i[4],
                    "source": i[5],
                    "commision": i[6],
                },
                second={
                    "date": e.datetime.strftime("%Y-%m-%d"),
                    "code": e.code,
                    "direction": e.direction,
                    "price": e.price,
                    "quantity": e.quantity,
                    "source": e.source,
                    "commision": e.commision,
                },
            )
        gl.logger.warn("FillEvent初始化测试完成.")
