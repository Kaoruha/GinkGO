# import unittest
# import uuid
# import random
# import time
# import pandas as pd
# import datetime

# from ginkgo.enums import SOURCE_TYPES

# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import MHandlerParam


# class ModelHandlerParamTest(unittest.TestCase):
#     """
#     UnitTest for Bar.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelHandlerParamTest, self).__init__(*args, **kwargs)
#         self.count = 10
#         self.model = MHandlerParam
#         self.params = [
#             {
#                 "handler_id": uuid.uuid4().hex,
#                 "index": i,
#                 "value": uuid.uuid4().hex,
#                 "source": random.choice([i for i in SOURCE_TYPES]),
#             }
#             for i in range(self.count)
#         ]

#     def test_ModelHandlerParam_Init(self) -> None:
#         for i in self.params:
#             o = self.model(handler_id=i["handler_id"], index=i["index"], value=i["value"], source=i["source"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.index, i["index"])
#             self.assertEqual(o.value, i["value"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelHandlerParam_SetFromData(self) -> None:
#         for i in self.params:
#             o = self.model()

#             # update handler_id
#             o.update(i["handler_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])

#             # udpate index
#             o.update(i["handler_id"], index=i["index"])
#             self.assertEqual(o.index, i["index"])

#             # update value
#             o.update(i["handler_id"], value=i["value"])
#             self.assertEqual(o.value, i["value"])

#             # update source
#             o.update(i["handler_id"], source=i["source"])
#             self.assertEqual(o.source, i["source"])

#         # Update all
#         for i in self.params:
#             o = self.model()
#             o.update(i["handler_id"], index=i["index"], value=i["value"], source=i["source"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.index, i["index"])
#             self.assertEqual(o.value, i["value"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelHandlerParam_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o = self.model()
#             o.update(df)
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.index, i["index"])
#             self.assertEqual(o.value, i["value"])
#             self.assertEqual(o.source, i["source"])
