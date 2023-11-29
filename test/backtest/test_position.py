import unittest
import time
import datetime
import pandas as pd
from ginkgo.backtest.position import Position
from ginkgo.enums import ORDER_TYPES, DIRECTION_TYPES, SOURCE_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.ginkgo_data import GDATA


class PositionTest(unittest.TestCase):
    """
    UnitTest for order.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(PositionTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "code": "test_position",
                "price": 10.2,
                "volume": 1000,
            },
            {
                "code": "test_position2",
                "price": 20.2,
                "volume": 1000,
            },
        ]

    def test_Position_Init(self) -> None:
        for i in self.params:
            o = Position()

    def test_position_setfromdata(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            self.assertEqual(i["code"], o.code)
            self.assertEqual(i["price"], o.price)
            self.assertEqual(i["price"], o.cost)
            self.assertEqual(0, o.fee)
            self.assertEqual(0, o.profit)

    def test_position_priceupdate(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o.on_price_update(0)
            self.assertEqual(0, o.price)
            self.assertEqual((o.price - o.cost) * o.volume, o.profit)

    def test_position_freeze(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o.freeze(200)
            self.assertEqual(200, o.frozen)

    def test_position_unfreeze(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o.freeze(200)
            self.assertEqual(200, o.frozen)
            o.unfreeze(100)
            self.assertEqual(100, o.frozen)

    def test_position_buysuccess(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o._bought(10, 1000)
            self.assertEqual((10 + i["price"]) / 2, o.cost)
            self.assertEqual(10, o.price)
            self.assertEqual(1000 + i["volume"], o.volume)

    def test_position_sellsuccess(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o.freeze(500)
            o._sold(10, 500)
            self.assertEqual(i["price"], o.cost)
            self.assertEqual(10, o.price)
            self.assertEqual(i["volume"] - 500, o.volume)

    def test_position_deal(self) -> None:
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o.deal(DIRECTION_TYPES.LONG, 10, 1000)
            self.assertEqual((10 + i["price"]) / 2, o.cost)
            self.assertEqual(10, o.price)
            self.assertEqual(1000 + i["volume"], o.volume)
        for i in self.params:
            o = Position()
            o.set(i["code"], i["price"], i["volume"])
            o.freeze(500)
            o.deal(DIRECTION_TYPES.SHORT, 10, 500)
            self.assertEqual(i["price"], o.cost)
            self.assertEqual(10, o.price)
            self.assertEqual(i["volume"] - 500, o.volume)
