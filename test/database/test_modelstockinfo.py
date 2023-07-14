import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GLOG
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MStockInfo
from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES
from ginkgo.libs.ginkgo_conf import GCONF


class ModelStockInfoTest(unittest.TestCase):
    """
    UnitTest for StockInfo.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelStockInfoTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode",
                "code_name": "testname",
                "industry": "test industry",
                "currency": CURRENCY_TYPES.CNY,
                "list_date": datetime.datetime.now(),
                "delist_date": datetime.datetime.now(),
                "timestamp": datetime.datetime.now(),
                "source": SOURCE_TYPES.SIM,
            },
            {
                "code": "testcode2",
                "code_name": "testname222",
                "industry": "test industry222",
                "currency": CURRENCY_TYPES.USD,
                "list_date": datetime.datetime.now(),
                "delist_date": datetime.datetime.now(),
                "timestamp": datetime.datetime.now(),
                "source": SOURCE_TYPES.SIM,
            },
        ]

    def test_ModelStockInfo_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MStockInfo()
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_ModelStockInfo_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MStockInfo()
                o.set(
                    i["code"],
                    i["code_name"],
                    i["industry"],
                    i["currency"],
                    i["list_date"],
                    i["delist_date"],
                )
                o.set_source(i["source"])
            except Exception as e:
                result = False
            self.assertEqual(result, True)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.code_name, i["code_name"])
            self.assertEqual(o.industry, i["industry"])
            self.assertEqual(o.currency, i["currency"])
            self.assertEqual(o.list_date, i["list_date"])
            self.assertEqual(o.delist_date, i["delist_date"])
            self.assertEqual(o.source, i["source"])

    def test_ModelStockInfo_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MStockInfo()
                df = pd.DataFrame.from_dict(i, orient="index")
                o.set(df[0])
            except Exception as e:
                result = False
            self.assertEqual(result, True)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.code_name, i["code_name"])
            self.assertEqual(o.industry, i["industry"])
            self.assertEqual(o.currency, i["currency"])
            self.assertEqual(o.list_date, i["list_date"])
            self.assertEqual(o.delist_date, i["delist_date"])
            self.assertEqual(o.source, i["source"])

    def test_ModelStockInfo_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MStockInfo)
        GDATA.create_table(MStockInfo)
        try:
            for i in self.params:
                o = MStockInfo()
                GDATA.add(o)
                GDATA.commit()
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_ModelStockInfo_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MStockInfo)
        GDATA.create_table(MStockInfo)
        s = []
        try:
            for i in self.params:
                o = MStockInfo()
                s.append(o)
            GDATA.add_all(s)
            GDATA.commit()
        except Exception as e:
            result = False
        self.assertEqual(result, True)

    def test_ModelStockInfo_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MStockInfo)
        GDATA.create_table(MStockInfo)
        try:
            o = MStockInfo()
            GDATA.add(o)
            GDATA.commit()
            r = GDATA.session.query(MStockInfo).first()
        except Exception as e:
            result = False

        self.assertNotEqual(r, None)
        self.assertEqual(result, True)
