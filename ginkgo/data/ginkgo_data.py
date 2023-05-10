import os
import sys
import inspect
import importlib
import pandas as pd
from ginkgo.data import DBDRIVER as dbdriver
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.models import MCodeOnTrade, MOrder, MBase
from ginkgo.enums import MARKET_TYPES
from ginkgo.data import GinkgoBaoStock


class GinkgoData(object):
    """
    Data Modeul
    Get: from the db
    """

    def __init__(self):
        self.__models = []
        self.get_models()
        self.bs = GinkgoBaoStock()

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

    def get_code_list(self, date: str or datetime.datetime, market: MARKET_TYPES):
        # TODO
        pass

    def insert_code_list(self, df: pd.DataFrame):
        rs = []
        for i in df.iterrows():
            item = MCodeOntrade()
            item.set(i)
            rs.append(item)
        self.add_all(rs)
        self.commit()

    def update_code_list(self, date: str or datetime.datetime):
        # CHINA
        # 1. Get Code List From Bao
        rs = self.bs.fetch_ashare_list(date)
        rs = rs.head(1)
        print(rs)
        # 2. Set up list(ModelCodeOntrade)
        # 3. insert_code_list()

    def update_code_list_to_latest(self):
        # TOOD
        pass

    def update_code_list_to_latest_async(self):
        # TOOD
        pass

    def update_ashare_list(self):
        # TODO
        pass

    def fetch_ashare_stock(self):
        # TODO
        pass

    def insert_ashare_stock(self):
        # TODO
        pass


GINKGODATA = GinkgoData()
