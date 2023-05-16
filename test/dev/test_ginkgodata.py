import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, MARKET_TYPES, FREQUENCY_TYPES
from ginkgo.data.models import MCodeOnTrade, MBar


class GinkgoDataTest(unittest.TestCase):
    """
    UnitTest for GinkgoData.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(GinkgoDataTest, self).__init__(*args, **kwargs)

    # def test_GinkgoData_GetCodeListLastdate(self) -> None:
    #     pass

    # def test_GinkgoData_GetCodeList(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     GINKGODATA.drop_table(MCodeOnTrade)
    #     GINKGODATA.create_table(MCodeOnTrade)
    #     date = "2022-04-01"
    #     GINKGODATA.update_cn_codelist(date)
    #     rs = GINKGODATA.get_codelist(date, MARKET_TYPES.CHINA)
    #     self.assertEqual(rs.shape[0], 5274)

    # def test_GinkgoData_InsertCodeList(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     GINKGODATA.drop_table(MCodeOnTrade)
    #     GINKGODATA.create_table(MCodeOnTrade)
    #     count = 252
    #     df = pd.DataFrame()
    #     for i in range(count):
    #         item = MCodeOnTrade()
    #         item.set(
    #             "halo",
    #             "haloo",
    #             True,
    #             MARKET_TYPES.CHINA,
    #             datetime.datetime.now().date(),
    #         )
    #         item.set_source(SOURCE_TYPES.TEST)
    #         d = item.to_dataframe()
    #         d = pd.DataFrame(d)
    #         df = pd.concat([df, d.T], axis=0)
    #     GINKGODATA.insert_codelist(df)
    #     c = GINKGODATA.get_table_size(MCodeOnTrade)
    #     self.assertEqual(c, count)

    # def test_GinkgoData_UpdateCNCodeList(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     GINKGODATA.drop_table(MCodeOnTrade)
    #     GINKGODATA.create_table(MCodeOnTrade)
    #     date = "2023-04-21"
    #     GINKGODATA.update_cn_codelist(date)
    #     c = GINKGODATA.get_table_size(MCodeOnTrade)
    #     self.assertEqual(c, 5660)
    #     GINKGODATA.update_cn_codelist(date)
    #     c = GINKGODATA.get_table_size(MCodeOnTrade)
    #     self.assertEqual(c, 5660)

    # def test_GinkgoData_UpdateCodeListPeriod(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     GINKGODATA.drop_table(MCodeOnTrade)
    #     GINKGODATA.create_table(MCodeOnTrade)
    #     # start_date = "1990-12-15"
    #     # end_date = "1992-08-06"
    #     start_date = "2023-04-11"
    #     end_date = "2023-04-21"
    #     GINKGODATA.update_cn_codelist_period(start_date, end_date)
    #     c = GINKGODATA.get_table_size(MCodeOnTrade)
    #     self.assertEqual(c, 50883)

    # def test_GinkgoData_UpdateCNCodeListToLatest_Entire(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     # GINKGODATA.drop_table(MCodeOnTrade)
    #     GINKGODATA.create_table(MCodeOnTrade)
    #     GINKGODATA.update_cn_codelist_to_latest_entire()
    #     c = GINKGODATA.get_table_size(MCodeOnTrade)
    #     self.assertGreater(c, 200000)

    def test_GinkgoData_UpdateCNCodeListToLatestAsync(self) -> None:
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
        GINKGODATA.update_cn_codelist_to_latest_entire_async()

    # def test_GinkgoData_GetBarLastDate(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     # Fake1
    #     GINKGODATA.drop_table(MBar)
    #     GINKGODATA.create_table(MBar)
    #     b = MBar()
    #     b.set("halo", 1.1, 1.7, 1, 1.5, 10000, FREQUENCY_TYPES.DAY, "2022-01-31")
    #     GINKGODATA.add(b)
    #     GINKGODATA.commit()
    #     b = MBar()
    #     b.set("halo", 1.1, 1.7, 1, 1.5, 10000, FREQUENCY_TYPES.DAY, "2022-02-11")
    #     GINKGODATA.add(b)
    #     GINKGODATA.commit()
    #     t = GINKGODATA.get_bar_lastdate("halo", FREQUENCY_TYPES.DAY)
    #     self.assertEqual(t.strftime("%Y-%m-%d"), "2022-02-11")
    #     # Fake1
    #     GINKGODATA.drop_table(MBar)
    #     GINKGODATA.create_table(MBar)
    #     b = MBar()
    #     b.set("halo", 1.1, 1.7, 1, 1.5, 10000, FREQUENCY_TYPES.DAY, "2022-02-11")
    #     GINKGODATA.add(b)
    #     GINKGODATA.commit()
    #     b = MBar()
    #     b.set("halo", 1.1, 1.7, 1, 1.5, 10000, FREQUENCY_TYPES.DAY, "2022-01-31")
    #     GINKGODATA.add(b)
    #     GINKGODATA.commit()
    #     t = GINKGODATA.get_bar_lastdate("halo", FREQUENCY_TYPES.DAY)
    #     self.assertEqual(t.strftime("%Y-%m-%d"), "2022-02-11")

    # def test_GinkgoData_GetBar(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)

    # def test_GinkgoData_InsertBar(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     GINKGODATA.drop_table(MBar)
    #     GINKGODATA.create_table(MBar)
    #     # Fake the dataframe
    #     count = 10
    #     rs = []
    #     for i in range(count):
    #         item = MBar()
    #         item.set(
    #             "halo" + str(i),
    #             1.1,
    #             1.7,
    #             1,
    #             1.5,
    #             10000,
    #             FREQUENCY_TYPES.DAY,
    #             "2022-01-31",
    #         )
    #         rs.append(item.to_dataframe())
    #     df = pd.DataFrame(rs)
    #     GINKGODATA.insert_bar(df)
    #     c = GINKGODATA.get_table_size(MBar)
    #     self.assertEqual(c, count)

    #     GINKGODATA.drop_table(MBar)
    #     GINKGODATA.create_table(MBar)
    #     # Will Check the duplicate record.
    #     count = 10
    #     rs = []
    #     for i in range(count):
    #         item = MBar()
    #         item.set(
    #             "halo",
    #             1.1,
    #             1.7,
    #             1,
    #             1.5,
    #             10000,
    #             FREQUENCY_TYPES.DAY,
    #             "2022-01-31",
    #         )
    #         rs.append(item.to_dataframe())
    #     df = pd.DataFrame(rs)
    #     GINKGODATA.insert_bar(df)
    #     c = GINKGODATA.get_table_size(MBar)
    #     self.assertEqual(c, 1)

    # def test_GinkgoData_UpdateBarFast(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     GINKGODATA.drop_table(MBar)
    #     GINKGODATA.create_table(MBar)
    #     code = "sh.000001"
    #     GINKGODATA.update_bar_to_latest_fast(code, FREQUENCY_TYPES.DAY)
    #     today = datetime.datetime.now()
    #     lastday = GINKGODATA.get_bar_lastdate(code, FREQUENCY_TYPES.DAY)
    #     self.assertGreater(datetime.timedelta(days=10), lastday - today)

    # def test_GinkgoData_UpdateBarEntireAsync(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     # GINKGODATA.drop_table(MBar)
    #     GINKGODATA.create_table(MBar)
    #     GINKGODATA.update_bar_to_latest_entire_async()

    # def test_GinkgoData_GetMin5LastDate(self) -> None:
    #     pass

    # def test_GinkgoData_GetMin5(self) -> None:
    #     pass

    # def test_GinkgoData_InsertMin5(self) -> None:
    #     pass

    # def test_GinkgoData_UpdateMin5(self) -> None:
    #     pass

    # def test_GinkgoData_GetAdjustfactorLastDate(self) -> None:
    #     pass

    # def test_GinkgoData_GetAdjustfactor(self) -> None:
    #     pass

    # def test_GinkgoData_InsertAdjustfactor(self) -> None:
    #     pass

    # def test_GinkgoData_UpdateAdjustfactor(self) -> None:
    #     pass
