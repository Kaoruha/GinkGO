import unittest
import time
import datetime
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GLOG


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
        pass

    def test_ModelExample_SetFromData(self) -> None:
        pass

    def test_ModelExample_SetFromDataFrame(self) -> None:
        pass

    def test_ModelExample_Insert(self) -> None:
        pass

    def test_ModelExample_BatchInsert(self) -> None:
        pass

    def test_ModelExample_Query(self) -> None:
        pass
