import datetime
import uuid
import unittest

from ginkgo.backtest.feeders.base_feeder import BaseFeeder
from ginkgo.backtest.execution.portfolios.base_portfolio import BasePortfolio

from unittest.mock import MagicMock


class FeedBaseTest(unittest.TestCase):
    """
    UnitTest for BaseFeeder.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(FeedBaseTest, self).__init__(*args, **kwargs)

    def setUp(self, *args, **kwargs) -> None:
        self.feeder = BaseFeeder("TestFeeder")

    def test_feedbaseinit(self):
        f = BaseFeeder()

    def test_subscribe(self):
        p = BasePortfolio()
        self.feeder.add_subscriber(p)
        self.assertEqual(1, len(self.feeder.subscribers))
        p2 = BasePortfolio()
        self.feeder.add_subscriber(p2)
        self.assertEqual(2, len(self.feeder.subscribers))

    def test_subscribe_duplicate(self):
        # TODO
        pass

    def test_put_event_with_engine_bound(self):
        # TODO
        pass

    def test_put_event_without_engine_bound(self):
        # TODO
        pass

    def test_get_daybar_normal(self):
        # TODO
        pass

    def test_get_daybar_future_date(self):
        # TODO
        pass

    def test_get_daybar_past_date(self):
        # TODO
        pass

    def test_get_daybar_without_now_set(self):
        # TODO
        pass

    def test_get_tracked_symbols_combined(self):
        # TODO
        pass

    def test_get_tracked_symbols_with_duplicates(self):
        # TODO
        pass

    def test_get_tracked_symbols_empty(self):
        # TODO
        pass

    def test_on_time_goes_by_calls_super(self):
        # TODO
        pass

    def test_broadcast_not_implemented(self):
        # TODO
        pass

    def test_is_code_on_market_not_implemented(self):
        # TODO
        pass
