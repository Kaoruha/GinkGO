import unittest
import pandas as pd
import time
import datetime
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MAdjustfactor
from ginkgo import GLOG


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
        result = True
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
