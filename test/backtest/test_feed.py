import datetime
import uuid
import unittest
from ginkgo.backtest.feeds import BaseFeed, BacktestFeed
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio


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


class BacktestFeedTest(unittest.TestCase):
    """
    UnitTest for BacktestFeed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BacktestFeedTest, self).__init__(*args, **kwargs)

    def test_backtestfeedinit(self):
        f = BacktestFeed()

    def test_subscribe(self):
        f = BacktestFeed()
        p = BasePortfolio()
        f.subscribe(p)
        self.assertEqual(1, len(f.subscribers))
        p2 = BasePortfolio()
        f.subscribe(p2)
        self.assertEqual(2, len(f.subscribers))

    def test_getdaybar(self):
        pass
