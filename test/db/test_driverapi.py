# import unittest
# import uuid
# import time
# from sqlalchemy import create_engine, Column, Integer, String, inspect

# from ginkgo.data.drivers import *
# from ginkgo.data.models import MMysqlBase, MClickBase
# from ginkgo.data.models import MOrder

# mysql_test_table_name = f"test_model{str(uuid.uuid4())[:5]}"
# click_test_table_name = f"test_model{str(uuid.uuid4())[:5]}"


# class MysqlTestModel(MMysqlBase):
#     __tablename__ = mysql_test_table_name
#     __abstract__ = False
#     id = Column(Integer, primary_key=True)
#     name = Column(String(20), default="")


# class ClickTestModel(MClickBase):
#     __tablename__ = click_test_table_name
#     __abstract__ = False
#     id = Column(Integer, primary_key=True)
#     name = Column(String(), default="")


# class DriverAPITest(unittest.TestCase):
#     """
#     UnitTest for Clickhouse Driver.
#     """

#     # Init

#     def __init__(self, *args, **kwargs) -> None:
#         super(DriverAPITest, self).__init__(*args, **kwargs)
#         drop_all_tables()

#     def test_DriverAPI_createtable(self) -> None:
#         drop_all_tables()
#         r1 = is_table_exsists(MysqlTestModel)
#         self.assertEqual(
#             False,
#             r1,
#             f"The table `{mysql_test_table_name}` already exists in MySQL, unable to perform the create table test.",
#         )
#         create_table(MysqlTestModel)
#         r2 = is_table_exsists(MysqlTestModel)
#         self.assertEqual(True, r2, f"Failed to create the table `{mysql_test_table_name}` in MySQL.")

#         r3 = is_table_exsists(ClickTestModel)
#         self.assertEqual(
#             False,
#             r3,
#             f"The table `{click_test_table_name}` already exists in Clickhouse, unable to perform the create table test.",
#         )
#         create_table(ClickTestModel)
#         r4 = is_table_exsists(ClickTestModel)
#         self.assertEqual(True, r4, f"Failed to create the table `{click_test_table_name}` in Clickhouse.")

#     def test_DriverAPI_droptable(self) -> None:
#         create_table(MysqlTestModel)
#         r1 = is_table_exsists(MysqlTestModel)
#         self.assertEqual(
#             True,
#             r1,
#             f"The table `{mysql_test_table_name}` should exists in MySQL, unable to perform the drop table test.",
#         )
#         drop_table(MysqlTestModel)
#         time.sleep(0.5)
#         r2 = is_table_exsists(MysqlTestModel)
#         self.assertEqual(False, r2, f"Failed to drop the table `{mysql_test_table_name}` in MySQL.")

#         create_table(ClickTestModel)
#         r3 = is_table_exsists(ClickTestModel)
#         self.assertEqual(
#             True,
#             r3,
#             f"The table `{click_test_table_name}` should exists in Clickhouse, unable to perform the drop table test.",
#         )
#         drop_table(ClickTestModel)
#         r4 = is_table_exsists(ClickTestModel)
#         self.assertEqual(False, r4, f"Failed to drop the table `{click_test_table_name}` in Clickhouse.")

#     # def test_DriverAPI_createalltable(self) -> None:
#     #     drop_all_tables()
#     #     time.sleep(0.2)
#     #     create_all_tables()
#     #     mysql_driver = get_mysql_connection()
#     #     inspector = inspect(mysql_driver.engine)
#     #     db_tables = inspector.get_table_names()
#     #     orm_tables = set(MMysqlBase.metadata.tables.keys())
#     #     self.assertEqual(set(db_tables), orm_tables, "Mysql数据库中的表与ORM定义的表不一致")

#     #     click_driver = get_click_connection()
#     #     inspector = inspect(click_driver.engine)
#     #     db_tables = inspector.get_table_names()
#     #     orm_tables = set(MClickBase.metadata.tables.keys())
#     #     self.assertEqual(set(db_tables), orm_tables, "Clickhouse数据库中的表与ORM定义的表不一致")
#     #     drop_all_tables()
