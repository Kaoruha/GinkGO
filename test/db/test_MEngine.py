import unittest
import uuid
import random
import time
import pandas as pd
import datetime

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MEngine
from ginkgo.enums import SOURCE_TYPES


class ModelEngineTest(unittest.TestCase):
    """
    UnitTest for Bar.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelEngineTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MEngine
        self.params = [
            {
                "name": uuid.uuid4().hex,
                "is_live": random.choice([True, False]),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelEngine_Init(self) -> None:
        for i in self.params:
            o = self.model(
                name=i["name"],
                is_live=i["is_live"],
            )
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.is_live, i["is_live"])

    def test_ModelEngine_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            o.update(i["name"])
            self.assertEqual(o.name, i["name"])
            o.update(i["name"], is_live=i["is_live"])
            self.assertEqual(o.is_live, i["is_live"])

        for i in self.params:
            o = self.model()
            o.update(i["name"], is_live=i["is_live"])
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.is_live, i["is_live"])

    def test_ModelEngine_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.is_live, i["is_live"])
