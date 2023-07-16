import unittest
import time
import datetime
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MAdjustfactor
from ginkgo import GCONF, GLOG


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
                "date": datetime.datetime.now(),
            }
        ]

    def test_ModelAdjustfactor_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        try:
            o = MAdjustfactor()
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_ModelAdjustfactor_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            o = MAdjustfactor()
            o.set(
                i["code"],
                i["foreadjustfactor"],
                i["backadjustfactor"],
                i["adjustfactor"],
                i["date"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
            self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
            self.assertEqual(o.adjustfactor, i["adjustfactor"])

    def test_ModelAdjustfactor_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelAdjustfactor_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MAdjustfactor)
        GDATA.create_table(MAdjustfactor)
        for i in self.params:
            try:
                o = MAdjustfactor()
                o.set(
                    i["code"],
                    i["foreadjustfactor"],
                    i["backadjustfactor"],
                    i["adjustfactor"],
                    i["date"],
                )
                GDATA.add(o)
                GDATA.commit()
            except Exception as e:
                result = False

        self.assertEqual(result, True)

    def test_ModelAdjustfactor_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelAdjustfactor_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass
