# import unittest
# import time
# import uuid
# import random
# import datetime

# from datetime import timedelta

# from ginkgo.data.operations.adjustfactor_crud import *
# from ginkgo.data.drivers import get_table_size, create_table, drop_table
# from ginkgo.data.models import MAdjustfactor


# class OperationAdjustfactorTest(unittest.TestCase):
#     """
#     UnitTest for Adjustfactor CRUD
#     """

#     @classmethod
#     def setUpClass(cls):
#         cls.model = MAdjustfactor
#         drop_table(cls.model)
#         time.sleep(0.1)
#         create_table(cls.model)
#         cls.count = 10
#         cls.params = [
#             {
#                 "timestamp": datetime.datetime.now(),
#                 "code": uuid.uuid4().hex,
#                 "foreadjustfactor": round(random.uniform(1.5, 5.5), 2),
#                 "backadjustfactor": round(random.uniform(1.5, 5.5), 2),
#                 "adjustfactor": round(random.uniform(1.5, 5.5), 2),
#             }
#             for i in range(cls.count)
#         ]

#     def test_OperationAdjustfactor_insert(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             add_adjustfactor(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#     def test_OperationAdjustfactor_bulkinsert(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         for i in self.params:
#             item = self.model(**i)
#             l.append(item)
#         add_adjustfactors(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(len(self.params), size1 - size0)

#     def test_OperationAdjustfactor_delete_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             item = add_adjustfactor(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             delete_adjustfactor_by_id(item.uuid)
#             size2 = get_table_size(self.model)
#             self.assertEqual(-1, size2 - size1)

#     def test_OperationAdjustfactor_softdelete_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             item = add_adjustfactor(**i)
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)

#             softdelete_adjustfactor_by_id(item.uuid)
#             size2 = get_table_size(self.model)
#             self.assertEqual(0, size2 - size1)

#     def test_OperationAdjustfactor_delete_by_code_and_date_range(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         code = uuid.uuid4().hex

#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2020-01-01",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2020-01-02",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2020-01-02",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2020-01-03",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         add_adjustfactors(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(4, size1 - size0)
#         delete_adjustfactor_by_code_and_date_range(code, start_date="2020-01-01", end_date="2020-01-02")
#         size2 = get_table_size(self.model)
#         self.assertEqual(-3, size2 - size1)

#     def test_OperationAdjustfactor_softdelete_by_code_and_date_range(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         code = uuid.uuid4().hex

#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-01",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-02",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-02",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-03",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         add_adjustfactors(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(4, size1 - size0)
#         df1 = get_adjustfactor_by_code_and_date_range(code)
#         softdelete_adjustfactor_by_code_and_date_range(code, start_date="2021-01-01", end_date="2021-01-02")
#         size2 = get_table_size(self.model)
#         self.assertEqual(0, size2 - size1)
#         df2 = get_adjustfactor_by_code_and_date_range(code)
#         self.assertEqual(-3, df2.shape[0] - df1.shape[0])

#     def test_OperationAdjustfactor_exists(self) -> None:
#         pass

#     def test_OperationAdjustfactor_update_by_id(self) -> None:
#         for i in self.params:
#             size0 = get_table_size(self.model)
#             res = add_adjustfactor(
#                 i["timestamp"], i["code"], i["foreadjustfactor"], i["backadjustfactor"], i["adjustfactor"]
#             )
#             size1 = get_table_size(self.model)
#             self.assertEqual(1, size1 - size0)
#             id = res.uuid
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(df.code, i["code"])
#             self.assertEqual(df.foreadjustfactor, i["foreadjustfactor"])
#             self.assertEqual(df.backadjustfactor, i["backadjustfactor"])
#             self.assertEqual(df.adjustfactor, i["adjustfactor"])
#             # Update code
#             new_code = uuid.uuid4().hex
#             update_adjustfactor_by_id(id, code=new_code)
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(df.code, new_code)

#             # Update foreadjustfactor
#             new_foreadjustfactor = round(random.uniform(1.5, 5.5), 2)
#             update_adjustfactor_by_id(id, foreadjustfactor=new_foreadjustfactor)
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(df.foreadjustfactor, new_foreadjustfactor)

#             # Update backadjustfactor
#             new_backadjustfactor = round(random.uniform(1.5, 5.5), 2)
#             update_adjustfactor_by_id(id, backadjustfactor=new_backadjustfactor)
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(df.backadjustfactor, new_backadjustfactor)

#             # Update adjustfactor
#             new_adjustfactor = round(random.uniform(1.5, 5.5), 2)
#             update_adjustfactor_by_id(id, adjustfactor=new_adjustfactor)
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(df.adjustfactor, new_adjustfactor)

#             # Update timestamp
#             new_timestamp = datetime.datetime.now()
#             update_adjustfactor_by_id(id, timestamp=new_timestamp)
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(abs(df.timestamp - new_timestamp) < timedelta(seconds=1), True)

#             # Update all
#             new_code = uuid.uuid4().hex
#             new_foreadjustfactor = round(random.uniform(1.5, 5.5), 2)
#             new_backadjustfactor = round(random.uniform(1.5, 5.5), 2)
#             new_adjustfactor = round(random.uniform(1.5, 5.5), 2)
#             update_adjustfactor_by_id(
#                 id,
#                 code=new_code,
#                 foreadjustfactor=new_foreadjustfactor,
#                 backadjustfactor=new_backadjustfactor,
#                 adjustfactor=new_adjustfactor,
#             )
#             df = get_adjustfactor_by_id(id).iloc[0]
#             self.assertEqual(df.code, new_code)
#             self.assertEqual(df.foreadjustfactor, new_foreadjustfactor)
#             self.assertEqual(df.backadjustfactor, new_backadjustfactor)
#             self.assertEqual(df.adjustfactor, new_adjustfactor)

#     def test_OperationAdjustfactor_update_by_code_and_date_range(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         code = uuid.uuid4().hex

#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-01",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-02",
#                 foreadjustfactor=13,
#                 backadjustfactor=13,
#                 adjustfactor=13,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-02",
#                 foreadjustfactor=14,
#                 backadjustfactor=14,
#                 adjustfactor=14,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-03",
#                 foreadjustfactor=15,
#                 backadjustfactor=15,
#                 adjustfactor=15,
#             )
#         )
#         add_adjustfactors(l)
#         size1 = get_table_size(self.model)
#         self.assertEqual(4, size1 - size0)
#         update_adjustfactor_by_code_and_date_range(
#             code,
#             start_date="2021-01-01",
#             end_date="2021-01-02",
#             foreadjustfactor=16,
#             backadjustfactor=17,
#             adjustfactor=18,
#         )
#         df = get_adjustfactor_by_code_and_date_range(code, start_date="2021-01-01", end_date="2021-01-02")
#         for i, r in df.iterrows():
#             self.assertEqual(r.foreadjustfactor, 16)
#             self.assertEqual(r.backadjustfactor, 17)
#             self.assertEqual(r.adjustfactor, 18)

#     def test_OperationAdjustfactor_get(self) -> None:
#         l = []
#         size0 = get_table_size(self.model)
#         code = uuid.uuid4().hex

#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-01",
#                 foreadjustfactor=12,
#                 backadjustfactor=12,
#                 adjustfactor=12,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-02",
#                 foreadjustfactor=13,
#                 backadjustfactor=13,
#                 adjustfactor=13,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-02",
#                 foreadjustfactor=14,
#                 backadjustfactor=14,
#                 adjustfactor=14,
#             )
#         )
#         l.append(
#             self.model(
#                 code=code,
#                 timestamp="2021-01-03",
#                 foreadjustfactor=15,
#                 backadjustfactor=15,
#                 adjustfactor=15,
#             )
#         )
#         add_adjustfactors(l)
#         size1 = get_table_size(self.model)
#         softdelete_adjustfactor_by_code_and_date_range(code, start_date="2021-01-01", end_date="2021-01-01")
#         self.assertEqual(4, size1 - size0)
#         df = get_adjustfactor_by_code_and_date_range(code)
#         self.assertEqual(3, df.shape[0])
#         df = get_adjustfactor_by_code_and_date_range(code, start_date="2021-01-01", end_date="2021-01-02")
#         self.assertEqual(2, df.shape[0])
#         df = get_adjustfactor_by_code_and_date_range(
#             code, start_date="2021-01-01", end_date="2021-01-03", page=0, page_size=2
#         )
#         self.assertEqual(2, df.shape[0])
#         df = get_adjustfactor_by_code_and_date_range(
#             code, start_date="2021-01-01", end_date="2021-01-03", page=1, page_size=2
#         )
#         self.assertEqual(1, df.shape[0])

#     def test_OperationAdjustfactor_exceptions(self) -> None:
#         # TODO
#         pass
