import unittest
import pandas as pd
import datetime
from time import sleep
from ginkgo.backtest.analyzers import BaseAnalyzer
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import datetime_normalize
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MAnalyzer


class BaseAnalyzerTest(unittest.TestCase):
    """
    Unit test for Analyzer.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BaseAnalyzerTest, self).__init__(*args, **kwargs)

    def test_baseanalyzer_Init(self) -> None:
        a = BaseAnalyzer("forunittest")
        self.assertTrue(True)

    def test_baseanalyzer_SetAnalyzerID(self) -> None:
        a = BaseAnalyzer("forunittest")
        a.set_analyzer_id("test")
        self.assertEqual(a.analyzer_id, "test")

    def test_baseanalyzer_SetBaktestID(self) -> None:
        a = BaseAnalyzer("forunittest")
        a.set_backtest_id("testbacktest")
        self.assertEqual(a.backtest_id, "testbacktest")

    def test_baseanalyzer_OnTimeGoesBy(self) -> None:
        a = BaseAnalyzer("forunittest")
        date = "2020-01-01 00:00:00"
        a.on_time_goes_by(date)
        self.assertEqual(a.now, datetime_normalize(date))

    def test_baseanalyzer_add_data(self) -> None:
        a = BaseAnalyzer("forunittest")
        a.add_data(1)
        self.assertEqual(0, a.value.shape[0])
        date = "2020-01-01 00:00:00"
        a.on_time_goes_by(date)
        a.add_data(1)
        self.assertEqual(1, a.value.shape[0])

    def test_baseanalyzer_get_data(self) -> None:
        a = BaseAnalyzer("forunittest")
        a.add_data(1.55)
        self.assertEqual(0, a.value.shape[0])
        date = "2020-01-01 00:00:00"
        a.on_time_goes_by(date)
        a.add_data(1.66)
        self.assertEqual(1, a.value.shape[0])
        self.assertEqual(1.66, a.get_data(date))

    def test_baseanalyzer_Insert(self) -> None:
        a = BaseAnalyzer("forunittest")
        date = "2020-01-01 00:00:00"
        a.on_time_goes_by(date)
        a.set_analyzer_id("testid")
        a.add_data(1.66)
        size0 = GDATA.get_table_size(MAnalyzer)
        a.add_record()
        size1 = GDATA.get_table_size(MAnalyzer)
        self.assertEqual(1, size1 - size0)
