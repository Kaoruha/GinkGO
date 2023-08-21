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
from ginkgo import GLOG


class ModelBarTest(unittest.TestCase):
    """
    UnitTest for Bar.
    """

    # Init
    # set data from bar
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelBarTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode",
                "uuid": "uuid1234uuid1234",
                "source": SOURCE_TYPES.BAOSTOCK,
                "open": 2,
                "high": 2.44,
                "low": 1,
                "close": 1.99,
                "volume": 23331,
                "timestamp": datetime.datetime.now(),
                "frequency": FREQUENCY_TYPES.DAY,
                "source": SOURCE_TYPES.SIM,
            }
        ]

    def test_ModelBar_Init(self) -> None:
        for i in self.params:
            o = MBar()

    def test_ModelBar_SetFromData(self) -> None:
        for i in self.params:
            o = MBar()
            o.set(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["frequency"],
                i["timestamp"],
            )
            o.set_source(i["source"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.open, i["open"])
            self.assertEqual(o.high, i["high"])
            self.assertEqual(o.low, i["low"])
            self.assertEqual(o.close, i["close"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelBar_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = MBar()
            o.set(df)
            o.set_source(i["source"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.open, i["open"])
            self.assertEqual(o.high, i["high"])
            self.assertEqual(o.low, i["low"])
            self.assertEqual(o.close, i["close"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelBar_Insert(self) -> None:
        GDATA.create_table(MBar)
        size0 = GDATA.get_table_size(MBar)
        o = MBar()
        GDATA.add(o)
        GDATA.commit()
        size1 = GDATA.get_table_size(MBar)
        self.assertEqual(1, size1 - size0)

    def test_ModelBar_BatchInsert(self) -> None:
        GDATA.create_table(MBar)
        times = random.random() * 500
        times = int(times)
        for i in range(times):
            size0 = GDATA.get_table_size(MBar)
            print(f"ModelBar BatchInsert Test : {i+1}", end="\r")
            count = random.random() * 500
            count = int(count)
            s = []
            for j in range(count):
                o = MBar()
                s.append(o)
            GDATA.add_all(s)
            GDATA.commit()
            size1 = GDATA.get_table_size(MBar)
            self.assertEqual(count, size1 - size0)

    def test_ModelBar_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.create_table(MBar)
        o = MBar()
        o.open = 111
        GDATA.add(o)
        GDATA.commit()
        r = (
            GDATA.get_driver(MBar)
            .session.query(MBar)
            .filter(MBar.uuid == o.uuid)
            .first()
        )
        self.assertNotEqual(r, None)
