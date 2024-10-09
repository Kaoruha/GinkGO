# import unittest
# import uuid
# import random
# import time
# import pandas as pd
# import datetime

# from ginkgo.enums import SOURCE_TYPES

# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import MHandler


# class ModelHandlerTest(unittest.TestCase):
#     """
#     UnitTest for Bar.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelHandlerTest, self).__init__(*args, **kwargs)
#         self.count = 10
#         self.model = MHandler
#         self.params = [
#             {
#                 "name": uuid.uuid4().hex,
#                 "lib_path": uuid.uuid4().hex,
#                 "func_name": uuid.uuid4().hex,
#                 "source": random.choice([i for i in SOURCE_TYPES]),
#             }
#             for i in range(self.count)
#         ]

#     def test_ModelHandler_Init(self) -> None:
#         for i in self.params:
#             o = self.model(name=i["name"], lib_path=i["lib_path"], func_name=i["func_name"], source=i["source"])
#             self.assertEqual(o.name, i["name"])
#             self.assertEqual(o.lib_path, i["lib_path"])
#             self.assertEqual(o.func_name, i["func_name"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelHandler_SetFromData(self) -> None:
#         for i in self.params:
#             o = self.model()
#             # Name upate
#             o.update(i["name"])
#             self.assertEqual(o.name, i["name"])

#             # lib_path update
#             o.update(i["name"], lib_path=i["lib_path"])
#             self.assertEqual(o.lib_path, i["lib_path"])

#             # func_name update
#             o.update(i["name"], func_name=i["func_name"])
#             self.assertEqual(o.func_name, i["func_name"])

#             # source udpate
#             o.update(i["name"], source=i["source"])
#             self.assertEqual(o.source, i["source"])

#         # Update all
#         for i in self.params:
#             o = self.model()
#             o.update(i["name"], lib_path=i["lib_path"], func_name=i["func_name"], source=i["source"])
#             self.assertEqual(o.name, i["name"])
#             self.assertEqual(o.lib_path, i["lib_path"])
#             self.assertEqual(o.func_name, i["func_name"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelHandler_SetFromDataFrame(self) -> None:
#         pass
