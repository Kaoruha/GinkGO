import unittest
import time
import datetime
from ginkgo.backtest.events import EventSignalGeneration
from ginkgo.libs import datetime_normalize, GLOG
from ginkgo.backtest.sizers import BaseSizer, FixedSizer, ATRSizer
from ginkgo.backtest.portfolios import PortfolioT1Backtest
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.feeders import BacktestFeed
from ginkgo.backtest.signal import Signal
from ginkgo.data.models import MBar
from ginkgo.enums import DIRECTION_TYPES, FREQUENCY_TYPES
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.backtest.engines import EventEngine
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.backtest.selectors import FixedSelector
import uuid


class SizerTest(unittest.TestCase):
    """
    UnitTest for Sizer.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SizerTest, self).__init__(*args, **kwargs)

    def test_basesizer_init(self):
        s = BaseSizer()

    def test_basesizer_bindportfolio(self):
        s = BaseSizer()
        p = BasePortfolio()
        self.assertEqual(None, s.portfolio)
        s.bind_portfolio(p)
        self.assertNotEqual(None, s.portfolio)

    def test_fixedsizer_init(self):
        s = FixedSizer()

    # def test_fixedsizer_cal(self):
    #     # Store test bar
    #     code = str(uuid.uuid4())
    #     b = MBar()
    #     b.set(code, 10, 11, 9.6, 10.2, 100000, FREQUENCY_TYPES.DAY, 20200101)
    #     GDATA.add(b)
    #     # Set Portfolio
    #     p = PortfolioT1Backtest()
    #     engine = EventEngine()
    #     p.bind_engine(engine)
    #     sizer = FixedSizer(1000)
    #     p.bind_sizer(sizer)
    #     risk = BaseRiskManagement()
    #     p.bind_risk(risk)
    #     selector = FixedSelector([code])
    #     p.bind_selector(selector)
    #     feed = BacktestFeed()
    #     sizer.bind_data_feeder(feed)
    #     # selector.bind_portfolio(p)
    #     # Test
    #     feed.on_time_goes_by(20200101)
    #     p.on_time_goes_by(20200101)
    #     signal = Signal(code, DIRECTION_TYPES.LONG, 20200101)
    #     o = sizer.cal(signal)
    #     self.assertEqual(10.2 * 1.1 * 1000, o.frozen)
    #     event = EventSignalGeneration(signal)
    #     p.on_signal(event)
    #     self.assertEqual(0, p.frozen)
    #     p.on_time_goes_by(20200102)
    #     p.on_signal(event)
    #     self.assertEqual(o.frozen, p.frozen)

    def test_atrsizer_init(self):
        s = ATRSizer()

    def test_atrsizer_cal(self):
        # TODO
        pass
