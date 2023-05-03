import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.tick import Tick
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_tick import MTick
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF


class ModelTickTest(unittest.TestCase):
    """
    UnitTest for ModelTick.
    """

    # Init
    # set data from dataframe
    # store in to ginkgodata
    # query from ginkgodata

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTickTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "source": SOURCE_TYPES.BAOSTOCK,
                "code": "testcode",
                "price": 2,
                "volume": 23331,
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_ModelTickInit(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            item = MTick()
            item.set(i["code"], i["price"], i["volume"], i["timestamp"])
            item.set_source(SOURCE_TYPES.SIM)
            self.assertEqual(item.code, i["code"])
            self.assertEqual(item.price, i["price"])
            self.assertEqual(item.volume, i["volume"])
            self.assertEqual(item.timestamp, i["timestamp"])

    def test_ModelTickSetFromDataframe(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            data = {
                "code": i["code"],
                "price": i["price"],
                "volume": i["volume"],
                "timestamp": i["timestamp"],
            }
            tick = MTick()
            tick.set(pd.Series(data))
            tick.set_source(SOURCE_TYPES.SIM)

            self.assertEqual(tick.code, i["code"])
            self.assertEqual(tick.price, i["price"])
            self.assertEqual(tick.volume, i["volume"])
            self.assertEqual(tick.timestamp, i["timestamp"])

    def test_ModelTickInsert(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        GINKGODATA.drop_table(MTick)
        GINKGODATA.create_table(MTick)
        try:
            o = MTick()
            GINKGODATA.add(o)
            GINKGODATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelTickBatchInsert(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True

        GINKGODATA.drop_table(MTick)
        GINKGODATA.create_table(MTick)
        try:
            s = []

            for i in range(10):
                o = MTick()
                s.append(o)

            GINKGODATA.add_all(s)
            GINKGODATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelTickQuery(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MTick)
        GINKGODATA.create_table(MTick)
        o = MTick()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        r = GINKGODATA.session.query(MTick).first()
        self.assertNotEqual(r, None)
        self.assertNotEqual(r.code, None)
