# import unittest
# import uuid
# import base64
# import random
# import time
# import pandas as pd
# import datetime
# from ginkgo.data.models import MAdjustfactor


# class ModelAdjustfactorTest(unittest.TestCase):
#     """
#     Examples for UnitTests of models
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelAdjustfactorTest, self).__init__(*args, **kwargs)
#         self.count = 10
#         self.model = MAdjustfactor
#         self.params = [
#             {
#                 "code": uuid.uuid4().hex,
#                 "adjustfactor": round(random.uniform(0, 100), 2),
#                 "foreadjustfactor": round(random.uniform(0, 100), 2),
#                 "backadjustfactor": round(random.uniform(0, 100), 2),
#                 "timestamp": datetime.datetime.now(),
#             }
#             for i in range(self.count)
#         ]

#     def test_ModelAdjustfactor_Init(self) -> None:
#         for i in self.params:
#             o = self.model(**i)
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
#             self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
#             self.assertEqual(o.adjustfactor, i["adjustfactor"])
#             self.assertEqual(o.timestamp, i["timestamp"])

#     def test_ModelAdjustfactor_SetFromData(self) -> None:
#         for i in self.params:
#             o = self.model()
#             o.update(
#                 i["code"],
#             )
#             self.assertEqual(o.code, i["code"])
#             o.update(
#                 i["code"],
#                 foreadjustfactor=i["foreadjustfactor"],
#             )
#             self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
#             o.update(
#                 i["code"],
#                 backadjustfactor=i["backadjustfactor"],
#             )
#             self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
#             o.update(
#                 i["code"],
#                 adjustfactor=i["adjustfactor"],
#             )
#             self.assertEqual(o.adjustfactor, i["adjustfactor"])
#         for i in self.params:
#             o = self.model()
#             o.update(
#                 i["code"],
#                 timestamp=i["timestamp"],
#             )
#             self.assertEqual(o.timestamp, i["timestamp"])

#     def test_ModelAdjustfactor_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o = self.model()
#             o.update(df)
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
#             self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
#             self.assertEqual(o.adjustfactor, i["adjustfactor"])
