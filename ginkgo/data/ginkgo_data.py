import os
import sys
import inspect
import importlib
from ginkgo.data.drivers.ginkgo_clickhouse import GINKGOCLICK as gc


class GinkgoData(object):
    def __init__(self):
        self.__models = []
        self.get_models()

    @property
    def session(self):
        return gc.session

    @property
    def engine(self):
        return gc.engine

    def add(self, value):
        self.session.add(value)

    def commit(self):
        self.session.commit()

    def add_all(self, values):
        self.session.add_all(values)

    def get_models(self):
        package_name = "ginkgo/data/models"
        files = os.listdir(package_name)
        for file in files:
            if not (file.endswith(".py") and file != "__init__.py"):
                continue

            file_name = file[:-3]
            package_name = package_name.replace("/", ".")
            module_name = package_name + "." + file_name
            # print(module_name)
            for name, cls in inspect.getmembers(
                importlib.import_module(module_name), inspect.isclass
            ):
                if cls.__module__ == module_name:
                    self.__models.append(cls)

    def create_all(self):
        """
        Create tables with all models without __abstract__ = True.
        """
        for m in self.__models:
            if m.__abstract__ == True:
                print(f"Pass {m}")
                continue

            if gc.is_table_exsists(m.__tablename__):
                print(f"Table {m.__tablename__} exist.")
            else:
                m.__table__.create()
                print(f"Create Table {m.__tablename__} : {m}")

    def drop_all(self):
        """
        ATTENTION!!
        Just call the func in dev.
        This will drop all the tables in models.
        """
        for m in self.__models:
            if gc.is_table_exsists(m.__tablename__):
                m.__table__.drop()
                print(f"Drop Table {m.__tablename__} : {m}")


GINKGODATA = GinkgoData()
