import unittest
import datetime
import random
from ginkgo.backtest.matchmakings import (
    MatchMakingBase,
    MatchMakingSim,
    MatchMakingLive,
)
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.libs import datetime_normalize
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.order import Order
from ginkgo.data.models import MOrder
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.enums import (
    FREQUENCY_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    ATTITUDE_TYPES,
)


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

    def test_MMB_onpriceupdate(self):
        m = MatchMakingBase()
        m.on_time_goes_by("20200101")
        self.assertEqual(datetime_normalize("20200101"), m.now)
        b = Bar()
        b.set("test_code", 10, 11, 9.5, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
        e = EventPriceUpdate(price_info=b)
        self.assertEqual(0, m.price.shape[0])
        m.on_price_update(e)
        self.assertEqual(1, m.price.shape[0])

        b2 = Bar()
        b2.set(
            "test_code2", 101, 111, 91.5, 101.2, 10001, FREQUENCY_TYPES.DAY, 20200101
        )
        e2 = EventPriceUpdate(price_info=b2)
        m.on_price_update(e2)
        self.assertEqual(2, m.price.shape[0])
        m.on_price_update(e2)
        m.on_price_update(e)
        self.assertEqual(2, m.price.shape[0])

        b3 = Bar()
        b3.set(
            "test_code2", 101, 111, 91.5, 101.2, 10001, FREQUENCY_TYPES.DAY, 20190101
        )
        e3 = EventPriceUpdate(price_info=b3)
        m.on_price_update(e3)
        self.assertEqual(2, m.price.shape[0])

        b4 = Bar()
        b4.set(
            "test_code2", 101, 111, 91.5, 101.2, 10001, FREQUENCY_TYPES.DAY, 20200501
        )
        e4 = EventPriceUpdate(price_info=b4)
        m.on_price_update(e4)
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

    def test_sim_queryorder(self):
        times = random.random() * 50
        times = int(times)
        mms = MatchMakingSim()
        for i in range(times):
            print(f"MatchMaking Order Query Test: {i+1}", end="\r")
            o = MOrder()
            GDATA.add(o)
            GDATA.commit()
            r = mms.query_order(o.uuid)
            self.assertNotEqual(r, None)

    def test_sim_onstockorder(self):
        GDATA.create_table(MOrder)
        m = MatchMakingSim()
        m.on_time_goes_by(20200101)
        self.assertEqual(datetime_normalize(20200101), m.now)
        o = Order()
        o.set(
            "test_order",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            1000,
            10.5,
            1000,
            0,
            0,
            0,
            20200101,
        )
        o.set_source(SOURCE_TYPES.TEST)
        mo = MOrder()
        df = o.to_dataframe().iloc[0]
        mo.set(df)
        GDATA.add(mo)
        GDATA.commit()
        oid = o.uuid

        m.on_stock_order(oid)
        self.assertEqual(True, oid in m.orders)
        self.assertEqual(1, len(m.orders))
        m.on_stock_order(oid)
        self.assertEqual(True, oid in m.orders)
        self.assertEqual(1, len(m.orders))

        # Try past and future order
        o = Order()
        o.set(
            "test_order",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            1000,
            10.5,
            1000,
            0,
            0,
            0,
            20100101,
        )
        o.set_source(SOURCE_TYPES.TEST)
        mo = MOrder()
        df = o.to_dataframe().iloc[0]
        mo.set(df)
        GDATA.add(mo)
        GDATA.commit()
        oid = o.uuid
        m.on_stock_order(oid)
        self.assertEqual(1, len(m.orders))

        o = Order()
        o.set(
            "test_order",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            1000,
            10.5,
            1000,
            0,
            0,
            0,
            20200102,
        )
        o.set_source(SOURCE_TYPES.TEST)
        mo = MOrder()
        df = o.to_dataframe().iloc[0]
        mo.set(df)
        GDATA.add(mo)
        GDATA.commit()
        oid = o.uuid
        m.on_stock_order(oid)
        self.assertEqual(1, len(m.orders))

    def test_sim_trymatch_outofbounds(self):
        GDATA.create_table(MOrder)
        m = MatchMakingSim()
        m.on_time_goes_by(20200101)
        self.assertEqual(datetime_normalize(20200101), m.now)
        # Price Come
        b = Bar()
        b.set("test_code", 10, 11, 9.5, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
        e = EventPriceUpdate(price_info=b)
        m.on_price_update(e)
        # Order Come over the peak
        o = Order()
        o.set(
            "test_code",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            1000,
            11.5,
            1000,
            0,
            0,
            0,
            20200101,
        )
        o.set_source(SOURCE_TYPES.TEST)
        mo = MOrder()
        df = o.to_dataframe().iloc[0]
        mo.set(df)
        GDATA.add(mo)
        GDATA.commit()
        oid = o.uuid

        m.on_stock_order(oid)
        # Try match

        m.try_match()
        o1 = m.query_order(oid)
        self.assertEqual(o1.status, ORDERSTATUS_TYPES.CANCELED)

        # Price Come
        b = Bar()
        b.set("test_code1", 10, 11, 9.5, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
        e = EventPriceUpdate(price_info=b)
        m.on_price_update(e)
        # Order Come under the vallay
        o = Order()
        o.set(
            "test_code1",
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            ORDERSTATUS_TYPES.SUBMITTED,
            1000,
            9.2,
            1000,
            0,
            0,
            0,
            20200101,
        )
        o.set_source(SOURCE_TYPES.TEST)
        mo = MOrder()
        df = o.to_dataframe().iloc[0]
        mo.set(df)
        GDATA.add(mo)
        GDATA.commit()
        oid = o.uuid

        m.on_stock_order(oid)
        # Try match

        m.try_match()
        o2 = m.query_order(oid)
        self.assertEqual(o2.status, ORDERSTATUS_TYPES.CANCELED)

    def test_sim_trymatch_limitlong(self):
        GDATA.create_table(MOrder)
        times = random.random() * 50
        times = int(times)
        for i in range(times):
            print(f"SimTrymatch LimitLong Test: {i+1}", end="\r")
            m = MatchMakingSim()
            m.on_time_goes_by(20200101)
            self.assertEqual(datetime_normalize(20200101), m.now)
            # Limit LONG
            # Price Come
            b = Bar()
            b.set("test_code2", 10, 11, 9, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
            e = EventPriceUpdate(price_info=b)
            m.on_price_update(e)
            # Order Come under the vallay
            o = Order()
            o.set(
                "test_code2",
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.LIMITORDER,
                ORDERSTATUS_TYPES.SUBMITTED,
                1000,
                9.2,
                9300,
                0,
                0,
                0,
                20200101,
            )
            o.set_source(SOURCE_TYPES.TEST)
            mo = MOrder()
            df = o.to_dataframe().iloc[0]
            mo.set(df)
            GDATA.add(mo)
            GDATA.commit()
            oid = o.uuid

            m.on_stock_order(oid)
            # Try match

            m.try_match()
            o3 = m.query_order(oid)
            self.assertEqual(ORDERSTATUS_TYPES.FILLED, o3.status)
            self.assertEqual(9.2, float(o3.transaction_price))

    def test_sim_trymatch_limitshort(self):
        GDATA.create_table(MOrder)
        times = random.random() * 50
        times = int(times)
        for i in range(times):
            print(f"SimTrymatch LimitShort Test: {i+1}", end="\r")
            m = MatchMakingSim()
            m.set_attituede(ATTITUDE_TYPES.PESSMISTIC)
            m.on_time_goes_by(20200101)
            self.assertEqual(datetime_normalize(20200101), m.now)
            # Limit SHORT
            # Price Come
            b = Bar()
            b.set("test_code2", 10, 11, 9, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
            e = EventPriceUpdate(price_info=b)
            m.on_price_update(e)
            # Order Come under the vallay
            o = Order()
            o.set(
                "test_code2",
                DIRECTION_TYPES.SHORT,
                ORDER_TYPES.LIMITORDER,
                ORDERSTATUS_TYPES.SUBMITTED,
                1000,
                9.2,
                9300,
                0,
                0,
                0,
                20200101,
            )
            o.set_source(SOURCE_TYPES.TEST)
            mo = MOrder()
            df = o.to_dataframe().iloc[0]
            mo.set(df)
            GDATA.add(mo)
            GDATA.commit()
            oid = o.uuid

            m.on_stock_order(oid)
            # Try match

            m.try_match()
            o3 = m.query_order(oid)
            self.assertEqual(ORDERSTATUS_TYPES.FILLED, o3.status)
            self.assertEqual(9.2, float(o3.transaction_price))
            self.assertGreaterEqual(float(o3.transaction_price), 9.2)

    def test_sim_trymatch_marketlong(self):
        GDATA.create_table(MOrder)
        times = random.random() * 50
        times = int(times)
        for i in range(times):
            print(f"SimTrymatch MarketLong Test: {i+1}", end="\r")
            m = MatchMakingSim()
            m.set_attituede(ATTITUDE_TYPES.PESSMISTIC)
            m.on_time_goes_by(20200101)
            self.assertEqual(datetime_normalize(20200101), m.now)
            # MARKET LONG
            # Price Come
            b = Bar()
            b.set("test_code2", 10, 11, 9, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
            e = EventPriceUpdate(price_info=b)
            m.on_price_update(e)
            # Order Come under the vallay
            o = Order()
            o.set(
                "test_code2",
                DIRECTION_TYPES.LONG,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.SUBMITTED,
                1000,
                9.2,
                9300,
                0,
                0,
                0,
                20200101,
            )
            o.set_source(SOURCE_TYPES.TEST)
            mo = MOrder()
            df = o.to_dataframe().iloc[0]
            mo.set(df)
            GDATA.add(mo)
            GDATA.commit()
            oid = o.uuid

            m.on_stock_order(oid)
            # Try match

            m.try_match()
            o3 = m.query_order(oid)
            self.assertEqual(ORDERSTATUS_TYPES.FILLED, o3.status)
            self.assertNotEqual(float(o3.transaction_price), 0)
            self.assertGreaterEqual(float(o3.transaction_price), b.open)

    def test_sim_trymatch_marketshort(self):
        GDATA.create_table(MOrder)
        times = random.random() * 50
        times = int(times)
        for i in range(times):
            print(f"SimTrymatch MarketShort Test: {i+1}", end="\r")
            m = MatchMakingSim()
            m.set_attituede(ATTITUDE_TYPES.PESSMISTIC)
            m.on_time_goes_by(20200101)
            self.assertEqual(datetime_normalize(20200101), m.now)
            # MARKET SHORT
            # Price Come
            b = Bar()
            b.set("test_code2", 10, 11, 9, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
            e = EventPriceUpdate(price_info=b)
            m.on_price_update(e)
            # Order Come under the vallay
            o = Order()
            o.set(
                "test_code2",
                DIRECTION_TYPES.SHORT,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.SUBMITTED,
                1000,
                9.2,
                9300,
                0,
                0,
                0,
                20200101,
            )
            o.set_source(SOURCE_TYPES.TEST)
            mo = MOrder()
            df = o.to_dataframe().iloc[0]
            mo.set(df)
            GDATA.add(mo)
            GDATA.commit()
            oid = o.uuid

            m.on_stock_order(oid)
            # Try match

            m.try_match()
            o3 = m.query_order(oid)
            self.assertEqual(ORDERSTATUS_TYPES.FILLED, o3.status)
            self.assertNotEqual(float(o3.transaction_price), 0)
            self.assertLessEqual(float(o3.transaction_price), b.open)

    def test_sim_trymatch_marketrandom(self):
        GDATA.create_table(MOrder)
        times = random.random() * 50
        times = int(times)
        for i in range(times):
            print(f"SimTrymatch MarketRandom Test: {i+1}", end="\r")
            m = MatchMakingSim()
            m.set_attituede(ATTITUDE_TYPES.RANDOM)
            m.on_time_goes_by(20200101)
            self.assertEqual(datetime_normalize(20200101), m.now)
            # MARKET SHORT
            # Price Come
            b = Bar()
            b.set("test_code2", 10, 11, 9, 10.2, 1000, FREQUENCY_TYPES.DAY, 20200101)
            e = EventPriceUpdate(price_info=b)
            m.on_price_update(e)
            # Order Come under the vallay
            o = Order()
            o.set(
                "test_code2",
                DIRECTION_TYPES.SHORT,
                ORDER_TYPES.MARKETORDER,
                ORDERSTATUS_TYPES.SUBMITTED,
                1000,
                9.2,
                9300,
                0,
                0,
                0,
                20200101,
            )
            o.set_source(SOURCE_TYPES.TEST)
            mo = MOrder()
            df = o.to_dataframe().iloc[0]
            mo.set(df)
            GDATA.add(mo)
            GDATA.commit()
            oid = o.uuid

            m.on_stock_order(oid)
            # Try match

            m.try_match()
            o3 = m.query_order(oid)
            self.assertEqual(ORDERSTATUS_TYPES.FILLED, o3.status)
            self.assertNotEqual(float(o3.transaction_price), 0)
            self.assertLessEqual(float(o3.transaction_price), b.high)
            self.assertGreaterEqual(float(o3.transaction_price), b.low)


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

    # def test_live_onstockorder(self):
    #     pass

    def test_live_queryorder(self):
        pass
