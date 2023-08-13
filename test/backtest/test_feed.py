import datetime
import uuid
import unittest
from ginkgo.backtest.feeds import BaseFeed, BarFeed
from ginkgo.backtest.portfolios import BasePortfolio, PortfolioT1Backtest
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.matchmakings import MatchMakingSim
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MBar
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.backtest.engines import EventEngine
from ginkgo.backtest.sizers import BaseSizer
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.backtest.position import Position


class FeedBaseTest(unittest.TestCase):
    """
    UnitTest for BaseFeed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(FeedBaseTest, self).__init__(*args, **kwargs)

    def test_feedbaseinit(self):
        f = BaseFeed()

    def test_subscribe(self):
        f = BaseFeed()
        p = BasePortfolio()
        f.subscribe(p)
        self.assertEqual(1, len(f.subscribers))
        p2 = BasePortfolio()
        f.subscribe(p2)
        self.assertEqual(2, len(f.subscribers))


class BarFeedTest(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(BarFeedTest, self).__init__(*args, **kwargs)

    def test_barfeed_init(self):
        f = BarFeed()

    def test_barfeed_broadcast(self):
        # Put the test data into database
        code = str(uuid.uuid4())
        b = MBar()
        b.set(code, 10, 11, 9.5, 10.2, 10000, FREQUENCY_TYPES.DAY, "20200101")
        GDATA.add(b)
        GDATA.commit()
        q = GDATA.get_daybar_df(code)
        self.assertEqual(1, q.shape[0])
        # Portfolio
        p1 = PortfolioT1Backtest()
        engine = EventEngine()
        p1.bind_engine(engine)
        se = FixedSelector([code])
        p1.bind_selector(se)
        si = BaseSizer()
        p1.bind_sizer(si)
        ri = BaseRiskManagement()
        p1.bind_risk(ri)

        pos = Position(code=code, price=5, volume=100)
        p1.add_position(pos)
        pos_get = p1.get_position(code)
        self.assertNotEqual(None, pos_get)
        self.assertEqual(5, pos_get.price)
        self.assertEqual(5, pos_get.cost)
        self.assertEqual(100, pos_get.volume)

        # Broadcast test
        f = BarFeed()
        f.bind_portfolio(p1)
        f.subscribe(p1)
        ma = MatchMakingSim()
        f.subscribe(ma)
        p1.on_time_goes_by(20200101)
        ma.on_time_goes_by(20200101)
        self.assertEqual(0, ma.price.shape[0])

        f.broadcast()
        self.assertEqual(1, ma.price.shape[0])
        self.assertEqual(10.2, pos.price)
        self.assertEqual(5, pos_get.cost)
        self.assertEqual(100, pos_get.volume)
