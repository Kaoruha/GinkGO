import unittest
import time
import datetime
import pandas as pd
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo import GCONF, GLOG
from ginkgo.data.models import MSignal


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
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])

    def test_ModelSignal_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])
            o.set(i["code"], i["direction"], i["timestamp"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelSignal_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MSignal)
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
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MSignal)
        GDATA.create_table(MSignal)
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])
            o.set(i["code"], i["direction"], i["timestamp"])
            GDATA.add(o)
            GDATA.commit()

    def test_ModelSignal_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelSignal_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MSignal)
        GDATA.create_table(MSignal)
        o = MSignal()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MSignal).first()
        self.assertNotEqual(r, None)
