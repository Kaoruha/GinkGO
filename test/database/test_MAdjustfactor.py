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


class ModelAdjustfactorTest(unittest.TestCase):
    """
    Examples for UnitTests of models
    """

    # Init
    # set data from bar
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelAdjustfactorTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode",
                "adjustfactor": 0.78,
                "foreadjustfactor": 0.5,
                "backadjustfactor": 0.8,
                "timestamp": datetime.datetime.now(),
            },
            {
                "code": "testcode",
                "adjustfactor": 0.71,
                "foreadjustfactor": 0.2,
                "backadjustfactor": 0.1,
                "timestamp": datetime.datetime.now(),
            },
        ]

    def test_ModelAdjustfactor_Init(self) -> None:
        o = MAdjustfactor()

    def test_ModelAdjustfactor_SetFromData(self) -> None:
        for i in self.params:
            o = MAdjustfactor()
            o.set(
                i["code"],
                i["foreadjustfactor"],
                i["backadjustfactor"],
                i["adjustfactor"],
                i["timestamp"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
            self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
            self.assertEqual(o.adjustfactor, i["adjustfactor"])

    def test_ModelAdjustfactor_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = MAdjustfactor()
            o.set(df)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
            self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
            self.assertEqual(o.adjustfactor, i["adjustfactor"])
        pass

    def test_ModelAdjustfactor_Insert(self) -> None:
        GDATA.create_table(MAdjustfactor)
        for i in self.params:
            size0 = GDATA.get_table_size(MAdjustfactor)
            o = MAdjustfactor()
            o.set(
                i["code"],
                i["foreadjustfactor"],
                i["backadjustfactor"],
                i["adjustfactor"],
                i["timestamp"],
            )
            GDATA.add(o)
            GDATA.commit()
            size1 = GDATA.get_table_size(MAdjustfactor)
            self.assertEqual(1, size1 - size0)

    def test_ModelAdjustfactor_BatchInsert(self) -> None:
        GDATA.create_table(MAdjustfactor)
        times0 = random.random() * 500
        times0 = int(times0)
        for j in range(times0):
            size0 = GDATA.get_table_size(MAdjustfactor)
            print(f"ModelAdjustfactor BatchInsert Test: {j+1}", end="\r")
            l = []
            times = random.random() * 500
            times = int(times)
            for k in range(times):
                for i in self.params:
                    o = MAdjustfactor()
                    o.set(
                        i["code"],
                        i["foreadjustfactor"],
                        i["backadjustfactor"],
                        i["adjustfactor"],
                        i["timestamp"],
                    )
                    l.append(o)
            GDATA.add_all(l)
            GDATA.commit()
            size1 = GDATA.get_table_size(MAdjustfactor)
            self.assertEqual(size1 - size0, len(l))

    def test_ModelAdjustfactor_Query(self) -> None:
        GDATA.create_table(MAdjustfactor)
        o = MAdjustfactor()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.get_driver(MAdjustfactor).session.query(MAdjustfactor).first()
        self.assertNotEqual(r, None)

    def test_ModelAdjustfactor_Update(self) -> None:
        num = random.random() * 500
        num = int(num)
        GDATA.create_table(MAdjustfactor)
        o = MAdjustfactor()
        GDATA.add(o)
        GDATA.commit()
        uuid = o.uuid
        for i in range(num):
            print(f"ModelAdjustfactor Update: {i+1}", end="\r")
            item = (
                GDATA.get_driver(MAdjustfactor)
                .session.query(MAdjustfactor)
                .filter(MAdjustfactor.uuid == uuid)
                .first()
            )
            s = random.random() * 500
            s = str(s)
            s = s.encode("ascii")
            s = base64.b64encode(s)
            s = s.decode("ascii")
            item.code = s
            GDATA.commit()
            item = (
                GDATA.get_driver(MAdjustfactor)
                .session.query(MAdjustfactor)
                .filter(MAdjustfactor.uuid == uuid)
                .first()
            )
            self.assertEqual(s, item.code)
