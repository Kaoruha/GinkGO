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
from ginkgo.libs.ginkgo_logger import GLOG


class ModelSignalTest(unittest.TestCase):
    """
    Signals for UnitTests of models
    """

    # Init
    # set data from bar
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelSignalTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "halo_signal",
                "direction": DIRECTION_TYPES.LONG,
                "timestamp": datetime.datetime.now(),
                "source": SOURCE_TYPES.TEST,
            },
        ]

    def test_ModelSignal_Init(self) -> None:
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])

    def test_ModelSignal_SetFromData(self) -> None:
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])
            o.set(i["code"], i["direction"], i["timestamp"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelSignal_SetFromDataFrame(self) -> None:
        GDATA.create_table(MSignal)
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.set(df)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelSignal_Insert(self) -> None:
        GDATA.create_table(MSignal)
        times = random.random() * 500
        times = int(times)
        for j in range(times):
            print(f"ModeSignal Insert Test : {j+1}", end="\r")
            for i in self.params:
                size0 = GDATA.get_table_size(MSignal)
                o = MSignal()
                o.set_source(i["source"])
                o.set(i["code"], i["direction"], i["timestamp"])
                GDATA.add(o)
                GDATA.commit()
                size1 = GDATA.get_table_size(MSignal)
                self.assertEqual(1, size1 - size0)

    def test_ModelSignal_BatchInsert(self) -> None:
        GDATA.create_table(MSignal)
        times = random.random() * 500
        times = int(times)
        for i in range(times):
            size0 = GDATA.get_table_size(MSignal)
            print(f"ModelSignal BatchInsert Test : {i+1}", end="\r")
            count = random.random() * 500
            count = int(count)
            s = []
            for j in range(count):
                o = MSignal()
                s.append(o)
            GDATA.add_all(s)
            GDATA.commit()
            size1 = GDATA.get_table_size(MSignal)
            self.assertEqual(len(s), size1 - size0)

    def test_ModelSignal_Query(self) -> None:
        GDATA.create_table(MSignal)
        o = MSignal()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.get_driver(MSignal).session.query(MSignal).first()
        self.assertNotEqual(r, None)
