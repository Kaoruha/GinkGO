import inspect
import time
import datetime
import os
import pandas as pd
import multiprocessing
import threading
from ginkgo.data import DBDRIVER
from ginkgo.data.sources import GinkgoTushare
from ginkgo.libs import GLOG
from ginkgo.libs import datetime_normalize
from ginkgo.data.models import MOrder, MBase, MBar, MStockInfo
from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES, FREQUENCY_TYPES, CURRENCY_TYPES
from ginkgo.data import GinkgoBaoStock
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse


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
        return DBDRIVER.session

    @property
    def engine(self):
        return DBDRIVER.engine

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
        if DBDRIVER.is_table_exsists(model.__tablename__):
            model.__table__.drop()
            GLOG.logger.warn(f"Drop Table {model.__tablename__} : {model}")

    def create_table(self, model: MBase) -> None:
        if model.__abstract__ == True:
            GLOG.logger.debug(f"Pass Model:{model}")
            return
        if DBDRIVER.is_table_exsists(model.__tablename__):
            GLOG.logger.debug(f"Table {model.__tablename__} exist.")
        else:
            model.__table__.create()
            GLOG.logger.info(f"Create Table {model.__tablename__} : {model}")

    def get_table_size(self, model: MBase) -> int:
        return DBDRIVER.get_table_size(model)

    # Query in database
    def get_order(self, order_id: str) -> MOrder:
        r = self.session.query(MOrder).filter(MOrder.uuid == order_id).first()
        r.code = r.code.strip(b"\x00".decode())
        return r

    def get_stock_info(self, code: str) -> pd.DataFrame:
        r = self.session.query(MStockInfo).filter(MStockInfo.code == code).first()
        return r

    # Daily Data update
    def update_stock_info(self) -> None:
        t0 = datetime.datetime.now()
        update_count = 0
        insert_count = 0
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_info()
        l = []
        for i, r in df.iterrows():
            item = MStockInfo()
            code = r["ts_code"] if r["ts_code"] else "DefaultCode"
            code_name = r["name"] if r["name"] else "DefaultCodeName"
            industry = r["industry"] if r["industry"] else "Other"
            list_date = r["list_date"] if r["list_date"] else "2100-01-01"
            delist_date = r["delist_date"] if r["delist_date"] else "2100-01-01"
            if (
                code is None
                or code_name is None
                or industry is None
                or list_date is None
                or delist_date is None
            ):
                print(r)
            item.set(
                code,
                code_name,
                industry,
                CURRENCY_TYPES[r.curr_type.upper()],
                r.list_date,
                delist_date,
            )
            item.set_source(SOURCE_TYPES.TUSHARE)
            q = self.get_stock_info(r.ts_code)
            # Check DB, if exist, update
            if q is not None:
                q.code = code
                q.code_name = code_name
                q.industry = industry
                q.currency = CURRENCY_TYPES[r.curr_type.upper()]
                q.list_date = datetime_normalize(list_date)
                q.delist_date = datetime_normalize(delist_date)
                self.commit()
                update_count += 1
                GLOG.logger.debug(f"Update {q.code} stock info")
                continue
            # if not exist, try insert
            l.append(item)
            if len(l) >= 1000:
                self.add_all(l)
                self.commit()
                insert_count += len(l)
                GLOG.logger.debug(f"Insert {len(l)} stock info.")
                l = []
        self.add_all(l)
        self.commit()
        GLOG.logger.info(f"Insert {len(l)} stock info.")
        insert_count += len(l)
        t1 = datetime.datetime.now()
        GLOG.logger.info(
            f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )


GDATA = GinkgoData()
