import datetime
import uuid
import unittest
from ginkgo.backtest.feeds import BaseFeed, bar_feed


class FeedBaseTest(unittest.TestCase):
    """
    UnitTest for BaseFeed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(FeedBaseTest, self).__init__(*args, **kwargs)

    def test_feedbaseinit(self):
        pass
