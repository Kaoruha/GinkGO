import unittest
import datetime
from time import sleep
from ginkgo.backtest.matchmakings import MatchMakingBase
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.libs import datetime_normalize
from ginkgo.backtest.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES


class MatchMakingBaseTest(unittest.TestCase):
    """
    UnitTest for MatchMakingBase
    """

    # Init
    def __init__(self, *args, **kwargs) -> None:
        super(MatchMakingBaseTest, self).__init__(*args, **kwargs)

        self.params = [
            {},
        ]

    def test_MMB_init(self):
        for i in self.params:
            t = MatchMakingBase()

    def test_MMB_ontimesgoesby(self):
        m = MatchMakingBase()
        m.on_time_goes_by("20200101")
        self.assertEqual(datetime_normalize("20200101"), m.now)
        m.on_time_goes_by(20200103)
        self.assertEqual(datetime_normalize("20200103"), m.now)
        m.on_time_goes_by(20200101)
        self.assertEqual(datetime_normalize("20200103"), m.now)
        m.on_time_goes_by(20200103)
        self.assertEqual(datetime_normalize("20200103"), m.now)
        m.on_time_goes_by(20200111)
        self.assertEqual(datetime_normalize("20200111"), m.now)

    def test_MMB_onstockprice(self):
        m = MatchMakingBase()
        m.on_time_goes_by("20200101")
        self.assertEqual(datetime_normalize("20200101"), m.now)
        b = Bar()
        b.set("test_code", 10, 11, 9.5, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
        e = EventPriceUpdate(price_info=b)
        m.on_stock_price(e)
        self.assertEqual(1, m.price.shape[0])

        b2 = Bar()
        b2.set(
            "test_code2", 101, 111, 91.5, 101.2, 10001, FREQUENCY_TYPES.DAY, 20200101
        )
        e2 = EventPriceUpdate(price_info=b2)
        m.on_stock_price(e2)
        self.assertEqual(2, m.price.shape[0])
        m.on_stock_price(e2)
        m.on_stock_price(e)
        self.assertEqual(2, m.price.shape[0])

        b3 = Bar()
        b3.set(
            "test_code2", 101, 111, 91.5, 101.2, 10001, FREQUENCY_TYPES.DAY, 20190101
        )
        e3 = EventPriceUpdate(price_info=b3)
        m.on_stock_price(e3)
        self.assertEqual(2, m.price.shape[0])

        b4 = Bar()
        b4.set(
            "test_code2", 101, 111, 91.5, 101.2, 10001, FREQUENCY_TYPES.DAY, 20200501
        )
        e4 = EventPriceUpdate(price_info=b4)
        m.on_stock_price(e4)
        self.assertEqual(2, m.price.shape[0])


class MatchMakingSimTest(unittest.TestCase):
    """
    UnitTest for MatchMakingSim
    """

    # Init
    def __init__(self, *args, **kwargs) -> None:
        super(MatchMakingSimTest, self).__init__(*args, **kwargs)

        self.params = [
            {},
        ]

    def test_sim_trymatch(self):
        pass

    def test_sim_onstockorder(self, order_id):
        pass

    def test_sim_queryorder(self):
        pass


class MatchMakingLiveTest(unittest.TestCase):
    """
    UnitTest for MatchMakingLive
    """

    # Init
    def __init__(self, *args, **kwargs) -> None:
        super(MatchMakingLiveTest, self).__init__(*args, **kwargs)

        self.params = [
            {},
        ]

    def test_live_onstockorder(self):
        pass

    def test_live_queryorder(self):
        pass
