import unittest
import uuid
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.backtest.order import Order
from ginkgo.backtest.strategies import StrategyBase
from ginkgo.libs.ginkgo_math import cal_fee
from ginkgo.enums import DIRECTION_TYPES, FREQUENCY_TYPES
from ginkgo.backtest.engines import BaseEngine, EventEngine
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.portfolios import PortfolioT1Backtest
from ginkgo.backtest.position import Position
from ginkgo.backtest.events import EventPriceUpdate, EventSignalGeneration
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_math import cal_fee
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.analyzers import BaseAnalyzer
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.sizers import BaseSizer, FixedSizer
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.backtest.feeds import BaseFeed


class PortfolioBaseTest(unittest.TestCase):
    """
    UnitTest for Signal.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(PortfolioBaseTest, self).__init__(*args, **kwargs)
        self.params = [
            {},
        ]

    def test_portfolio_init(self) -> None:
        p = BasePortfolio()

    def test_portfolio_addstrategy(self) -> None:
        p = BasePortfolio()
        s = StrategyBase()
        p.add_strategy(s)
        self.assertEqual(1, len(p.strategies))
        s2 = StrategyBase()
        p.add_strategy(s2)
        self.assertEqual(2, len(p.strategies))

    def test_portfolio_addposition(self) -> None:
        p = BasePortfolio()
        pos1 = Position("test_code", 10, 1000)
        p.add_position(pos1)
        r = p.positions["test_code"]
        self.assertEqual("test_code", r.code)
        self.assertEqual(10, r.price)
        self.assertEqual(10, r.cost)
        self.assertEqual(1000, r.volume)
        pos2 = Position("test_code2", 20, 1000)
        p.add_position(pos2)
        self.assertEqual(2, len(p.positions))

    def test_portfolio_timegoes(self) -> None:
        p = BasePortfolio()
        risk = BaseRiskManagement()
        p.bind_risk(risk=risk)
        engine = BaseEngine()
        p.bind_engine(engine)
        sizer = BaseSizer()
        p.bind_sizer(sizer)
        s = FixedSelector("test_selector", ["test_code"])
        p.bind_selector(s)

        self.assertEqual(0, len(p.interested))

        p.on_time_goes_by("20200101")
        self.assertEqual(1, len(p.interested))
        self.assertEqual(datetime_normalize("20200101"), p.now)
        p.on_time_goes_by(20200103)
        self.assertEqual(1, len(p.interested))
        self.assertEqual(datetime_normalize("20200103"), p.now)
        p.on_time_goes_by(20200101)
        self.assertEqual(1, len(p.interested))
        self.assertEqual(datetime_normalize("20200103"), p.now)
        p.on_time_goes_by(20200103)
        self.assertEqual(1, len(p.interested))
        self.assertEqual(datetime_normalize("20200103"), p.now)
        p.on_time_goes_by(20200111)
        self.assertEqual(1, len(p.interested))
        self.assertEqual(datetime_normalize("20200111"), p.now)

    def test_portfolio_bindengine(self) -> None:
        p = BasePortfolio()
        e = BaseEngine()
        p.bind_engine(e)
        self.assertNotEqual(p.engine, None)

    def test_portfolio_analyzer(self) -> None:
        p = BasePortfolio()
        i = BaseAnalyzer("test_index")
        p.add_analyzer(i)
        r = None
        try:
            r = p.analyzers["test_index"]
        except Exception as e:
            pass
        self.assertNotEqual(None, r)


class PortfolioT1Test(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(PortfolioT1Test, self).__init__(*args, **kwargs)

    def test_portfoliot1_init(self) -> None:
        p = PortfolioT1Backtest()

    # def test_portfoliot1_onprice(self) -> None:
    #     p = PortfolioT1Backtest()
    #     risk = BaseRiskManagement()
    #     p.bind_risk(risk=risk)
    #     engine = EventEngine()
    #     p.bind_engine(engine)
    #     sizer = BaseSizer()
    #     p.bind_sizer(sizer)
    #     s = FixedSelector(["test_code"])
    #     p.bind_selector(s)
    #     p.on_time_goes_by("20000101")
    #     b = Bar()
    #     b.set("test_code", 10, 10.5, 9, 9.52, 1000, FREQUENCY_TYPES.DAY, "20000101")
    #     e = EventPriceUpdate(b)
    #     pos = Position("test_code", 20, 1000)
    #     p.add_position(pos)
    #     # 1. position update
    #     p.on_price_update(e)
    #     self.assertEqual(9.52, p.get_position("test_code").price)
    #     p.on_time_goes_by("20000102")
    #     b2 = Bar()
    #     b2.set("test_code", 10, 10.5, 9, 9.92, 1000, FREQUENCY_TYPES.DAY, "20000102")
    #     e2 = EventPriceUpdate(b2)
    #     p.on_price_update(e2)
    #     self.assertEqual(9.92, p.get_position("test_code").price)
    #     # 2. Strategy update
    #     # TODO

    # def test_portfoliot1_onsignal(self) -> None:
    #     code = uuid.uuid4()
    #     code = str(code)
    #     p = PortfolioT1Backtest()
    #     risk = BaseRiskManagement()
    #     p.bind_risk(risk=risk)
    #     engine = EventEngine()
    #     p.bind_engine(engine)
    #     sizer = FixedSizer(1)
    #     sizer.bind_data_feeder(BaseFeed())
    #     p.bind_sizer(sizer)
    #     s = FixedSelector([code])
    #     p.bind_selector(s)
    #     p.on_time_goes_by("20000101")
    #     signal = Signal(code, DIRECTION_TYPES.LONG, 20000101)
    #     event = EventSignalGeneration(signal)
    #     p.on_signal(event)
    #     self.assertEqual(1, len(p.signals))
    #     p.on_time_goes_by("20000102")
    #     self.assertEqual(0, len(p.signals))
    #     p.on_signal(event)
    #     self.assertEqual(0, len(p.signals))
    #     # TODO
    #     # for order_id in p.orders:
    #     #     uid = order_id.value
    #     #     orderindb = GDATA.get_order_by_id(uid)
    #     #     self.assertNotEqual(None, orderindb)
