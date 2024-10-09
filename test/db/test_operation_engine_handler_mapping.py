# import unittest
# import time
# import uuid
# import random
# import datetime

# from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
# from ginkgo.data.drivers import get_table_size, create_table, drop_table
# from ginkgo.data.operations.engine_handler_mapping_crud import *
# from ginkgo.data.models import MEngineHandlerMapping


# class OperationEngineHandlerMappingTest(unittest.TestCase):
#     """
#     UnitTest for Analyzer CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MEngineHandlerMapping
#         drop_table(cls.model)
#         time.sleep(0.1)
#         create_table(cls.model)
#         cls.count = 10
#         cls.params = [
#             {
#                 "engine_id": uuid.uuid4().hex,
#                 "handler_id": uuid.uuid4().hex,
#                 "type": random.choice([i for i in EVENT_TYPES]),
#                 "name": uuid.uuid4().hex,
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationEngineHandlerMapping_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationEngineHandlerMapping_bulkinsert(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         res = add_engine_handler_mappings(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationEngineHandlerMapping_delete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             delete_engine_handler_mapping(res.uuid)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationEngineHandlerMapping_softdelete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             softdelete_engine_handler_mapping(res.uuid)
#             time.sleep(0.2)
#             size2 = get_table_size(self.model)
#             self.assertEqual(0, size2 - size1)
#             delete_engine_handler_mapping(res.uuid)
#             time.sleep(0.2)
#             size3 = get_table_size(self.model)
#             self.assertEqual(-1, size3 - size1)

#     # def test_OperationEngineHandlerMapping_exists(self) -> None:
#     #     pass

#     def test_OperationEngineHandlerMapping_update(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine_handler_mapping(engine_id="test", handler_id="test", type=EVENT_TYPES.OTHER, name="name")
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             # Update Engine ID
#             update_engine_handler_mapping(res.uuid, engine_id=i["engine_id"])
#             df = get_engine_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["engine_id"], i["engine_id"])

#             # Update Handler ID
#             update_engine_handler_mapping(res.uuid, handler_id=i["handler_id"])
#             df = get_engine_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["handler_id"], i["handler_id"])

#             # update type
#             update_engine_handler_mapping(res.uuid, type=i["type"])
#             df = get_engine_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["type"], i["type"])

#             # update name
#             update_engine_handler_mapping(res.uuid, name=i["name"])
#             df = get_engine_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["name"], i["name"])

#     def test_OperationEngineHandlerMapping_get(self) -> None:
#         engine_id = uuid.uuid4().hex
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_engine_handler_mapping(
#                 engine_id=engine_id, handler_id=i["handler_id"], type=i["type"], name=i["name"]
#             )
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#         df = get_engine_handler_mappings(engine_id=engine_id)
#         self.assertEqual(self.count, df.shape[0])

#     # def test_OperationEngine_exceptions(self) -> None:
#     #     # TODO
#     #     pass
