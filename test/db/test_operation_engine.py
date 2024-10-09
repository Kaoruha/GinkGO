# import unittest
# import time
# import uuid
# import random
# import datetime

# from ginkgo.enums import SOURCE_TYPES
# from ginkgo.data.drivers import get_table_size, create_table, drop_table
# from ginkgo.data.operations.engine_crud import *
# from ginkgo.data.models import MEngine


# class OperationEngineTest(unittest.TestCase):
#     """
#     UnitTest for Analyzer CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MEngine
#         drop_table(cls.model)
#         time.sleep(0.1)
#         create_table(cls.model)
#         cls.count = 10
#         cls.params = [
#             {
#                 "name": uuid.uuid4().hex,
#                 "is_live": random.choice([True, False]),
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationEngine_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationEngine_bulkinsert(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         add_engines(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationEngine_delete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             delete_engine(res.uuid)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationEngine_softdelete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             softdelete_engine(res.uuid)
#             time.sleep(0.2)
#             size2 = get_table_size(self.model)
#             self.assertEqual(0, size2 - size1)
#             delete_engine(res.uuid)
#             time.sleep(0.2)
#             size3 = get_table_size(self.model)
#             self.assertEqual(-1, size3 - size1)

#     def test_OperationEngine_exists(self) -> None:
#         pass

#     def test_OperationEngine_update(self) -> None:
#         pass

#     def test_OperationEngine_get(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             item = get_engine(id=res.uuid)
#             self.assertEqual(i["name"], item["name"])
#             self.assertEqual(i["is_live"], item["is_live"])

#     def test_OperationEngine_exceptions(self) -> None:
#         pass
