import time
import datetime
import os
import pandas as pd
import multiprocessing
import threading
from ginkgo.data import DBDRIVER
from ginkgo.data.sources import GinkgoTushare
from ginkgo.data.models import MOrder, MBase, MBar, MStockInfo, MTradeDay
from ginkgo import GLOG, GCONF
from ginkgo.libs import datetime_normalize, str2bool
from ginkgo.enums import (
    MARKET_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
)
from ginkgo.data.sources import GinkgoBaoStock, GinkgoTushare
from ginkgo.data.drivers import GinkgoClickhouse


class GinkgoData(object):
    """
    Data Modeul
    Get: from the db
    """

    def __init__(self):
        self.__models = []
        self.get_models()
        self.bs = GinkgoBaoStock()
        self.batch_size = 2000

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
            GLOG.WARN(f"Drop Table {model.__tablename__} : {model}")

    def create_table(self, model: MBase) -> None:
        if model.__abstract__ == True:
            GLOG.WARN(f"Pass Model:{model}")
            return
        if DBDRIVER.is_table_exsists(model.__tablename__):
            GLOG.WARN(f"Table {model.__tablename__} exist.")
        else:
            model.__table__.create()
            GLOG.INFO(f"Create Table {model.__tablename__} : {model}")

    def get_table_size(self, model: MBase) -> int:
        return DBDRIVER.get_table_size(model)

    # Query in database
    def get_order(self, order_id: str) -> MOrder:
        r = self.session.query(MOrder).filter(MOrder.uuid == order_id).first()
        r.code = r.code.strip(b"\x00".decode())
        return r

    def get_order_df(self, order_id: str) -> pd.DataFrame:
        r = self.session.query(MOrder).filter(MOrder.uuid == order_id)
        df = pd.read_sql(r.statement, self.engine)
        df.code = df.code.strip(b"\x00".decode())
        return df

    def get_stock_info(self, code: str) -> MStockInfo:
        r = self.session.query(MStockInfo).filter(MStockInfo.code == code).first()
        return r

    def get_stock_info_df(self, code: str) -> pd.DataFrame:
        r = self.session.query(MStockInfo).filter(MStockInfo.code == code)
        df = pd.read_sql(r.statement, self.engine)
        return df

    def get_trade_calendar(
        self,
        market: MARKET_TYPES,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> list:
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            self.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.timestamp >= date_start)
            .filter(MTradeDay.timestamp <= date_end)
            .all()
        )
        return r

    def get_trade_calendar_df(
        self,
        market: MARKET_TYPES,
        date_start: str or datetime.datetime,
        date_end: str or datetime.datetime,
    ) -> pd.DataFrame:
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            self.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.timestamp >= date_start)
            .filter(MTradeDay.timestamp <= date_end)
        )
        df = pd.read_sql(r.statement, self.engine)
        return df

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
            industry = r["industry"] if r["industry"] else "Others"
            list_date = r["list_date"] if r["list_date"] else "2100-01-01"
            delist_date = r["delist_date"] if r["delist_date"] else "2100-01-01"
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
                if (
                    q.code == code
                    and q.code_name == code_name
                    and q.industry == industry
                    and q.currency == CURRENCY_TYPES[r.curr_type.upper()]
                    and q.list_date == datetime_normalize(list_date)
                    and q.delist_date == datetime_normalize(delist_date)
                ):
                    GLOG.DEBUG(f"Ignore Stock Info {code}")
                    continue
                q.code = code
                q.code_name = code_name
                q.industry = industry
                q.currency = CURRENCY_TYPES[r.curr_type.upper()]
                q.list_date = datetime_normalize(list_date)
                q.delist_date = datetime_normalize(delist_date)
                self.commit()
                update_count += 1
                GLOG.DEBUG(f"Update {q.code} stock info")
                continue
            # if not exist, try insert
            l.append(item)
            if len(l) >= self.batch_size:
                self.add_all(l)
                self.commit()
                insert_count += len(l)
                GLOG.DEBUG(f"Insert {len(l)} stock info.")
                l = []
        self.add_all(l)
        self.commit()
        GLOG.DEBUG(f"Insert {len(l)} stock info.")
        insert_count += len(l)
        t1 = datetime.datetime.now()
        GLOG.INFO(
            f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )

    def update_trade_calendar(self) -> None:
        """
        Update all Makets' Calendar
        """
        self.update_cn_trade_calendar()

    def update_cn_trade_calendar(self) -> None:
        t0 = datetime.datetime.now()
        update_count = 0
        insert_count = 0
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_trade_day()
        l = []
        for i, r in df.iterrows():
            item = MTradeDay()
            date = datetime_normalize(r["cal_date"])
            market = MARKET_TYPES.CHINA
            is_open = str2bool(r["is_open"])
            item.set(market, is_open, date)
            item.set_source(SOURCE_TYPES.TUSHARE)
            q = self.get_trade_calendar(market, date, date)
            # Check DB, if exist update
            if len(q) >= 1:
                if len(q) >= 2:
                    GLOG.WARN(f"Trade Calendar have {len(q)} {market} date on {date}")
                for item2 in q:
                    if (
                        item2.timestamp == date
                        and item2.market == market
                        and str2bool(item2.is_open) == is_open
                    ):
                        GLOG.DEBUG(f"Ignore TradeCalendar {date} {market}")
                        continue
                    item2.timestamp = date
                    item2.market = market
                    item2.is_open = is_open
                    update_count += 1
                    self.commit()
                    GLOG.DEBUG(f"Update {item2.timestamp} {item2.market} TradeCalendar")
            else:
                # Not Exist in db
                l.append(item)
                if len(l) >= self.batch_size:
                    self.add_all(l)
                    self.commit()
                    insert_count += len(l)
                    GLOG.DEBUG(f"Insert {len(l)} Trade Calendar.")
                    l = []
        self.add_all(l)
        self.commit()
        GLOG.INFO(f"Insert {len(l)} Trade Calendar.")
        insert_count += len(l)
        t1 = datetime.datetime.now()
        GLOG.INFO(
            f"TradeCalendar Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )


GDATA = GinkgoData()
