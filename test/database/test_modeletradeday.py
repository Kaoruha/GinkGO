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
        result = True
        try:
            for i in self.params:
                o = MTradeDay()
        except Exception as e:
            print(e)
            result = False
        self.assertEqual(result, True)

    def test_ModelTradeDay_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MTradeDay()
                o.set(i["market"], i["is_open"], i["date"])
                o.set_source(i["source"])
            except Exception as e:
                print(e)
                result = False
            self.assertEqual(o.timestamp, i["date"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])
        self.assertEqual(result, True)

    def test_ModelTradeDay_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MTradeDay()
                df = pd.DataFrame.from_dict(i, orient="index")
                o.set(df[0])
            except Exception as e:
                print(e)
                result = False
            self.assertEqual(o.timestamp, i["date"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])
        self.assertEqual(result, True)

    def test_ModelTradeDay_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        try:
            for i in self.params:
                o = MTradeDay()
                GDATA.add(o)
                GDATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelTradeDay_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        s = []
        try:
            for i in self.params:
                o = MTradeDay()
                s.append(o)
            GDATA.add_all(s)
            GDATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelTradeDay_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        try:
            o = MTradeDay()
            GDATA.add(o)
            GDATA.commit()
            r = GDATA.session.query(MTradeDay).first()
        except Exception as e:
            result = False

        self.assertNotEqual(r, None)
        self.assertEqual(result, True)
