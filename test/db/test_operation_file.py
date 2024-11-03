import unittest
import time
import random
import uuid
from ginkgo.data.drivers import add, add_all, get_table_size, create_table, drop_table
from ginkgo.data.models import MFile
from ginkgo.enums import FILE_TYPES
from ginkgo.data.operations.file_crud import *


class OperationFileTest(unittest.TestCase):
    """
    UnitTest for File CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MFile
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {"type": random.choice([i for i in FILE_TYPES]), "name": uuid.uuid4().hex, "data": b"123"}
            for i in range(cls.count)
        ]

    def test_OperationFile_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_file(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            self.assertEqual(res["type"], i["type"])
            self.assertEqual(res["name"], i["name"])
            self.assertEqual(res["data"], i["data"])

    def test_OperationFile_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_files(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationFile_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            item = add_file(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_file(item.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationFile_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            item = add_file(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_file(item.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

    def test_OperationFile_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_file(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # Update Type
            update_file(res.uuid, type=FILE_TYPES.SELECTOR)
            df = get_file(res.uuid).iloc[0]
            self.assertEqual(df.type, FILE_TYPES.SELECTOR)

            # Update name
            new_name = uuid.uuid4().hex
            update_file(res.uuid, name=new_name)
            df = get_file(res.uuid).iloc[0]
            self.assertEqual(new_name, df["name"])

            # Update content
            new_content = b"testnewnew"
            update_file(res.uuid, data=new_content)
            df = get_file(res.uuid).iloc[0]
            self.assertEqual(df.data, new_content)

            # Update all
            new_name = uuid.uuid4().hex
            new_type = FILE_TYPES.RISKMANAGER
            new_content = b"testnewnew2"
            update_file(res.uuid, name=new_name, type=new_type, data=new_content)
            df = get_file(res.uuid).iloc[0]
            self.assertEqual(new_name, df["name"])
            self.assertEqual(new_type, df.type)
            self.assertEqual(new_content, df.data)

    def test_OperationFile_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_file(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_file(res.uuid).iloc[0]
            self.assertEqual(res.uuid, df["uuid"])

    def test_OperationFile_get_fuzz(self) -> None:
        name_prefix = uuid.uuid4().hex[:5]
        size0 = get_table_size(self.model)
        add_file(type=FILE_TYPES.STRATEGY, name=f"{name_prefix}001", data=b"haha")
        add_file(type=FILE_TYPES.STRATEGY, name=f"{name_prefix}002", data=b"haha")
        size1 = get_table_size(self.model)
        time.sleep(0.01)
        df = get_files(type=FILE_TYPES.STRATEGY)
        self.assertEqual(df.shape[0] >= 2, True)
        print(df)
        df2 = get_files(name=f"{name_prefix}")
        print(df2)

    def test_OperationFile_get_content(self) -> None:
        pass

    def test_OperationFile_exists(self) -> None:
        pass

    def test_OperationFile_exceptions(self) -> None:
        pass
