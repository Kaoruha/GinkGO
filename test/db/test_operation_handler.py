import unittest
import time
import random
import uuid
from ginkgo.data.drivers import add, add_all, get_table_size, create_table, drop_table
from ginkgo.data.models import MHandler
from ginkgo.enums import FILE_TYPES
from ginkgo.data.operations.handler_crud import *


class OperationHandlerTest(unittest.TestCase):
    """
    UnitTest for File CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MHandler
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "name": uuid.uuid4().hex,
                "lib_path": uuid.uuid4().hex,
                "func_name": uuid.uuid4().hex,
            }
            for i in range(cls.count)
        ]

    def test_OperationHandler_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            self.assertEqual(res["name"], i["name"])
            self.assertEqual(res["lib_path"], i["lib_path"])
            self.assertEqual(res["func_name"], i["func_name"])

    def test_OperationHandler_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_handlers(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationHandler_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            item = add_handler(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_handler(item.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationHandler_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            item = add_handler(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_handler(item.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

    def test_OperationHandler_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update name
            new_name = uuid.uuid4().hex
            update_handler(res.uuid, name=new_name)
            item = get_handler(res.uuid).iloc[0]
            self.assertEqual(new_name, item["name"])

            # update libpath
            new_lib_path = uuid.uuid4().hex
            update_handler(res.uuid, lib_path=new_lib_path)
            item = get_handler(res.uuid).iloc[0]
            self.assertEqual(new_lib_path, item["lib_path"])

            # update func_name
            new_func_name = uuid.uuid4().hex
            update_handler(res.uuid, func_name=new_func_name)
            item = get_handler(res.uuid).iloc[0]
            self.assertEqual(new_func_name, item["func_name"])

    def test_OperationHandler_read(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_handler(res.uuid).iloc[0]
            self.assertEqual(res.uuid, df["uuid"])

    def test_OperationHandler_read(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
        df = get_handlers()
        print(df)
        self.assertEqual(df.shape[0] > 0, True)

    # def test_OperationHandler_exists(self) -> None:
    #     pass

    # def test_OperationHandler_exceptions(self) -> None:
    #     pass
