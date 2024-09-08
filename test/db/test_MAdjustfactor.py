# import unittest
# import base64
# import random
# import time
# import pandas as pd
# import datetime
# from ginkgo.libs.ginkgo_conf import GCONF
# from ginkgo.data.models import MAdjustfactor
# from ginkgo.data.ginkgo_data import GDATA


# class ModelAdjustfactorTest(unittest.TestCase):
#     """
#     Examples for UnitTests of models
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelAdjustfactorTest, self).__init__(*args, **kwargs)
#         self.test_count = 10
#         self.params = [
#             {
#                 "code": "testcode",
#                 "adjustfactor": 0.78,
#                 "foreadjustfactor": 0.5,
#                 "backadjustfactor": 0.8,
#                 "timestamp": datetime.datetime.now(),
#             },
#             {
#                 "code": "testcode",
#                 "adjustfactor": 0.71,
#                 "foreadjustfactor": 0.2,
#                 "backadjustfactor": 0.1,
#                 "timestamp": datetime.datetime.now(),
#             },
#         ]

#     def test_ModelAdjustfactor_Init(self) -> None:
#         o = MAdjustfactor()

#     def test_ModelAdjustfactor_SetFromData(self) -> None:
#         for i in self.params:
#             o = MAdjustfactor()
#             o.set(
#                 i["code"],
#                 i["foreadjustfactor"],
#                 i["backadjustfactor"],
#                 i["adjustfactor"],
#                 i["timestamp"],
#             )
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
#             self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
#             self.assertEqual(o.adjustfactor, i["adjustfactor"])

#     def test_ModelAdjustfactor_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o = MAdjustfactor()
#             o.set(df)
#             self.assertEqual(o.code, i["code"])
#             self.assertEqual(o.foreadjustfactor, i["foreadjustfactor"])
#             self.assertEqual(o.backadjustfactor, i["backadjustfactor"])
#             self.assertEqual(o.adjustfactor, i["adjustfactor"])

#     def test_ModelAdjustfactor_Insert(self) -> None:
#         GDATA.create_table(MAdjustfactor)
#         for i in self.params:
#             size0 = GDATA.get_table_size(MAdjustfactor)
#             o = MAdjustfactor()
#             o.set(
#                 i["code"],
#                 i["foreadjustfactor"],
#                 i["backadjustfactor"],
#                 i["adjustfactor"],
#                 i["timestamp"],
#             )
#             GDATA.add(o)
#             size1 = GDATA.get_table_size(MAdjustfactor)
#             self.assertEqual(1, size1 - size0)

#     def test_ModelAdjustfactor_BatchInsert(self) -> None:
#         GDATA.create_table(MAdjustfactor)
#         times0 = random.random() * self.test_count
#         times0 = int(times0)
#         for j in range(times0):
#             size0 = GDATA.get_table_size(MAdjustfactor)
#             l = []
#             times = random.random() * self.test_count
#             times = int(times)
#             for k in range(times):
#                 for i in self.params:
#                     o = MAdjustfactor()
#                     o.set(
#                         i["code"],
#                         i["foreadjustfactor"],
#                         i["backadjustfactor"],
#                         i["adjustfactor"],
#                         i["timestamp"],
#                     )
#                     l.append(o)
#             GDATA.add_all(l)
#             size1 = GDATA.get_table_size(MAdjustfactor)
#             self.assertEqual(size1 - size0, len(l))

#     def test_ModelAdjustfactor_Query(self) -> None:
#         GDATA.create_table(MAdjustfactor)
#         o = MAdjustfactor()
#         uuid = o.uuid
#         GDATA.add(o)
#         r = (
#             GDATA.get_driver(MAdjustfactor)
#             .session.query(MAdjustfactor)
#             .filter(MAdjustfactor.uuid == uuid)
#             .first()
#         )
#         self.assertNotEqual(r, None)

#     def test_ModelAdjustfactor_Update(self) -> None:
#         num = random.random() * self.test_count
#         num = int(num)
#         GDATA.create_table(MAdjustfactor)
#         o = MAdjustfactor()
#         uuid = o.uuid
#         GDATA.add(o)
#         for i in range(num):
#             GDATA.get_driver(MAdjustfactor)
#             item = (
#                 GDATA.get_driver(MAdjustfactor)
#                 .session.query(MAdjustfactor)
#                 .filter(MAdjustfactor.uuid == uuid)
#                 .first()
#             )
#             s = random.random() * 500
#             s = str(s)
#             s = s.encode("ascii")
#             s = base64.b64encode(s)
#             s = s.decode("ascii")
#             item.code = s
#             GDATA.get_driver(MAdjustfactor).session.merge(item)
#             GDATA.get_driver(MAdjustfactor).session.commit()
#             item2 = (
#                 GDATA.get_driver(MAdjustfactor)
#                 .session.query(MAdjustfactor)
#                 .filter(MAdjustfactor.uuid == uuid)
#                 .first()
#             )
#             self.assertEqual(s, item2.code)
