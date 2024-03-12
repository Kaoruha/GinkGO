import unittest
import base64
import random
import time
import pandas as pd
import datetime
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MAnalyzer
from ginkgo.data.ginkgo_data import GDATA


class ModelAnalyerTest(unittest.TestCase):
    """
    Examples for UnitTests of models Analyzer
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelAnalyerTest, self).__init__(*args, **kwargs)
        self.test_count = 10
        self.params = [
            {
                "name": "profit_test",
                "backtest_id": "whatareyounongshalei",
                "value": 0.1,
                "timestamp": datetime.datetime.now(),
                "backtest_id": "whatareyounongshaleiconf",
                "analyzer_id": "profit_test",
            },
        ]

    def test_ModelAnalyzer_Init(self) -> None:
        o = MAnalyzer()

    def test_ModelAnalyzer_SetFromData(self) -> None:
        for i in self.params:
            o = MAnalyzer()
            o.set(
                i["backtest_id"],
                i["timestamp"],
                i["value"],
                i["name"],
                i["analyzer_id"],
            )
            self.assertEqual(o.backtest_id, i["backtest_id"])
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.analyzer_id, i["analyzer_id"])

    def test_ModelAnalyzer_SetFromDataFrame(self) -> None:
        pass

    def test_ModelAnalyzer_Insert(self) -> None:
        GDATA.create_table(MAnalyzer)
        for i in self.params:
            size0 = GDATA.get_table_size(MAnalyzer)
            o = MAnalyzer()
            o.set(
                i["backtest_id"],
                i["timestamp"],
                i["value"],
                i["name"],
                i["analyzer_id"],
            )
            GDATA.add(o)
            size1 = GDATA.get_table_size(MAnalyzer)
            self.assertEqual(1, size1 - size0)

    def test_ModelAnalyzer_BatchInsert(self) -> None:
        GDATA.create_table(MAnalyzer)
        times0 = random.random() * self.test_count
        times0 = int(times0)
        for j in range(times0):
            size0 = GDATA.get_table_size(MAnalyzer)
            l = []
            times = random.random() * self.test_count
            times = int(times)
            for k in range(times):
                for i in self.params:
                    o = MAnalyzer()
                    o.set(
                        i["backtest_id"],
                        i["timestamp"],
                        i["value"],
                        i["name"],
                        i["analyzer_id"],
                    )
                    l.append(o)
            GDATA.add_all(l)
            size1 = GDATA.get_table_size(MAnalyzer)
            self.assertEqual(size1 - size0, len(l))

    def test_ModelAnalyzer_Query(self) -> None:
        GDATA.create_table(MAnalyzer)
        o = MAnalyzer()
        uuid = o.uuid
        GDATA.add(o)
        r = (
            GDATA.get_driver(MAnalyzer)
            .session.query(MAnalyzer)
            .filter(MAnalyzer.uuid == uuid)
            .first()
        )
        self.assertNotEqual(r, None)
