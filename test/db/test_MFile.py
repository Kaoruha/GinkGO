import unittest
import uuid
import random
import time
import pandas as pd
import datetime

from ginkgo.enums import SOURCE_TYPES

from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.data.models import MFile


class ModelFileTest(unittest.TestCase):
    """
    UnitTest for Bar.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelFileTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MFile
        self.params = [
            {
                "name": uuid.uuid4().hex,
                "type": SOURCE_TYPES.SIM,
                "data": b"testdata",
            }
            for i in range(self.count)
        ]

    def test_ModelFile_Init(self) -> None:
        for i in self.params:
            o = self.model(name=i["name"], type=i["type"], data=i["data"])
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.data, i["data"])

    def test_ModelFile_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Name upate
            o.update(i["name"])
            self.assertEqual(o.name, i["name"])

            # Type update
            o.update(i["name"], type=i["type"])
            self.assertEqual(o.type, i["type"])

            # Data update
            o.update(i["name"], data=i["data"])
            self.assertEqual(o.data, i["data"])

        for i in self.params:
            o = self.model()
            # Name, Type, Data update
            o.update(i["name"], type=i["type"], data=i["data"])
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.data, i["data"])

    def test_ModelFile_SetFromDataFrame(self) -> None:
        pass
