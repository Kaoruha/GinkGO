# import unittest
# import uuid
# import random
# import time
# import pandas as pd
# import datetime

# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import MEngineHandlerMapping
# from ginkgo.enums import SOURCE_TYPES


# class ModelEngineHandlerMappingTest(unittest.TestCase):
#     """
#     UnitTest for Bar.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelEngineHandlerMappingTest, self).__init__(*args, **kwargs)
#         self.count = 10
#         self.model = MEngineHandlerMapping
#         self.params = [
#             {
#                 "engine_id": uuid.uuid4().hex,
#                 "handler_id": uuid.uuid4().hex,
#                 "type": random.choice([i for i in SOURCE_TYPES]),
#                 "name": uuid.uuid4().hex,
#                 "source": random.choice([i for i in SOURCE_TYPES]),
#             }
#             for i in range(self.count)
#         ]

#     def test_ModelEngineHandlerMapping_Init(self) -> None:
#         for i in self.params:
#             o = self.model(
#                 engine_id=i["engine_id"],
#                 handler_id=i["handler_id"],
#                 type=i["type"],
#                 name=i["name"],
#                 source=i["source"],
#             )
#             self.assertEqual(o.engine_id, i["engine_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.type, i["type"])
#             self.assertEqual(o.name, i["name"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelEngineHandlerMapping_SetFromData(self) -> None:
#         for i in self.params:
#             o = self.model()
#             o.update(i["engine_id"])
#             self.assertEqual(o.engine_id, i["engine_id"])
#             o.update(i["engine_id"], handler_id=i["handler_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             o.update(i["engine_id"], type=i["type"])
#             self.assertEqual(o.type, i["type"])
#             o.update(i["engine_id"], name=i["name"])
#             self.assertEqual(o.name, i["name"])
#             o.update(i["engine_id"], source=i["source"])
#             self.assertEqual(o.source, i["source"])

#         for i in self.params:
#             o = self.model()
#             o.update(i["engine_id"], handler_id=i["handler_id"], type=i["type"], name=i["name"], source=i["source"])
#             self.assertEqual(o.engine_id, i["engine_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.type, i["type"])
#             self.assertEqual(o.name, i["name"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelEngineHandlerMapping_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o = self.model()
#             o.update(df)
#             self.assertEqual(o.engine_id, i["engine_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.type, i["type"])
#             self.assertEqual(o.name, i["name"])
#             self.assertEqual(o.source, i["source"])
