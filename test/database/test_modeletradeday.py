import unittest
import time
import datetime
import pandas as pd
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GCONF, GLOG
from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES
from ginkgo.data.models import MTradeDay
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class ModelTradeDayTest(unittest.TestCase):
    """
    Unittest for Model TradeDay
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTradeDayTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "date": datetime.datetime.now(),
                "is_open": True,
                "market": MARKET_TYPES.CHINA,
                "source": SOURCE_TYPES.SIM,
            },
            {
                "date": datetime.datetime.now(),
                "is_open": False,
                "market": MARKET_TYPES.NASDAQ,
                "source": SOURCE_TYPES.SIM,
            },
        ]

    def test_ModelTradeDay_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            o = MTradeDay()

    def test_ModelTradeDay_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            o = MTradeDay()
            o.set(i["market"], i["is_open"], i["date"])
            o.set_source(i["source"])
            self.assertEqual(o.timestamp, i["date"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTradeDay_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            o = MTradeDay()
            df = pd.DataFrame.from_dict(i, orient="index")
            o.set(df[0])
            self.assertEqual(o.timestamp, i["date"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTradeDay_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        for i in self.params:
            o = MTradeDay()
            GDATA.add(o)
            GDATA.commit()

    def test_ModelTradeDay_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        s = []
        for i in self.params:
            o = MTradeDay()
            s.append(o)
        GDATA.add_all(s)
        GDATA.commit()

    def test_ModelTradeDay_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        o = MTradeDay()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MTradeDay).first()
        self.assertNotEqual(r, None)
