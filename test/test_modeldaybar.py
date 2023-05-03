import unittest
import time
import datetime
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_daybar import MDaybar
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF


class ModelDaybarTest(unittest.TestCase):
    """
    UnitTest for Daybar.
    """

    # Init
    # set data from bar
    # store in to ginkgodata
    # query from ginkgodata

    def __init__(self, *args, **kwargs) -> None:
        super(ModelDaybarTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode",
                "source": SOURCE_TYPES.BAOSTOCK,
                "open": 2,
                "high": 2.44,
                "low": 1,
                "close": 1.99,
                "volume": 23331,
                "timestamp": datetime.datetime.now(),
                "frequency": FREQUENCY_TYPES.DAY,
            }
        ]

    def test_ModelDaybar_Init(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MDaybar()
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_ModelDaybar_SetFromData(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            o = MDaybar()
            o.set(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
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

    def test_ModelDaybar_SetFromDataFrame(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["frequency"],
                i["timestamp"],
            )
            o = MDaybar()
            o.set(b.to_dataframe)
            o.set_source(i["source"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.open, i["open"])
            self.assertEqual(o.high, i["high"])
            self.assertEqual(o.low, i["low"])
            self.assertEqual(o.close, i["close"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.timestamp, i["timestamp"])

    def test_ModelDaybar_Insert(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        GINKGODATA.drop_table(MDaybar)
        GINKGODATA.create_table(MDaybar)
        try:
            o = MDaybar()
            GINKGODATA.add(o)
            GINKGODATA.commit()
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_ModelDaybar_BatchInsert(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        GINKGODATA.drop_table(MDaybar)
        GINKGODATA.create_table(MDaybar)
        try:
            s = []
            for i in range(10):
                o = MDaybar()
                s.append(o)
            GINKGODATA.add_all(s)
            GINKGODATA.commit()
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_ModelDaybar_Query(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        GINKGODATA.drop_table(MDaybar)
        GINKGODATA.create_table(MDaybar)
        try:
            o = MDaybar()
            GINKGODATA.add(o)
            GINKGODATA.commit()
            r = GINKGODATA.session.query(MDaybar).first()
        except Exception as e:
            result = False

        self.assertNotEqual(r, None)
        self.assertEqual(result, True)
