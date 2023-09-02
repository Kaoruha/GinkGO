import unittest
import base64
import random
import time
import pandas as pd
import datetime
from ginkgo.libs.ginkgo_conf import GCONF

from ginkgo.enums import (
    SOURCE_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
    TICKDIRECTION_TYPES,
)

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import (
    MOrder,
    MTradeDay,
    MStockInfo,
    MSignal,
    MTick,
    MAdjustfactor,
    MBar,
)

from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GLOG


class ModelTickTest(unittest.TestCase):
    """
    UnitTest for ModelTick.
    """

    # Init
    # set data from dataframe
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTickTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "source": SOURCE_TYPES.SIM,
                "code": "testcode",
                "price": 2,
                "volume": 23331,
                "direction": TICKDIRECTION_TYPES.NOIDEA,
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_ModelTick_Init(self) -> None:
        for i in self.params:
            item = MTick()
            item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            item.set_source(i["source"])
            self.assertEqual(item.code, i["code"])
            self.assertEqual(item.price, i["price"])
            self.assertEqual(item.volume, i["volume"])
            self.assertEqual(item.timestamp, i["timestamp"])
            self.assertEqual(item.source, i["source"])

    def test_ModelTick_SetFromDataframe(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            tick = MTick()
            tick.set(df)
            tick.set_source(i["source"])

            self.assertEqual(tick.code, i["code"])
            self.assertEqual(tick.price, i["price"])
            self.assertEqual(tick.volume, i["volume"])
            self.assertEqual(tick.timestamp, i["timestamp"])
            self.assertEqual(tick.source, i["source"])

    def test_ModelTick_Insert(self) -> None:
        times = random.random() * 500
        times = int(times)
        for j in self.params:
            model = GDATA.get_tick_model(j["code"])
            GDATA.create_table(model)
            for i in range(times):
                size0 = GDATA.get_table_size(model)
                print(f"ModelTick Insert Test : {i+1}", end="\r")
                o = model()
                GDATA.add(o)
                GDATA.commit()
                size1 = GDATA.get_table_size(model)
                self.assertEqual(1, size1 - size0)

    def test_ModelTick_BatchInsert(self) -> None:
        times = random.random() * 500
        times = int(times)
        for i in self.params:
            model = GDATA.get_tick_model(i["code"])
            GDATA.create_table(model)
            for j in range(times):
                size0 = GDATA.get_table_size(model)
                print(f"ModelTick BatchInsert Test : {j+1}", end="\r")
                s = []
                count = random.random() * 500
                count = int(count)
                for i in range(count):
                    o = model()
                    s.append(o)
                GDATA.add_all(s)
                GDATA.commit()
                size1 = GDATA.get_table_size(model)
                self.assertEqual(len(s), size1 - size0)

    def test_ModelTick_Query(self) -> None:
        for i in self.params:
            model = GDATA.get_tick_model(i["code"])
            GDATA.create_table(model)
            o = model()
            GDATA.add(o)
            GDATA.commit()
            r = GDATA.get_driver(model).session.query(model).first()
            self.assertNotEqual(r, None)
