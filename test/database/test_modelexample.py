import unittest
import time
import datetime
from ginkgo.libs import GLOG
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_conf import GCONF


class ModelExampleTest(unittest.TestCase):
    """
    Examples for UnitTests of models
    """

    # Init
    # set data from bar
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelExampleTest, self).__init__(*args, **kwargs)
        self.params = []

    def test_ModelExample_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelExample_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelExample_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelExample_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelExample_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass

    def test_ModelExample_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        pass
