# import unittest
# import time
# import uuid
# import random
# import datetime

# from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
# from ginkgo.data.drivers import get_table_size, create_table, drop_table
# from ginkgo.data.operations.portfolio_handler_mapping_crud import *

# from ginkgo.data.models import MPortfolioHandlerMapping


# class OperationPortfolioHandlerMappingTest(unittest.TestCase):
#     """
#     UnitTest for Analyzer CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MPortfolioHandlerMapping
#         drop_table(cls.model)
#         time.sleep(0.1)
#         create_table(cls.model)
#         cls.count = 10
#         cls.params = [
#             {
#                 "portfolio_id": uuid.uuid4().hex,
#                 "handler_id": uuid.uuid4().hex,
#                 "type": random.choice([i for i in EVENT_TYPES]),
#                 "name": uuid.uuid4().hex,
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationPortfolioHandlerMapping_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_portfolio_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationPortfolioHandlerMapping_bulkinsert(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         res = add_portfolio_handler_mappings(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationPortfolioHandlerMapping_delete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_portfolio_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             delete_portfolio_handler_mapping(res.uuid)
#             time.sleep(0.1)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationPortfolioHandlerMapping_softdelete(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_portfolio_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             softdelete_portfolio_handler_mapping(res.uuid)
#             size2 = get_table_size(self.model)
#             self.assertEqual(0, size2 - size1)
#             delete_portfolio_handler_mapping(res.uuid)
#             size3 = get_table_size(self.model)
#             self.assertEqual(-1, size3 - size1)

#     def test_OperationPortfolioHandlerMapping_exists(self) -> None:
#         pass

#     def test_OperationPortfolioHandlerMapping_update(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_portfolio_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             # update portfolio id
#             new_portfolio_id = uuid.uuid4().hex
#             update_portfolio_handler_mapping(res.uuid, portfolio_id=new_portfolio_id)
#             df = get_portfolio_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["portfolio_id"], new_portfolio_id)

#             # update handler id
#             new_handler_id = uuid.uuid4().hex
#             update_portfolio_handler_mapping(res.uuid, handler_id=new_handler_id)
#             df = get_portfolio_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["handler_id"], new_handler_id)

#             # update type
#             new_type = random.choice([i for i in EVENT_TYPES])
#             update_portfolio_handler_mapping(res.uuid, type=new_type)
#             df = get_portfolio_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["type"], new_type)

#             # update name
#             new_name = uuid.uuid4().hex
#             update_portfolio_handler_mapping(res.uuid, name=new_name)
#             df = get_portfolio_handler_mapping_by_id(res.uuid)
#             self.assertEqual(df["name"], new_name)

#     def test_OperationPortfolioHandlerMapping_get_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_portfolio_handler_mapping(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             df = get_portfolio_handler_mapping_by_id(id=res.uuid)
#             self.assertEqual(df["uuid"], res["uuid"])
#             self.assertEqual(df["portfolio_id"], res["portfolio_id"])
#             self.assertEqual(df["handler_id"], res["handler_id"])
#             self.assertEqual(df["type"], res["type"])
#             self.assertEqual(df["name"], res["name"])

#     def test_OperationPortfolioHandlerMapping_get_by_portfolio(self) -> None:
#         new_portfolio_id = uuid.uuid4().hex
#         for i in range(self.count):
#             params_copy = self.params[i].copy()
#             params_copy["portfolio_id"] = new_portfolio_id
#             add_portfolio_handler_mapping(**params_copy)
#         df = get_portfolio_handler_mappings(new_portfolio_id)
#         self.assertEqual(df.shape[0], self.count)

#     def test_OperationPortfolio_exceptions(self) -> None:
#         # TODO
#         pass
