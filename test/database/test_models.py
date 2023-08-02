import unittest
import time
import pandas as pd
import datetime

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
        GDATA.drop_table(MBar)
        GDATA.create_table(MBar)
        o = MBar()
        GDATA.add(o)
        GDATA.commit()

    def test_ModelBar_BatchInsert(self) -> None:
        GDATA.drop_table(MBar)
        GDATA.create_table(MBar)
        s = []
        for i in range(10):
            o = MBar()
            s.append(o)
        GDATA.add_all(s)
        GDATA.commit()

    def test_ModelBar_Query(self) -> None:
        GDATA.drop_table(MBar)
        GDATA.create_table(MBar)
        o = MBar()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MBar).first()
        self.assertNotEqual(r, None)


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
        GDATA.drop_table(MAdjustfactor)
        GDATA.create_table(MAdjustfactor)
        for i in self.params:
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

    def test_ModelAdjustfactor_BatchInsert(self) -> None:
        GDATA.drop_table(MAdjustfactor)
        GDATA.create_table(MAdjustfactor)
        l = []
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

    def test_ModelAdjustfactor_Query(self) -> None:
        GDATA.drop_table(MAdjustfactor)
        GDATA.create_table(MAdjustfactor)
        o = MAdjustfactor()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MAdjustfactor).first()
        self.assertNotEqual(r, None)


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
        for i in self.params:
            o = MTradeDay()

    def test_ModelTradeDay_SetFromData(self) -> None:
        for i in self.params:
            o = MTradeDay()
            o.set(i["market"], i["is_open"], i["date"])
            o.set_source(i["source"])
            self.assertEqual(o.timestamp, i["date"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTradeDay_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = MTradeDay()
            df = pd.DataFrame.from_dict(i, orient="index")
            o.set(df[0])
            self.assertEqual(o.timestamp, i["date"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTradeDay_Insert(self) -> None:
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        for i in self.params:
            o = MTradeDay()
            GDATA.add(o)
            GDATA.commit()

    def test_ModelTradeDay_BatchInsert(self) -> None:
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        s = []
        for i in self.params:
            o = MTradeDay()
            s.append(o)
        GDATA.add_all(s)
        GDATA.commit()

    def test_ModelTradeDay_Query(self) -> None:
        GDATA.drop_table(MTradeDay)
        GDATA.create_table(MTradeDay)
        o = MTradeDay()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MTradeDay).first()
        self.assertNotEqual(r, None)


class ModelOrderTest(unittest.TestCase):
    """
    UnitTest for Order.
    """

    # Init
    # set data from bar
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelOrderTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testordercode",
                "uuid": "uuidtestorderordertestuuid",
                "direction": DIRECTION_TYPES.LONG,
                "type": ORDER_TYPES.MARKETORDER,
                "status": ORDERSTATUS_TYPES.SUBMITTED,
                "source": SOURCE_TYPES.PORTFOLIO,
                "limit_price": 10.12,
                "volume": 2000,
                "frozen": 20240,
                "transaction_price": 0,
                "remain": 0,
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_ModelOrder_Init(self) -> None:
        for i in self.params:
            o = MOrder()
            o.set_source(i["source"])

    def test_ModelOrder_SetFromData(self) -> None:
        for i in self.params:
            o = MOrder()
            o.set_source(i["source"])
            o.set(
                i["uuid"],
                i["code"],
                i["direction"],
                i["type"],
                i["status"],
                i["volume"],
                i["limit_price"],
                i["frozen"],
                i["transaction_price"],
                i["remain"],
                i["timestamp"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelOrder_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = MOrder()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.set(df)
            o.set_source(i["source"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelOrder_Insert(self) -> None:
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        o = MOrder()
        GDATA.add(o)
        GDATA.commit()

    def test_ModelOrder_BatchInsert(self) -> None:
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        s = []
        for i in range(10):
            o = MOrder()
            s.append(o)

        GDATA.add_all(s)
        GDATA.commit()

    def test_ModelOrder_Query(self) -> None:
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        o = MOrder()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MOrder).first()
        self.assertNotEqual(r, None)


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
        GDATA.drop_table(MSignal)
        GDATA.create_table(MSignal)
        for i in self.params:
            o = MSignal()
            o.set_source(i["source"])
            o.set(i["code"], i["direction"], i["timestamp"])
            GDATA.add(o)
            GDATA.commit()

    def test_ModelSignal_BatchInsert(self) -> None:
        pass

    def test_ModelSignal_Query(self) -> None:
        GDATA.drop_table(MSignal)
        GDATA.create_table(MSignal)
        o = MSignal()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MSignal).first()
        self.assertNotEqual(r, None)


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
        for i in self.params:
            o = MStockInfo()

    def test_ModelStockInfo_SetFromData(self) -> None:
        for i in self.params:
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
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.code_name, i["code_name"])
            self.assertEqual(o.industry, i["industry"])
            self.assertEqual(o.currency, i["currency"])
            self.assertEqual(o.list_date, i["list_date"])
            self.assertEqual(o.delist_date, i["delist_date"])
            self.assertEqual(o.source, i["source"])

    def test_ModelStockInfo_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = MStockInfo()
            df = pd.DataFrame.from_dict(i, orient="index")
            o.set(df[0])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.code_name, i["code_name"])
            self.assertEqual(o.industry, i["industry"])
            self.assertEqual(o.currency, i["currency"])
            self.assertEqual(o.list_date, i["list_date"])
            self.assertEqual(o.delist_date, i["delist_date"])
            self.assertEqual(o.source, i["source"])

    def test_ModelStockInfo_Insert(self) -> None:
        GDATA.drop_table(MStockInfo)
        GDATA.create_table(MStockInfo)
        for i in self.params:
            o = MStockInfo()
            GDATA.add(o)
            GDATA.commit()

    def test_ModelStockInfo_BatchInsert(self) -> None:
        GDATA.drop_table(MStockInfo)
        GDATA.create_table(MStockInfo)
        s = []
        for i in self.params:
            o = MStockInfo()
            s.append(o)
        GDATA.add_all(s)
        GDATA.commit()

    def test_ModelStockInfo_Query(self) -> None:
        GDATA.drop_table(MStockInfo)
        GDATA.create_table(MStockInfo)
        o = MStockInfo()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MStockInfo).first()
        self.assertNotEqual(r, None)


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
        GDATA.drop_table(MTick)
        GDATA.create_table(MTick)
        o = MTick()
        GDATA.add(o)
        GDATA.commit()

    def test_ModelTick_BatchInsert(self) -> None:
        GDATA.drop_table(MTick)
        GDATA.create_table(MTick)
        s = []

        for i in range(10):
            o = MTick()
            s.append(o)

        GDATA.add_all(s)
        GDATA.commit()

    def test_ModelTick_Query(self) -> None:
        GDATA.drop_table(MTick)
        GDATA.create_table(MTick)
        o = MTick()
        GDATA.add(o)
        GDATA.commit()
        r = GDATA.session.query(MTick).first()
        self.assertNotEqual(r, None)
        self.assertNotEqual(r.code, None)
