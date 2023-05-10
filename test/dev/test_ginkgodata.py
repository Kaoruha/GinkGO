import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data.models import MCodeOnTrade


class GinkgoDataTest(unittest.TestCase):
    """
    UnitTest for GinkgoData.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(GinkgoDataTest, self).__init__(*args, **kwargs)

    def test_GinkgoData_GetCodeList(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)

    def test_GinkgoData_InsertCodeList(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
        count = 20
        df = pd.DataFrame()
        for i in range(count):
            item = MCodeOnTrade()
            df = pd.concat([df, item.to_dataframe().T], axis=0)
        print(df)

    def test_GinkgoData_UpdateCodeList(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)

    def test_GinkgoData_UpdateCodeListToLatest(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)

    def test_GinkgoData_UpdateCodeListToLatestAsync(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MCodeOnTrade)
        GINKGODATA.create_table(MCodeOnTrade)
