import unittest
import random
import uuid
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES, CAPITALADJUSTMENT_TYPES

from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.data.models import MCapitalAdjustment


class ModelCapitalAdjustmentTest(unittest.TestCase):
    """
    UnitTest for ModelCapitalAdjustment.
    """

    # Init
    # set data from dataframe

    def __init__(self, *args, **kwargs) -> None:
        super(ModelCapitalAdjustmentTest, self).__init__(*args, **kwargs)
        self.count = random.randint(1, 10)
        self.model = MCapitalAdjustment
        self.params = [
            {
                "code": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "type": random.choice([i for i in CAPITALADJUSTMENT_TYPES]),
                "fenhong": Decimal(str(round(random.uniform(0, 20), 1))),
                "peigujia": Decimal(str(round(random.uniform(0, 20), 1))),
                "songzhuangu": Decimal(str(round(random.uniform(0, 20), 1))),
                "peigu": Decimal(str(round(random.uniform(0, 20), 1))),
                "suogu": Decimal(str(round(random.uniform(0, 20), 1))),
                "panqianliutong": Decimal(str(round(random.uniform(0, 20), 1))),
                "panhouliutong": Decimal(str(round(random.uniform(0, 20), 1))),
                "qianzongguben": Decimal(str(round(random.uniform(0, 20), 1))),
                "houzongguben": Decimal(str(round(random.uniform(0, 20), 1))),
                "fenshu": Decimal(str(round(random.uniform(0, 20), 1))),
                "xingquanjia": Decimal(str(round(random.uniform(0, 20), 1))),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelCapitalAdjustment_Init(self) -> None:
        for i in self.params:
            item = self.model(**i)
            self.assertEqual(item.code, i["code"])
            self.assertEqual(item.timestamp, i["timestamp"])
            self.assertEqual(item.type, i["type"])
            self.assertEqual(item.fenhong, i["fenhong"])
            self.assertEqual(item.peigujia, i["peigujia"])
            self.assertEqual(item.songzhuangu, i["songzhuangu"])
            self.assertEqual(item.peigu, i["peigu"])
            self.assertEqual(item.suogu, i["suogu"])
            self.assertEqual(item.panqianliutong, i["panqianliutong"])
            self.assertEqual(item.panhouliutong, i["panhouliutong"])
            self.assertEqual(item.qianzongguben, i["qianzongguben"])
            self.assertEqual(item.houzongguben, i["houzongguben"])
            self.assertEqual(item.fenshu, i["fenshu"])
            self.assertEqual(item.xingquanjia, i["xingquanjia"])
            self.assertEqual(item.source, i["source"])

    def test_ModelCapitalAdjustment_SetFromData(self) -> None:
        for i in self.params:
            item = self.model()

            # Set timestamp
            item.update(i["code"], timestamp=i["timestamp"])
            self.assertEqual(item.timestamp, i["timestamp"])

            # set type
            item.update(i["code"], type=i["type"])
            self.assertEqual(item.type, i["type"])

            # set fenhong
            item.update(i["code"], fenhong=i["fenhong"])
            self.assertEqual(item.fenhong, i["fenhong"])

            # set peigujia
            item.update(i["code"], peigujia=i["peigujia"])
            self.assertEqual(item.peigujia, i["peigujia"])

            # set songzhuangu
            item.update(i["code"], songzhuangu=i["songzhuangu"])
            self.assertEqual(item.songzhuangu, i["songzhuangu"])

            # set peigu
            item.update(i["code"], peigu=i["peigu"])
            self.assertEqual(item.peigu, i["peigu"])

            # set suogu
            item.update(i["code"], suogu=i["suogu"])
            self.assertEqual(item.suogu, i["suogu"])

            # set panqianliutong
            item.update(i["code"], panqianliutong=i["panqianliutong"])
            self.assertEqual(item.panqianliutong, i["panqianliutong"])

            # set panhouliutong
            item.update(i["code"], panhouliutong=i["panhouliutong"])
            self.assertEqual(item.panhouliutong, i["panhouliutong"])

            # set qianzongguben
            item.update(i["code"], qianzongguben=i["qianzongguben"])
            self.assertEqual(item.qianzongguben, i["qianzongguben"])

            # set houzongguben
            item.update(i["code"], houzongguben=i["houzongguben"])
            self.assertEqual(item.houzongguben, i["houzongguben"])

            # set fenshu
            item.update(i["code"], fenshu=i["fenshu"])
            self.assertEqual(item.fenshu, i["fenshu"])

            # set xingquanjia
            item.update(i["code"], xingquanjia=i["xingquanjia"])
            self.assertEqual(item.xingquanjia, i["xingquanjia"])

            # set source
            item.update(i["code"], source=i["source"])
            self.assertEqual(item.source, i["source"])

    def test_ModelCapitalAdjustment_SetFromDataframe(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(i["code"], o.code)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["type"], o.type)
            self.assertEqual(i["fenhong"], o.fenhong)
            self.assertEqual(i["peigujia"], o.peigujia)
            self.assertEqual(i["songzhuangu"], o.songzhuangu)
            self.assertEqual(i["peigu"], o.peigu)
            self.assertEqual(i["suogu"], o.suogu)
            self.assertEqual(i["panqianliutong"], o.panqianliutong)
            self.assertEqual(i["panhouliutong"], o.panhouliutong)
            self.assertEqual(i["qianzongguben"], o.qianzongguben)
            self.assertEqual(i["houzongguben"], o.houzongguben)
            self.assertEqual(i["fenshu"], o.fenshu)
            self.assertEqual(i["xingquanjia"], o.xingquanjia)
            self.assertEqual(i["source"], o.source)
