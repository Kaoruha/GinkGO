import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, MARKET_TYPES
from ginkgo.data.models import MCodeOnTrade


class GinkgoDataTest(unittest.TestCase):
    """
    UnitTest for GinkgoData.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(GinkgoDataTest, self).__init__(*args, **kwargs)

    def test_GinkgoData_GetCodeListLastdate(self) -> None:
        pass

    def test_GinkgoData_GetCodeList(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
        date = "2022-04-01"
        GINKGODATA.update_cn_codelist(date)
        rs = GINKGODATA.get_codelist(date, MARKET_TYPES.CHINA)
        self.assertEqual(rs.shape[0], 5274)

    def test_GinkgoData_InsertCodeList(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
        count = 252
        df = pd.DataFrame()
        for i in range(count):
            item = MCodeOnTrade()
            item.set(
                "halo",
                "haloo",
                True,
                MARKET_TYPES.CHINA,
                datetime.datetime.now().date(),
            )
            item.set_source(SOURCE_TYPES.TEST)
            d = item.to_dataframe()
            d = pd.DataFrame(d)
            df = pd.concat([df, d.T], axis=0)
        GINKGODATA.insert_codelist(df)
        c = GINKGODATA.get_table_size(MCodeOnTrade)
        self.assertEqual(c, count)

    def test_GinkgoData_UpdateCNCodeList(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
        date = "2023-04-21"
        GINKGODATA.update_cn_codelist(date)
        c = GINKGODATA.get_table_size(MCodeOnTrade)
        self.assertEqual(c, 5660)
        GINKGODATA.update_cn_codelist(date)
        c = GINKGODATA.get_table_size(MCodeOnTrade)
        self.assertEqual(c, 5660)

    def test_GinkgoData_UpdateCodeListPeriod(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
        start_date = "2023-04-11"
        end_date = "2023-04-21"
        GINKGODATA.update_cn_codelist_period(start_date, end_date)
        c = GINKGODATA.get_table_size(MCodeOnTrade)
        self.assertEqual(c, 50883)

    def test_GinkgoData_GetDayBarLastDate(self) -> None:
        pass

    def test_GinkgoData_GetDayBar(self) -> None:
        pass

    def test_GinkgoData_InsertDayBar(self) -> None:
        pass

    def test_GinkgoData_UpdateDayBar(self) -> None:
        pass

    def test_GinkgoData_GetMin5LastDate(self) -> None:
        pass

    def test_GinkgoData_GetMin5(self) -> None:
        pass

    def test_GinkgoData_InsertMin5(self) -> None:
        pass

    def test_GinkgoData_UpdateMin5(self) -> None:
        pass

    def test_GinkgoData_GetAdjustfactorLastDate(self) -> None:
        pass

    def test_GinkgoData_GetAdjustfactor(self) -> None:
        pass

    def test_GinkgoData_InsertAdjustfactor(self) -> None:
        pass

    def test_GinkgoData_UpdateAdjustfactor(self) -> None:
        pass
