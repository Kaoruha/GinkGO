import os
import sys
import inspect
import importlib
import pandas as pd
from ginkgo.data import DBDRIVER as dbdriver
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.models.model_base import MBase
from ginkgo.data.models.model_order import MOrder


class GinkgoData(object):
    def __init__(self):
        self.__models = []
        self.get_models()

    @property
    def session(self):
        return dbdriver.session

    @property
    def engine(self):
        return dbdriver.engine

    def add(self, value) -> None:
        self.session.add(value)

    def commit(self) -> None:
        """
        Session Commit.
        """
        self.session.commit()

    def add_all(self, values) -> None:
        """
        Add multi data into session
        """
        # TODO support different database engine.
        # Now is for clickhouse.
        self.session.add_all(values)

    def get_models(self) -> None:
        """
        Read all py files under /data/models
        """
        self.__models = []
        for i in MBase.__subclasses__():
            if i.__abstract__ == True:
                continue
            if i not in self.__models:
                self.__models.append(i)

    def create_all(self) -> None:
        """
        Create tables with all models without __abstract__ = True.
        """
        for m in self.__models:
            self.create_table(m)

    def drop_all(self) -> None:
        """
        ATTENTION!!
        Just call the func in dev.
        This will drop all the tables in models.
        """
        for m in self.__models:
            self.drop_table(m)

    def drop_table(self, model: MBase) -> None:
        if dbdriver.is_table_exsists(model.__tablename__):
            model.__table__.drop()
            gl.logger.warn(f"Drop Table {model.__tablename__} : {model}")

    def create_table(self, model: MBase) -> None:
        if model.__abstract__ == True:
            gl.logger.debug(f"Pass Model:{model}")
            return
        if dbdriver.is_table_exsists(model.__tablename__):
            gl.logger.debug(f"Table {model.__tablename__} exist.")
        else:
            model.__table__.create()
            gl.logger.info(f"Create Table {model.__tablename__} : {model}")

    def get_order(self, order_id: str):
        r = GINKGODATA.session.query(MOrder).filter_by(uuid=order_id).first()
        r.code = r.code.strip(b"\x00".decode())
        return r

    def fetch_ashare_list(self):
        # TODO
        pass

    def insert_ashare_list(self, df):
        # TODO
        pass

    def query_ashare_list(self, date):
        # TODO
        pass

    def fetch_ashare_stock(self):
        # TODO
        pass

    def insert_ashare_stock(self):
        # TODO
        pass

    def query_ashare_stock(self):
        # TODO
        pass


GINKGODATA = GinkgoData()
