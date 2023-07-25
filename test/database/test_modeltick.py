import unittest
import time
import datetime
import pandas as pd
from ginkgo.backtest.tick import Tick
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models.model_tick import MTick
from ginkgo.enums import SOURCE_TYPES
from ginkgo import GCONF, GLOG


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
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_ModelTick_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            item = MTick()
            item.set(i["code"], i["price"], i["volume"], i["timestamp"])
            item.set_source(i["source"])
            self.assertEqual(item.code, i["code"])
            self.assertEqual(item.price, i["price"])
            self.assertEqual(item.volume, i["volume"])
            self.assertEqual(item.timestamp, i["timestamp"])
            self.assertEqual(item.source, i["source"])

    def test_ModelTick_SetFromDataframe(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            data = {
                "code": i["code"],
                "price": i["price"],
                "volume": i["volume"],
                "timestamp": i["timestamp"],
                "source": i["source"],
            }
            tick = MTick()
            tick.set(pd.Series(data))
            tick.set_source(i["source"])

            self.assertEqual(tick.code, i["code"])
            self.assertEqual(tick.price, i["price"])
            self.assertEqual(tick.volume, i["volume"])
            self.assertEqual(tick.timestamp, i["timestamp"])
            self.assertEqual(tick.source, i["source"])

    def test_ModelTick_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MTick)
        GDATA.create_table(MTick)
        try:
            o = MTick()
            GDATA.add(o)
            GDATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelTick_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True

        GDATA.drop_table(MTick)
        GDATA.create_table(MTick)
        try:
            s = []

            for i in range(10):
                o = MTick()
                s.append(o)

            GDATA.add_all(s)
            GDATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelTick_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MTick)
        GDATA.create_table(MTick)
        o = MTick()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MTick).first()
        self.assertNotEqual(r, None)
        self.assertNotEqual(r.code, None)
