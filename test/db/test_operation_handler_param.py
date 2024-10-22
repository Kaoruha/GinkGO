import unittest
import time
import random
import uuid
from ginkgo.data.drivers import add, add_all, get_table_size, create_table, drop_table
from ginkgo.data.models import MHandlerParam
from ginkgo.enums import FILE_TYPES
from ginkgo.data.operations.handler_param_crud import *


class OperationHandlerParamTest(unittest.TestCase):
    """
    UnitTest for File CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MHandlerParam
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "handler_id": uuid.uuid4().hex,
                "index": random.randint(1, 10),
                "value": uuid.uuid4().hex,
            }
            for i in range(cls.count)
        ]

    def test_OperationHandlerParam_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler_param(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            self.assertEqual(res["handler_id"], i["handler_id"])
            self.assertEqual(res["index"], i["index"])
            self.assertEqual(res["value"], i["value"])

    def test_OperationHandlerParam_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_handler_params(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationHandlerParam_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            item = add_handler_param(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_handler_param(item.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationHandlerParam_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            item = add_handler_param(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_handler_param(item.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

    def test_OperationHandlerParam_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler_param(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update handler_id
            new_handler_param_id = uuid.uuid4().hex
            update_handler_param(res.uuid, handler_id=new_handler_param_id)
            item = get_handler_param(res.uuid)
            self.assertEqual(item["handler_id"], new_handler_param_id)

            # update index
            new_index = random.randint(1, 10)
            update_handler_param(res.uuid, index=new_index)
            item = get_handler_param(res.uuid)
            self.assertEqual(item["index"], new_index)

            # update value
            new_value = uuid.uuid4().hex
            update_handler_param(res.uuid, value=new_value)
            item = get_handler_param(res.uuid)
            self.assertEqual(item["value"], new_value)

    def test_OperationHandlerParam_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler_param(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_handler_param(res.uuid)
            self.assertEqual(res["uuid"], df["uuid"])
            self.assertEqual(res["handler_id"], df["handler_id"])
            self.assertEqual(res["index"], df["index"])
            self.assertEqual(res["value"], df["value"])

    def test_OperationHandlerParam_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_handler_param(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            df = get_handler_params(res["handler_id"])
            self.assertEqual(df.shape[0] > 0, True)

    def test_OperationHandlerParam_exists(self) -> None:
        pass

    def test_OperationHandlerParam_exceptions(self) -> None:
        pass
