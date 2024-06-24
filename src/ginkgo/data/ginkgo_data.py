import yaml
import uuid
import time
import signal
import psutil
import pickle
import types
import datetime
import os
import pandas as pd
import numpy as np
import multiprocessing
import threading
from rich.console import Console
from rich.progress import Progress
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import or_

from ginkgo.data.models import (
    MAnalyzer,
    MSignal,
    MOrder,
    MOrderRecord,
    MPositionLive,
    MPositionRecord,
    MBar,
    MStockInfo,
    MTradeDay,
    MAdjustfactor,
    MClickBase,
    MMysqlBase,
    MTick,
    MFile,
    MBacktest,
    MLivePortfolio,
)
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize, str2bool
from ginkgo.enums import (
    ORDER_TYPES,
    MARKET_TYPES,
    DIRECTION_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
    TICKDIRECTION_TYPES,
    FILE_TYPES,
    ORDERSTATUS_TYPES,
)
from ginkgo.data.sources import GinkgoBaoStock, GinkgoTushare, GinkgoTDX
from ginkgo.data.drivers import (
    GinkgoClickhouse,
    GinkgoMysql,
    GinkgoRedis,
    GinkgoProducer,
)
from ginkgo.libs.ginkgo_ps import find_process_by_keyword
from ginkgo.backtest.position import Position
from ginkgo.data.drivers.ginkgo_kafka import kafka_topic_llen
from ginkgo.backtest.order import Order


console = Console()


class GinkgoData(object):
    """
    Data Module
    """

    def __init__(self):
        GLOG.DEBUG("Init GinkgoData.")
        self.dataworker_pool_name = "ginkgo_dataworker"  # Conf
        self._click_models = []
        self._mysql_models = []
        self.get_models()
        self.batch_size = 500
        self.cpu_ratio = 0.5
        self.redis_expiration_time = 60 * 60 * 6
        self.max_try = 5
        try:
            self.cpu_ratio = GCONF.CPURATIO
        except Exception as e:
            self.cpu_ratio = 0.8
            GLOG.ERROR(e)
        self.tick_models = {}
        self.cache_daybar_count = 0
        self.cache_daybar_max = 4
        self.timeout = 60
        self._mysql = None
        self._clickhouse = None
        self._redis = None
        self._kafka = None
        self._live_status_name = "live_status"
        self._live_engine_control_name = "live_control"
        self._live_engine_pid_name = "live_engine_pid"

    def send_signal_run_live(self, id: str) -> None:
        self.get_kafka_producer().send(
            "ginkgo_main_control", {"type": "run_live", "id": str(id)}
        )

    def send_signal_stop_live(self, id: str) -> None:
        self.get_kafka_producer().send(
            "ginkgo_main_control", {"type": "stop_live", "id": str(id)}
        )

    def send_signal_run_backtest(self, id: str) -> None:
        self.get_kafka_producer().send(
            "ginkgo_main_control", {"type": "backtest", "id": str(id)}
        )

    def send_signal_stop_dataworker(self):
        self.get_kafka_producer().send(
            "ginkgo_data_update", {"type": "kill", "code": "blabla"}
        )

    def send_signal_test_dataworker(self):
        self.get_kafka_producer().send(
            "ginkgo_data_update", {"type": "other", "code": "blabla1"}
        )

    def send_signal_update_adjust(self, code: str = "") -> None:
        if code == "":
            self.get_kafka_producer().send(
                "ginkgo_data_update", {"type": "adjust", "code": "all", "fast": True}
            )
        else:
            self.get_kafka_producer().send(
                "ginkgo_data_update", {"type": "adjust", "code": code, "fast": True}
            )
        GLOG.DEBUG(f"Send Signal to update {code} adjustfacotr.")

    def send_signal_update_calender(self) -> None:
        self.get_kafka_producer().send(
            "ginkgo_data_update", {"type": "calender", "code": "None", "fast": True}
        )
        GLOG.DEBUG(f"Send Signal to update calender.")

    def send_signal_update_stockinfo(self) -> None:
        self.get_kafka_producer().send(
            "ginkgo_data_update", {"type": "stockinfo", "code": "None", "fast": True}
        )
        GLOG.DEBUG(f"Send Signal to update stockinfo.")

    def send_signal_update_bar(self, code: str, fast_mode: bool = True) -> None:
        self.get_kafka_producer().send(
            "ginkgo_data_update", {"type": "bar", "code": code, "fast": fast_mode}
        )
        GLOG.DEBUG(f"Send Signal to update {code} bar.")

    def send_signal_update_all_bar(self, fast_mode: bool = True) -> None:
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.send_signal_update_bar(code, fast_mode)

    def send_signal_update_tick(self, code: str, fast_mode: bool = True) -> None:
        self.get_kafka_producer().send(
            "ginkgo_data_update", {"type": "tick", "code": code, "fast": fast_mode}
        )
        GLOG.DEBUG(f"Send Signal to update {code} tick.")

    def send_signal_update_all_tick(self, fast_mode: bool = True) -> None:
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.send_signal_update_tick(code, fast_mode)

    def send_signal_to_liveengine(self, engine_id: str, command: str) -> None:
        print(f"try send command to topic: {self._live_engine_control_name}")
        self.get_kafka_producer().send(
            self._live_engine_control_name,
            {"engine_id": engine_id, "command": command, "ttr": 0},
        )

    # Operation about Database >>

    def clean_db(self):
        """
        Have no idea why db connection prevent the multiprocessing pool start.
        Reset the db to solve the problem for now.
        """
        del self._mysql
        del self._clickhouse
        del self._redis
        self._mysql = None
        self._clickhouse = None
        self._redis = None

    def get_driver(self, value):
        is_class = isinstance(value, type)
        driver = None
        if is_class:
            if issubclass(value, MClickBase):
                driver = self.get_click()
            elif issubclass(value, MMysqlBase):
                driver = self.get_mysql()
        else:
            if isinstance(value, MClickBase):
                driver = self.get_click()
            elif isinstance(value, MMysqlBase):
                driver = self.get_mysql()

        if driver is None:
            GLOG.CRITICAL(f"Model {value} should be sub of clickbase or mysqlbase.")

        return driver

    def get_mysql(self) -> GinkgoMysql:
        if self._mysql is None:
            GLOG.DEBUG("Generate Mysql Engine.")
            self._mysql = GinkgoMysql(
                user=GCONF.MYSQLUSER,
                pwd=GCONF.MYSQLPWD,
                host=GCONF.MYSQLHOST,
                port=GCONF.MYSQLPORT,
                db=GCONF.MYSQLDB,
            )
        return self._mysql

    def get_click(self) -> GinkgoClickhouse:
        if self._clickhouse is None:
            GLOG.DEBUG("Generate Clickhouse Engine.")
            self._clickhouse = GinkgoClickhouse(
                user=GCONF.CLICKUSER,
                pwd=GCONF.CLICKPWD,
                host=GCONF.CLICKHOST,
                port=GCONF.CLICKPORT,
                db=GCONF.CLICKDB,
            )
        return self._clickhouse

    def get_redis(self) -> GinkgoRedis:
        if self._redis is None:
            GLOG.DEBUG("Generate Redis Engine.")
            self._redis = GinkgoRedis(GCONF.REDISHOST, GCONF.REDISPORT).redis
        return self._redis

    def get_kafka_producer(self) -> GinkgoProducer:
        if self._kafka is None:
            self._kafka = GinkgoProducer()
        return self._kafka

    def add(self, value) -> None:
        """
        Add a single data item.
        Args:
            value(Model): Data Model
        Returns:
            None
        """
        if not isinstance(value, (MClickBase, MMysqlBase)):
            GLOG.ERROR(f"Can not add {value} to database.")
            return
        GLOG.DEBUG("Try add data to session.")
        for i in range(self.max_try):
            driver = self.get_driver(value)
            try:
                driver.session.add(value)
                driver.session.commit()
                driver.session.close()
            except Exception as e:
                driver.session.rollback()
                GLOG.CRITICAL(f"{type(value)} add failed {i+1}/{self.max_try}")
                print(e)
                time.sleep(1)

    def add_all(self, values) -> None:
        """
        Add multi data into session.
        """
        GLOG.DEBUG("Try add multi data to session.")
        click_list = []
        mysql_list = []
        for i in values:
            if isinstance(i, MClickBase):
                GLOG.DEBUG(f"Add {type(i)} to clickhouse session.")
                click_list.append(i)
            elif isinstance(i, MMysqlBase):
                GLOG.DEBUG(f"Add {type(i)} to mysql session.")
                mysql_list.append(i)
            else:
                GLOG.WARN("Just support clickhouse and mysql now. Ignore other type.")

        for i in range(self.max_try):
            click_driver = self.get_click()
            mysql_driver = self.get_mysql()
            try:
                if len(click_list) > 0:
                    click_driver.session.add_all(click_list)
                    click_driver.session.commit()
                    click_driver.session.close()
                    GLOG.DEBUG(f"Clickhouse commit {len(click_list)} records.")
            except Exception as e:
                click_driver.session.rollback()
                GLOG.CRITICAL(f"ClickHouse add failed {i+1}/{self.max_try}")
                print(e)
                time.sleep(1)
        for i in range(self.max_try):
            try:
                if len(mysql_list) > 0:
                    mysql_driver.session.add_all(mysql_list)
                    mysql_driver.session.commit()
                    mysql_driver.session.close()
                    GLOG.DEBUG(f"Mysql commit {len(mysql_list)} records.")
            except Exception as e:
                print(e)
                mysql_driver.session.rollback()
                GLOG.CRITICAL(f"Mysql add failed {i+1}/{self.max_try}")
                time.sleep(1)

    def get_tick_model(self, code: str) -> type:
        """
        Tick data can not be stored in one table.
        Do database partitioning first.
        Class of Tick model will generate dynamically.
        """
        name = f"{code}.Tick"
        if name in self.tick_models.keys():
            return self.tick_models[name]
        newclass = type(
            name,
            (MTick,),
            {
                "__tablename__": name,
                "__abstract__": False,
            },
        )
        self.tick_models[name] = newclass
        return newclass

    def get_models(self) -> None:
        """
        Read all py files under /data/models
        """
        GLOG.DEBUG(f"Try to read all models.")
        click_count = 0
        mysql_count = 0
        self._click_models = []
        self._mysql_models = []
        for i in MClickBase.__subclasses__():
            if i.__abstract__ == True:
                continue
            if i not in self._click_models:
                self._click_models.append(i)
                click_count += 1

        for i in MMysqlBase.__subclasses__():
            if i.__abstract__ == True:
                continue
            if i not in self._mysql_models:
                self._mysql_models.append(i)
                mysql_count += 1
        GLOG.DEBUG(f"Read {click_count} clickhouse models.")
        GLOG.DEBUG(f"Read {mysql_count} mysql models.")

    def create_all(self) -> None:
        """
        Create tables with all models without __abstract__ = True.
        """
        # Create Tables in clickhouse
        click_driver = self.get_click()
        mysql_driver = self.get_mysql()
        MClickBase.metadata.create_all(click_driver.engine)
        # Create Tables in mysql
        MMysqlBase.metadata.create_all(mysql_driver.engine)
        GLOG.DEBUG(f"{type(self)} Create all tables.")

    def drop_all(self) -> None:
        """
        ATTENTION!!
        Just call the func in dev.
        This will drop all the tables in models.
        """
        # Drop Tables in clickhouse
        MClickBase.metadata.drop_all(self.get_click().engine)
        # Drop Tables in mysql
        MMysqlBase.metadata.drop_all(self.get_mysql().engine)
        GLOG.WARN(f"{type(self)} drop all tables.")

    def is_table_exsist(self, model) -> bool:
        """
        Check the whether the table exists in the database.
        Auto choose the database driver.
        """
        db = self.get_driver(model)
        if db.is_table_exsists(model.__tablename__):
            return True
        else:
            return False

    def drop_table(self, model) -> None:
        """
        Drop table from Database.
        Support Clickhouse and Mysql now.
        """
        db = self.get_driver(model)
        if db is None:
            GLOG.ERROR(f"Can not get driver for {model}.")
            return
        if self.is_table_exsist(model):
            model.__table__.drop(db.engine)
            GLOG.WARN(f"Drop Table {model.__tablename__} : {model}")
        else:
            GLOG.DEBUG(f"No need to drop {model.__tablename__} : {model}")

    def create_table(self, model) -> None:
        """
        Create table with model.
        Support Clickhouse and Mysql now.
        """
        db = self.get_driver(model)
        if db is None:
            return
        if model.__abstract__ == True:
            GLOG.DEBUG(f"Pass Model:{model}")
            return
        if self.is_table_exsist(model):
            GLOG.DEBUG(f"Table {model.__tablename__} exist.")
        else:
            model.__table__.create(db.engine)
            GLOG.INFO(f"Create Table {model.__tablename__} : {model}")

    def get_table_size(self, model, engine=None) -> int:
        """
        Get the size of table.
        Support Clickhouse and Mysql now.
        """
        db = engine if engine else self.get_driver(model)
        if db is None:
            return 0
        return db.get_table_size(model)

    # << Operation about Database

    # CRUD of ORDER >>
    def get_order_by_id(self, order_id: str, engine=None) -> Order:
        GLOG.DEBUG(f"Try to get Order about {order_id}.")
        data = self.get_order_df_by_id(order_id).iloc[0]
        o = Order()
        o.set(data)
        return o

    def update_order(self, order: Order, engine=None) -> None:
        db = engine if engine else self.get_driver(MOrder)
        order_id = order.uuid
        r = (
            db.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
            .first()
        )
        if r is None:
            return
        r.code = order.code
        r.direction = order.direction
        r.type = order.type
        r.status = order.status
        r.volume = order.volume
        r.limit_price = order.limit_price
        r.frozen = order.frozen
        r.transaction_price = order.transaction_price
        r.remain = order.remain
        r.timestamp = order.timestamp
        db.session.commit()
        db.session.close()

    def get_signal_df_by_backtest_and_code_pagination(
        self,
        portfolio_id: str,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        page: int = 0,
        size: int = 100,
        engine=None,
    ) -> MOrder:
        GLOG.DEBUG(f"Try to get Signal about {portfolio_id}.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MSignal)
        r = (
            db.session.query(MSignal)
            .filter(MSignal.portfolio_id == portfolio_id)
            .filter(MSignal.code == code)
            .filter(MSignal.isdel == False)
            .filter(MSignal.timestamp >= date_start)
            .filter(MSignal.timestamp <= date_end)
            .order_by(MSignal.create)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def get_signal_df_by_backtest_and_date_range_pagination(
        self,
        portfolio_id: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        page: int = 0,
        size: int = 100,
        engine=None,
    ) -> MOrder:
        GLOG.DEBUG(f"Try to get Signal about {portfolio_id}.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MSignal)
        r = (
            db.session.query(MSignal)
            .filter(MSignal.portfolio_id == portfolio_id)
            .filter(MSignal.isdel == False)
            .filter(MSignal.timestamp >= date_start)
            .filter(MSignal.timestamp <= date_end)
            .order_by(MSignal.create)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def get_orderrecord_df(
        self,
        backtest_id: str,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        page: int = 0,
        size: int = 10000,
        engine=None,
    ) -> MOrder:
        GLOG.DEBUG(f"Try to get OrderRecord about {backtest_id} {code}.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MOrderRecord)
        r = (
            db.session.query(MOrderRecord)
            .filter(MOrderRecord.backtest_id == backtest_id)
            .filter(MOrderRecord.code == code)
            .filter(MOrderRecord.isdel == False)
            .filter(MOrderRecord.timestamp >= date_start)
            .filter(MOrderRecord.timestamp <= date_end)
            .order_by(MOrderRecord.create)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def get_order_df_by_backtest_and_date_range_pagination(
        self,
        backtest_id: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        page: int = 0,
        size: int = 100,
        engine=None,
    ) -> MOrder:
        GLOG.DEBUG(f"Try to get Order about {backtest_id}.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.backtest_id == backtest_id)
            .filter(MOrder.isdel == False)
            .filter(MOrder.timestamp >= date_start)
            .filter(MOrder.timestamp <= date_end)
            .order_by(MOrder.create)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def get_order_by_backtest_pagination(
        self, backtest_id: str, page: int = 0, size: int = 100, engine=None
    ) -> MOrder:
        GLOG.DEBUG(f"Try to get Order about {order_id}.")
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.backtest_id == backtest_id)
            .filter(MOrder.isdel == False)
            .order_by(MOrder.create)
            .offset(page * size)
            .limit(size)
            .all()
        )

        if len(r) == 0:
            return []
        for i in r:
            i.code = i.code.strip(b"\x00".decode())
        return r

    def get_order_df_by_backtest_pagination(
        self, backtest_id: str, page: int = 0, size: int = 100, engine=None
    ) -> MOrder:
        GLOG.DEBUG(f"Try to get Order about {order_id}.")
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.backtest_id == backtest_id)
            .filter(MOrder.isdel == False)
            .order_by(MOrder.create)
            .offset(page * size)
            .limit(size)
            .all()
        )
        df = pd.read_sql(r.statement, db.engine)
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        db.session.close()
        return df

    def get_order(self, order_id: str, engine=None) -> MOrder:
        """
        Deprecated. Use get_order_by_id
        """
        GLOG.DEBUG(f"Try to get Order about {order_id}.")
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
            .first()
        )
        if r is not None:
            r.code = r.code.strip(b"\x00".decode())
        return r

    def get_order_df_by_id(self, order_id: str, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()

        if df.shape[0] > 1:
            GLOG.ERROR(
                f"Order_id :{order_id} has {df.shape[0]} records, please check the code and clean the database."
            )
            # TODO clean the database
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        return df

    def get_order_df(self, order_id: str, engine=None) -> pd.DataFrame:
        """
        Deprecated. Use get_order_df_by_id
        """
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()

        if df.shape[0] > 1:
            GLOG.ERROR(
                f"Order_id :{order_id} has {df.shape[0]} records, please check the code and clean the database."
            )
            # TODO clean the database
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        return df

    def get_order_df_by_portfolioid(
        self, portfolio_id: str, engine=None
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.portfolio_id == portfolio_id)
            .filter(MOrder.isdel == False)
            .order_by(MOrder.timestamp.asc())
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()

        if df.shape[0] == 0:
            GLOG.DEBUG("Try get order df by backtest, but no order found.")
            return pd.DataFrame()
        GLOG.DEBUG(f"Get Order DF with backtest: {backtest_id}")
        GLOG.DEBUG(df)
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        return df

    # << CRUD of ORDER

    # Filter with ADJUSTFACTOR >>

    def filter_with_adjustfactor(self, code: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the OHLC with adjustfactor.
        """
        GLOG.DEBUG(f"Cal {code} Adjustfactor.")
        if df.shape[0] == 0:
            GLOG.DEBUG(f"You should not pass a empty dataframe.")
            return pd.DataFrame()
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        date_start = df.loc[0, ["timestamp"]].values[0]
        date_end = df.loc[df.shape[0] - 1, ["timestamp"]].values[0]
        ad = self.get_adjustfactor_df(
            code, date_start=GCONF.DEFAULTSTART, date_end=GCONF.DEFAULTEND
        )
        if ad.shape[0] == 0:
            return df
        ad = ad.sort_values(by="timestamp", ascending=True)
        ad.reset_index(drop=True, inplace=True)
        # new_ad = pd.DataFrame(columns=["timestamp", "adjustfactor"])
        start = datetime_normalize(date_start)
        end = datetime.datetime.now()
        date_range = pd.date_range(start=start, end=end, freq="D")
        ad = ad.set_index("timestamp").reindex(index=date_range)
        ad["adjustfactor"] = ad["adjustfactor"].fillna(method="bfill")
        end = datetime_normalize(date_end)
        date_range = pd.date_range(start=start, end=end, freq="D")
        ad = ad.reindex(index=date_range)
        ad = ad["adjustfactor"]
        ad = ad.to_frame(name="adjustfactor")
        ad.index = pd.to_datetime(ad.index)
        ad.rename(columns={"index": "timestamp"}, inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        df = df[~df.index.duplicated()]
        ad_reindexd = ad.reindex(index=df.index)
        # ad_reindexd = ad_reindexd.drop_duplicates(subset=["timestamp"], keep="first")
        df["open"] = df["open"] / ad["adjustfactor"]
        df["open"] = df["open"].apply(lambda x: round(x, 2))
        df["high"] = df["high"] / ad["adjustfactor"]
        df["high"] = df["high"].apply(lambda x: round(x, 2))
        df["low"] = df["low"] / ad["adjustfactor"]
        df["low"] = df["low"].apply(lambda x: round(x, 2))
        df["close"] = df["close"] / ad["adjustfactor"]
        df["close"] = df["close"].apply(lambda x: round(x, 2))
        df = df.assign(timestamp=df.index)
        df.reset_index(drop=True, inplace=True)
        return df

    def get_stock_info(self, code: str, engine=None) -> MStockInfo:
        GLOG.DEBUG(f"Get Stockinfo about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        r = (
            db.session.query(MStockInfo)
            .filter(MStockInfo.code == code)
            .filter(MStockInfo.isdel == False)
            .first()
        )
        return r

    def get_stock_info_df_by_code(self, code: str = None, engine=None) -> pd.DataFrame:
        GLOG.DEBUG(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        r = (
            db.session.query(MStockInfo)
            .filter(MStockInfo.code == code)
            .filter(MStockInfo.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        db.session.close()
        return df

    def get_stock_info_df_pagination(
        self, page: int = 0, size: int = 100, engine=None
    ) -> pd.DataFrame:
        """
        Deprecated
        """
        GLOG.DEBUG(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        r = (
            db.session.query(MStockInfo)
            .filter(MStockInfo.isdel == False)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        db.session.close()
        return df

    def get_stock_info_df(self, code: str = None, engine=None) -> pd.DataFrame:
        """
        Deprecated
        """
        GLOG.DEBUG(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        if code == "" or code is None:
            r = db.session.query(MStockInfo).filter(MStockInfo.isdel == False)
        else:
            r = (
                db.session.query(MStockInfo)
                .filter(MStockInfo.code == code)
                .filter(MStockInfo.isdel == False)
            )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        db.session.close()
        return df

    def get_stockinfo_df_fuzzy(
        self, filter: str, page: int = 0, size: int = 20, engine=None
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MStockInfo)
        r = (
            db.session.query(MStockInfo)
            .filter(
                or_(
                    MStockInfo.code.like(f"%{filter}%"),
                    MStockInfo.code_name.like(f"%{filter}%"),
                )
            )
            .filter(MStockInfo.isdel == False)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="update", ascending=False)
        df["code_name"] = df["code_name"].apply(lambda x: x.strip("\x00"))
        return df

    def get_trade_calendar(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.DEBUG(f"Try get Trade Calendar.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MTradeDay)
        r = (
            db.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.timestamp >= date_start)
            .filter(MTradeDay.timestamp <= date_end)
            .filter(MTradeDay.isdel == False)
            .all()
        )
        return r

    def get_trade_calendar_df(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> pd.DataFrame:
        GLOG.DEBUG(f"Try get Trade Calendar df.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MTradeDay)
        r = (
            db.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.timestamp >= date_start)
            .filter(MTradeDay.timestamp <= date_end)
            .filter(MTradeDay.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def get_daybar(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.DEBUG(f"Try get DAYBAR about {code} from {date_start} to {date_end}.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MBar)
        r = (
            db.session.query(MBar)
            .filter(MBar.code == code)
            .filter(MBar.isdel == False)
            .filter(MBar.timestamp >= date_start)
            .filter(MBar.timestamp <= date_end)
            .all()
        )
        return r

    def get_daybar_df(
        self,
        code: str = "",
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        adjust: int = 1,  # 0 no adjust, 1 back adjust 2 forward adjust
        engine=None,
    ) -> pd.DataFrame:
        """
        Get the daybar with back adjust.
        """
        GLOG.DEBUG(f"Try get DAYBAR df about {code} from {date_start} to {date_end}.")
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MBar)
        if code == "":
            r = (
                db.session.query(MBar)
                .filter(MBar.timestamp >= date_start)
                .filter(MBar.timestamp <= date_end)
                .filter(MBar.isdel == False)
            )
        else:
            r = (
                db.session.query(MBar)
                .filter(MBar.code == code)
                .filter(MBar.timestamp >= date_start)
                .filter(MBar.timestamp <= date_end)
                .filter(MBar.isdel == False)
            )

        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def get_adjustfactor(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.DEBUG(
            f"Try get ADJUSTFACTOR about {code} from {date_start} to {date_end}."
        )
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MAdjustfactor)
        r = (
            db.session.query(MAdjustfactor)
            .filter(MAdjustfactor.code == code)
            .filter(MAdjustfactor.timestamp >= date_start)
            .filter(MAdjustfactor.timestamp <= date_end)
            .filter(MAdjustfactor.isdel == False)
            .order_by(MAdjustfactor.timestamp.asc())
            .all()
        )
        return self._convert_to_full_cal(r)

    def _convert_to_full_cal(self, df):
        """
        Convert Adjustfactor into Full Calendar.
        """
        # TODO
        # Get Start
        # Get End
        return df

    def get_adjustfactor_df(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.DEBUG(
            f"Try get ADJUSTFACTOR df about {code} from {date_start} to {date_end}."
        )
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(MAdjustfactor)
        r = (
            db.session.query(MAdjustfactor)
            .filter(MAdjustfactor.code == code)
            .filter(MAdjustfactor.timestamp >= date_start)
            .filter(MAdjustfactor.timestamp <= date_end)
            .filter(MAdjustfactor.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.drop_duplicates(subset=["timestamp"], keep="first")
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def is_tick_indb(self, code: str, date: any, engine=None) -> bool:
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return False
        date_start = datetime_normalize(date)
        date_end = date_start + datetime.timedelta(days=1)
        db = engine if engine else self.get_driver(model)
        r = (
            db.session.query(model)
            .filter(model.code == code)
            .filter(model.timestamp >= date_start)
            .filter(model.timestamp <= date_end)
            .filter(model.isdel == False)
            .first()
        )
        if r is None:
            db.session.close()
            return False
        else:
            db.session.close()
            return True

    def get_tick(self, code: str, date_start: any, date_end: any, engine=None) -> MTick:
        GLOG.DEBUG(f"Try get TICK about {code} from {date_start} to {date_end}.")
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return []
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(model)
        r = (
            db.session.query(model)
            .filter(model.code == code)
            .filter(model.timestamp >= date_start)
            .filter(model.timestamp <= date_end)
            .filter(model.isdel == False)
            .all()
        )
        return r

    def get_tick_df_by_daterange(
        self, code: str, date_start: any, date_end: any, engine=None
    ) -> pd.DataFrame:
        GLOG.DEUBG(f"Try get TICK df about {code} from {date_start} to {date_end}.")
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return pd.DataFrame()
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(model)
        r = (
            db.session.query(model)
            .filter(model.code == code)
            .filter(model.timestamp >= date_start)
            .filter(model.timestamp <= date_end)
            .filter(model.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        db.session.close()
        # Adjust
        return df

    def get_tick_df(
        self, code: str, date_start: any, date_end: any, engine=None
    ) -> pd.DataFrame:
        """
        Deprecated, use get_tick_df_by_daterange
        """
        GLOG.DEUBG(f"Try get TICK df about {code} from {date_start} to {date_end}.")
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return pd.DataFrame()
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        db = engine if engine else self.get_driver(model)
        r = (
            db.session.query(model)
            .filter(model.code == code)
            .filter(model.timestamp >= date_start)
            .filter(model.timestamp <= date_end)
            .filter(model.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        db.session.close()
        # TODO adjust
        return df

    def del_tick(self, code: str, date: any) -> None:
        # TODO
        pass

    def update_tick(self, code: str, fast_mode: bool = False, engine=None) -> None:
        GLOG.DEBUG(f"Updating TICK {code}.")
        list_date = self.get_stock_info(code).list_date
        # CreateTable
        model = self.get_tick_model(code)
        self.create_table(model)
        db = engine if engine else self.get_driver(model)
        # Try get
        t0 = datetime.datetime.now()
        insert_count = 0
        tdx = GinkgoTDX()
        nodata_count = 0
        nodata_max = 60
        date = datetime.datetime.now()
        while True:
            # Break
            if fast_mode and nodata_count > nodata_max:
                GLOG.DEBUG(f"{code} No data in {nodata_max} days. Break.")
                print(f"{code} No data in {nodata_max} days. Break.")
                break
            if date < list_date:
                break
            if nodata_count > nodata_max:
                break
            # Query database
            date_start = date.strftime("%Y%m%d")
            date_end = (date + datetime.timedelta(days=1)).strftime("%Y%m%d")
            GLOG.DEBUG(f"Trying to update {code} Tick on {date}")
            print(f"Trying to update {code} Tick on {date}")
            if self.is_tick_indb(code, date_start):
                GLOG.DEBUG(
                    f"{code} Tick on {date} is in database. Go next {nodata_count}/{nodata_max}"
                )
                print(
                    f"{code} Tick on {date} is in database. Go next {nodata_count}/{nodata_max}"
                )
                date = date + datetime.timedelta(days=-1)
                nodata_count = nodata_count + 1 if fast_mode else 0
                continue
            # Check is market open today
            open_day = self.get_trade_calendar_df(
                market=MARKET_TYPES.CHINA, date_start=date_start, date_end=date_start
            )
            if open_day.shape[0] == 0:
                date = date + datetime.timedelta(days=-1)
                continue
            if open_day.is_open.values[0] == "false":
                date = date + datetime.timedelta(days=-1)
                continue

            # Fetch and insert
            rs = tdx.fetch_history_transaction(code, date)
            if rs.shape[0] == 0:
                GLOG.DEBUG(f"{code} No data on {date} from remote.")
                print(f"{code} No data on {date} from remote.")
                date = date + datetime.timedelta(days=-1)
                nodata_count = nodata_count + 1 if fast_mode else 0
                continue
            print(f"Got {rs.shape} records.")

            l = []
            for i, r in rs.iterrows():
                timestamp = f"{date.strftime('%Y-%m-%d')} {r.timestamp}:00"
                price = float(r.price)
                volume = int(r.volume)
                buyorsell = int(r.buyorsell)
                buyorsell = TICKDIRECTION_TYPES(buyorsell)
                item = model()
                item.set(code, price, volume, buyorsell, timestamp)
                l.append(item)
            self.add_all(l)
            print(f"Insert {code} Tick {len(l)}.")
            nodata_count = 0
            insert_count += len(l)
            # ReCheck
            if self.is_tick_indb(code, date_start):
                print(f"{code} {date_start} Insert Recheck Successful.")
            else:
                print(f"{code} {date_start} Insert Failed. Still no data in database.")
            date = date + datetime.timedelta(days=-1)
        t1 = datetime.datetime.now()
        print(f"Updating Tick {code} complete. Cost: {t1-t0}")

    def update_all_cn_tick(self, fast_mode: bool = False) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_tick(code, fast_mode=fast_mode)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update ALL CN TICK cost {t1-t0}")

    def update_all_cn_tick_aysnc(self, fast_mode: bool = False) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        self.clean_db()

        if info.shape[0] == 0:
            console.log(f"[red]No Data Get from DB. Cancel Tick Update Aysnc[/red]")
            return
        cpu_count = multiprocessing.cpu_count()
        cpu_count = int(cpu_count * self.cpu_ratio)
        p = multiprocessing.Pool(cpu_count)
        for i, r in info.iterrows():
            code = r["code"]
            res = p.apply_async(
                self.update_tick,
                args=(
                    code,
                    fast_mode,
                ),
            )

        p.close()
        p.join()
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update All CN Tick Done. Cost: {t1-t0}")

    # Daily Data update
    def update_stock_info(self, engine=None) -> None:
        db = engine if engine else self.get_driver(MStockInfo)
        size = db.get_table_size(MStockInfo)
        GLOG.DEBUG(f"Current Stock Info Size: {size}")
        t0 = datetime.datetime.now()
        update_count = 0
        insert_count = 0
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_info()
        l = []
        with Progress() as progress:
            task = progress.add_task("Updating StockInfo", total=df.shape[0])
            for i, r in df.iterrows():
                item = MStockInfo()
                code = r["ts_code"] if r["ts_code"] else "DefaultCode"
                progress.update(
                    task,
                    advance=1,
                    description=f"Updating StockInfo: [light_coral]{code}[/light_coral]",
                )
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
                q = self.get_stock_info(r.ts_code, engine=db)
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
                    db.session.commit()
                    update_count += 1
                    GLOG.DEBUG(f"Update {q.code} stock info")
                    continue
                # if not exist, try insert
                l.append(item)
                if len(l) >= self.batch_size:
                    self.add_all(l)
                    insert_count += len(l)
                    l = []
            self.add_all(l)
        insert_count += len(l)
        GLOG.DEBUG(f"Insert {len(l)} stock info.")
        t1 = datetime.datetime.now()
        GLOG.INFO(
            f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )
        size = db.get_table_size(MStockInfo)
        GLOG.DEBUG(f"After Update Stock Info Size: {size}")

    def update_trade_calendar(self) -> None:
        """
        Update all Makets' Calendar
        """
        GLOG.INFO("Updating Trade Calendar")
        self.update_cn_trade_calendar()
        # TODO Support more market.

    def update_cn_trade_calendar(self) -> None:
        market = MARKET_TYPES.CHINA
        db = self.get_driver(MTradeDay)
        size = db.get_table_size(MTradeDay)
        GLOG.DEBUG(f"Current Trade Calendar Size: {size}")
        t0 = datetime.datetime.now()
        update_count = 0
        insert_count = 0
        tu = GinkgoTushare()
        l = []
        df = tu.fetch_cn_stock_trade_day()
        with Progress() as progress:
            task = progress.add_task("Updating StockInfo", total=df.shape[0])
            if df is None:
                GLOG.ERROR("Tushare get no data. Update CN TradeCalendar Failed.")
                return
            for i, r in df.iterrows():
                item = MTradeDay()
                date = datetime_normalize(r["cal_date"])
                market = MARKET_TYPES.CHINA
                is_open = str2bool(r["is_open"])
                item.set(market, is_open, date)
                item.set_source(SOURCE_TYPES.TUSHARE)
                q = self.get_trade_calendar(market, date, date, db)
                # Check DB, if exist update
                progress.update(
                    task,
                    advance=1,
                    description=f"Updating CN Trade Day: [light_coral]{date}[light_coral]",
                )
                if len(q) >= 1:
                    if len(q) >= 2:
                        GLOG.ERROR(
                            f"Trade Calendar have {len(q)} {market} date on {date}"
                        )
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
                        item2.update = datetime.datetime.now()
                        update_count += 1
                        db.session.commit()
                        GLOG.DEBUG(
                            f"Update {item2.timestamp} {item2.market} TradeCalendar"
                        )

                if len(q) == 0:
                    # Not Exist in db
                    l.append(item)
                    if len(l) >= self.batch_size:
                        self.add_all(l)
                        insert_count += len(l)
                        GLOG.DEBUG(f"Insert {len(l)} Trade Calendar.")
                        l = []
            self.add_all(l)
        GLOG.DEBUG(f"Insert {len(l)} Trade Calendar.")
        insert_count += len(l)
        t1 = datetime.datetime.now()
        GLOG.INFO(
            f"TradeCalendar Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )
        size = db.get_table_size(MTradeDay)
        db.session.close()
        GLOG.DEBUG(f"After Update Trade Calendar Size: {size}")

    def update_cn_daybar(self, code: str, fast_mode: bool = False) -> None:
        GLOG.DEBUG(f"Try to update CN DAYBAR about {code}.")
        GLOG.INFO(f"Updating CN DAYBAR about {code}.")
        # Get the stock info of code
        t0 = datetime.datetime.now()
        GLOG.DEBUG(f"Get stock info about {code}")
        info = self.get_stock_info_df(code)
        driver = GinkgoClickhouse(
            user=GCONF.CLICKUSER,
            pwd=GCONF.CLICKPWD,
            host=GCONF.CLICKHOST,
            port=GCONF.CLICKPORT,
            db=GCONF.CLICKDB,
        )

        if info is None:
            GLOG.WARN(
                f"{code} not exsit in db, please check your code or try updating the stock info"
            )
            return

        # Got the range of date
        if info.shape[0] == 0:
            GLOG.WARN(f"{code} has no stock info in db.")
            console.print(
                f":zipper-mouth_face: Please run [steel_blue1]ginkgo data update --stockinfo[/steel_blue1] first."
            )
            return
        date_start = info.list_date.values[0]
        date_start = datetime_normalize(str(pd.Timestamp(date_start)))
        date_end = info.delist_date.values[0]
        date_end = datetime_normalize(str(pd.Timestamp(date_end)))
        today = datetime.datetime.now()
        if today < date_end:
            date_end = today

        old_df = self.get_daybar_df(code)
        tu = GinkgoTushare()
        if fast_mode:
            latest_date = old_df.iloc[-1]["timestamp"]
            p = date_end - latest_date
            if p > datetime.timedelta(days=1):
                l = []
                rs = tu.fetch_cn_stock_daybar(code, latest_date, date_end)
                if rs.shape[0] == 0:
                    print(f"No new data about {code} from remote.")
                    return
                for i, r in rs.iterrows():
                    date = datetime_normalize(r["trade_date"])
                    q = self.get_daybar(code, date, date)
                    if len(q) > 0:
                        print(f"{code} at {date} already in db.")
                        continue
                    # New Insert
                    b = MBar()
                    b.set_source(SOURCE_TYPES.TUSHARE)
                    b.set(
                        code,
                        r["open"],
                        r["high"],
                        r["low"],
                        r["close"],
                        r["vol"],
                        FREQUENCY_TYPES.DAY,
                        date,
                    )
                    l.append(b)
                if len(l) == 0:
                    return
                driver.session.add_all(l)
                driver.session.commit()
                GLOG.DEBUG(f"Insert {len(l)} {code} Daybar.")
                print(f"Insert {len(l)} {code} Daybar.")
                return
            else:
                print(f"{code} no need to update.")
                return

        missing_period = [
            [None, None],
        ]

        trade_calendar = self.get_trade_calendar_df(
            MARKET_TYPES.CHINA, date_start, date_end
        )
        if trade_calendar.shape[0] == 0:
            GLOG.WARN("There is no trade calendar.")
            console.print(
                f":zipper-mouth_face: Please run [steel_blue1]ginkgo data update --calendar[/steel_blue1] first."
            )
            return
        trade_calendar = trade_calendar[trade_calendar["is_open"] == "true"]
        trade_calendar.sort_values(by="timestamp", inplace=True, ascending=True)
        trade_calendar = trade_calendar[trade_calendar["timestamp"] >= date_start]
        trade_calendar = trade_calendar[trade_calendar["timestamp"] <= date_end]

        df1 = trade_calendar["timestamp"]
        old_timestamp = old_df.timestamp.values if old_df.shape[0] > 0 else []
        for i, r in trade_calendar.iterrows():
            trade_calendar.loc[i, "in_db"] = r["timestamp"] in old_timestamp
        missing_period = [
            [None, None],
        ]
        last_missing = None
        GLOG.DEBUG(f"Check {code} Daybar Calendar.")
        for i, r in trade_calendar.iterrows():
            current = str(r["timestamp"])
            current = datetime_normalize(current)
            GLOG.DEBUG(f"Daybar Calendar Check {current}  {code}")
            # Check if the bar exist in db
            if r["in_db"] == False:
                last_missing = r["timestamp"]
                if missing_period[0][0] is None:
                    missing_period[0][0] = last_missing
                else:
                    if missing_period[-1][-1] is not None:
                        missing_period.append([last_missing, None])
            elif r["in_db"] == True:
                if missing_period[0][0] is None:
                    continue
                else:
                    missing_period[-1][1] = last_missing
        if missing_period[-1][1] is None:
            missing_period[-1][1] = datetime_normalize(
                trade_calendar.iloc[-1]["timestamp"]
            )
        GLOG.DEBUG(f"Daybar Calendar Check {code} Done.")

        # fetch the data and insert to db
        l = []
        insert_count = 0
        update_count = 0
        GLOG.DEBUG(f"Daybar {code} Missing Period: {len(missing_period)}")
        for period in missing_period:
            if period[0] is None:
                break
            print(period)
            continue
            start = period[0]
            end = period[1]
            GLOG.DEBUG(f"Fetch {code} {info.code_name} from {start} to {end}")
            rs = tu.fetch_cn_stock_daybar(code, start, end)
            # There is no data from date_start to date_end
            if rs.shape[0] == 0:
                GLOG.DEBUG(
                    f"{code} {info.code_name} from {start} to {end} has no records."
                )
                continue

            # rs has data
            for i, r in rs.iterrows():
                date = datetime_normalize(r["trade_date"])
                q = self.get_daybar(code, date, date)
                if len(q) > 0:
                    print(f"{code} at {date} already in db.")
                    continue
                # New Insert
                b = MBar()
                b.set_source(SOURCE_TYPES.TUSHARE)
                b.set(
                    code,
                    r["open"],
                    r["high"],
                    r["low"],
                    r["close"],
                    r["vol"],
                    FREQUENCY_TYPES.DAY,
                    date,
                )
                l.append(b)
                if len(l) >= self.batch_size:
                    driver.session.add_all(l)
                    driver.session.commit()
                    insert_count += len(l)
                    GLOG.DEBUG(f"Insert {len(l)} {code} Daybar.")
                    l = []
        driver.session.add_all(l)
        driver.session.commit()
        insert_count += len(l)
        GLOG.DEBUG(f"Insert {len(l)} {code} Daybar.")
        t1 = datetime.datetime.now()
        GLOG.WARN(
            f"Daybar {code} Update: {update_count} Insert: {insert_count} Cost: {t1-t0}"
        )

    def update_all_cn_daybar(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_cn_daybar(code)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update ALL CN Daybar cost {t1-t0}")

    def update_all_cn_daybar_aysnc(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        self.clean_db()
        if info.shape[0] == 0:
            GLOG.WARN(f"Stock Info is empty.")
            console.print(
                f":zipper-mouth_face: Please run [steel_blue1]ginkgo data update --stockinfo[/steel_blue1] first."
            )

        l = []
        cpu_count = multiprocessing.cpu_count()
        cpu_count = int(cpu_count * self.cpu_ratio)
        p = multiprocessing.Pool(cpu_count)
        for i, r in info.iterrows():
            code = r["code"]
            res = p.apply_async(self.update_cn_daybar, args=(code,))

        p.close()
        p.join()
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update All CN Daybar Done. Cost: {t1-t0}")

    def update_cn_adjustfactor(self, code: str, queue=None) -> None:
        GLOG.DEBUG(f"Updating AdjustFactor {code}")
        t0 = datetime.datetime.now()
        GLOG.DEBUG(f"Try get AdjustFactor {code} from Tushare.")
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_adjustfactor(code)  # This API seems something wrong.
        GLOG.DEBUG(f"Got {df.shape[0]} records about {code} AdjustFactor.")
        if df.shape[0] == 0:
            return
        GLOG.DEBUG(f"Got {df.shape[0]} records about {code} AdjustFactor.")
        insert_count = 0
        update_count = 0
        driver = self.get_mysql()
        l = []
        GLOG.DEBUG(f"Ergodic {code} AdjustFactor.")
        for i, r in df.iterrows():
            code = r["ts_code"]
            date = datetime_normalize(r["trade_date"])
            factor = r["adj_factor"]

            # Check ad if exist in database
            # Data in database
            GLOG.DEBUG(f"Try to get ADJUST {code} {date} from database.")
            q = self.get_adjustfactor(code, date, date)
            # If exist, update
        #     if len(q) >= 1:
        #         # TODO Database seem not have duplicated data. But get_adjustfactor function return multi.
        #         if len(q) >= 2:
        #             GLOG.ERROR(
        #                 f"Should not have {len(q)} {code} AdjustFactor on {date}"
        #             )
        #         GLOG.DEBUG(f"Got {len(q)} {code} AdjustFactor on {date}, update it.")
        #         for item in q:
        #             if (
        #                 item.code == code
        #                 and item.timestamp == date
        #                 and float(item.adjustfactor) == factor
        #             ):
        #                 GLOG.DEBUG(f"Ignore Adjustfactor {code} {date}")
        #                 continue
        #             item.adjustfactor = factor
        #             item.update = datetime.datetime.now()
        #             update_count += 1
        #             driver.session.commit()
        #             GLOG.DEBUG(f"Update {code} {date} AdjustFactor")

        #     # If not exist, new insert
        #     elif len(q) == 0:
        #         GLOG.DEBUG(f"No {code} {date} AdjustFactor in database.")
        #         # Insert
        #         adjs = self.get_adjustfactor(code, GCONF.DEFAULTSTART, date)
        #         if len(adjs) == 0 or adjs is None:
        #             o = MAdjustfactor()
        #             o.set_source(SOURCE_TYPES.TUSHARE)
        #             o.set(code, 1.0, 1.0, factor, date)
        #             l.append(o)
        #             GLOG.DEBUG(f"Add AdjustFactor {code} {date} to list.")
        #         elif len(adjs) > 0:
        #             latest = adjs[-1]
        #             if float(latest.adjustfactor) == factor:
        #                 GLOG.DEBUG(
        #                     f"Adjust {code} {date} is same., just update the update time."
        #                 )
        #                 latest.update_time(date)
        #                 update_count += 1
        #                 driver.session.commit()
        #             else:
        #                 GLOG.DEBUG(
        #                     f"Adjust {code} {date} is different. update the factor."
        #                 )
        #                 o = MAdjustfactor()
        #                 o.set_source(SOURCE_TYPES.TUSHARE)
        #                 o.set(code, 1.0, 1.0, factor, date)
        #                 l.append(o)
        #     if len(l) > self.batch_size:
        #         driver.session.add_all(l)
        #         driver.session.commit()
        #         insert_count += len(l)
        #         GLOG.DEBUG(f"Insert {len(l)} {code} AdjustFactor.")
        #         l = []
        # if len(l) > 0:
        #     driver.session.add_all(l)
        #     driver.session.commit()
        #     insert_count += len(l)
        #     GLOG.DEBUG(f"Insert {len(l)} {code} AdjustFactor.")
        # self.clean_db()
        # t1 = datetime.datetime.now()
        # GLOG.DEBUG(
        #     f"AdjustFactor {code} Update: {update_count} Insert: {insert_count} Cost: {t1-t0}"
        # )

    def update_all_cn_adjustfactor(self):
        GLOG.DEBUG(f"Begin to update all CN AdjustFactor")
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        info = info[100:102]
        with Progress() as progress:
            task = progress.add_task("Updating CN AdjustFactor: ", total=info.shape[0])
            for i, r in info.iterrows():
                code = r["code"]
                print(code)
                progress.update(
                    task,
                    advance=1,
                    description=f"Updating AdjustFactor: [light_coral]{code}[/light_coral]",
                )
                self.update_cn_adjustfactor(code, None)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update ALL CN AdjustFactor cost {t1-t0}")

    def start_listen(self, msg: str, max_count: int, queue) -> None:
        with Progress() as progress:
            task = progress.add_task(msg, total=max_count)
            count = 0
            while True:
                try:
                    item = queue.get(block=False)
                    item_str = item if isinstance(item, str) else ""
                    progress.update(
                        task,
                        advance=1,
                        description=f"{msg}: [light_coral]{item_str}[/light_coral]",
                    )
                    count += 1
                except Exception as e:
                    time.sleep(0.2)
                if count == max_count:
                    break

    def update_all_cn_adjustfactor_aysnc(self):
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        l = []
        cpu_count = multiprocessing.cpu_count()
        cpu_count = int(cpu_count * self.cpu_ratio)
        for i, r in info.iterrows():
            code = r["code"]
            l.append(code)

        p = multiprocessing.Pool(cpu_count)
        q = multiprocessing.Manager().Queue()

        t = threading.Thread(
            target=self.start_listen, args=("Updating CN AdjustFactor", len(l), q)
        )

        for code in l:
            res = p.apply_async(
                self.update_cn_adjustfactor,
                args=(
                    code,
                    q,
                ),
            )

        p.close()
        t.start()
        p.join()
        t.join()
        t1 = datetime.datetime.now()
        size = self.get_mysql().get_table_size(MAdjustfactor)
        GLOG.INFO(f"Update ALL CN AdjustFactor cost {t1-t0}")
        GLOG.INFO(f"After Update Adjustfactor Size: {size}")

    def get_file(self, id: str, engine=None) -> MFile:
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.uuid == id)
            .filter(MFile.isdel == False)
            .first()
        )
        return r

    def get_file_by_id(self, file_id: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.uuid == file_id)
            .filter(MFile.isdel == False)
            .first()
        )
        return r

    def get_file_by_backtest(self, backtest_id: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.backtest_id == backtest_id)
            .filter(MFile.isdel == False)
            .first()
        )
        return r

    def get_file_by_name(self, name: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.file_name == name)
            .filter(MFile.isdel == False)
            .first()
        )
        return r

    def get_file_list_df(
        self, type: FILE_TYPES = None, page: int = 0, size: int = 20, engine=None
    ):
        db = engine if engine else self.get_driver(MFile)
        if type is None:
            r = db.session.query(MFile).filter(MFile.isdel == False)
        else:
            r = (
                db.session.query(MFile)
                .filter(MFile.type == type)
                .filter(MFile.isdel == False)
                .offset(page * size)
                .limit(size)
            )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="update", ascending=False)
        df["file_name"] = df["file_name"].apply(lambda x: x.strip("\x00"))
        return df

    def get_file_list_df_fuzzy(
        self, filter: str, page: int = 0, size: int = 20, engine=None
    ):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.file_name.like(f"%{filter}%"))
            .filter(MFile.isdel == False)
            .order_by(MFile.update.desc())
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="update", ascending=False)
        df["file_name"] = df["file_name"].apply(lambda x: x.strip("\x00"))
        return df

    def update_file(
        self,
        id: str,
        type: FILE_TYPES = None,
        name: str = "",
        content: bytes = b"",
        engine=None,
    ):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.uuid == id)
            .filter(MFile.isdel == False)
            .first()
        )
        if r is None:
            db.session.close()
            return
        if r.islive == True:
            console.print(f":sad: Can not edit file {r.name} locked for live.")
            return
        if type is not None:
            r.type = type
        if len(name) > 0:
            r.file_name = name
        if len(content) > 0:
            print(f"Raw content: {r.content}")
            r.content = content
        r.update = datetime.datetime.now()
        print(f"Content: {r.content}")
        db.session.commit()
        r = db.session.query(MFile).filter(MFile.uuid == id).first()
        print("After update")
        print(r.uuid)
        print(r.content)
        db.session.close()
        self.clean_db()

    def copy_file(
        self, type: FILE_TYPES, name: str, source: str, is_live: bool = False
    ) -> MFile:
        file = self.get_file(source)
        if file is None:
            GLOG.DEBUG(f"File {source} not exist. Copy failed.")
            return
        item = MFile()
        item.type = type
        item.file_name = name
        item.islive = is_live
        item.content = file.content
        if type == FILE_TYPES.BACKTEST:
            try:
                content = yaml.safe_load(file.content.decode("utf-8"))
                content["name"] = name
                item.content = yaml.dump(content).encode("utf-8")
            except Exception as e:
                print(e)
        id = item.uuid
        self.add(item)
        return id

    def add_file(
        self,
        type: FILE_TYPES,
        name: str,
    ) -> MFile():
        item = MFile()
        file_id = item.uuid
        item.type = type
        item.file_name = name
        item.content = b""
        self.add(item)
        return file_id

    def remove_file(self, id: str) -> bool:
        db = self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.uuid == id)
            .filter(MFile.isdel == False)
            .first()
        )
        if r is None:
            return False
        r.update = datetime.datetime.now()
        r.isdel = True
        db.session.commit()
        db.session.close()
        return True

    def init_file(self) -> None:
        def walk_through(folder: str):
            path = f"{file_root}/{folder}"
            files = os.listdir(path)
            black_list = ["__", "base"]
            for file_name in files:
                if any(substring in file_name for substring in black_list):
                    continue
                file_path = f"{path}/{file_name}"
                file_name = file_name.split(".")[0]
                model = self.get_file_by_name(file_name)
                if model is None:
                    with open(file_path, "rb") as file:
                        content = file.read()
                        item = MFile()
                        item.type = file_map[folder]
                        item.file_name = file_name
                        item.content = content
                        self.add(item)
                        console.print(f":sunglasses: Add {file_name}")
                        GLOG.DEBUG(f"Add {file_name}")

        file_map = {
            "analyzers": FILE_TYPES.ANALYZER,
            "risk_managements": FILE_TYPES.RISKMANAGER,
            "selectors": FILE_TYPES.SELECTOR,
            "sizers": FILE_TYPES.SIZER,
            "strategies": FILE_TYPES.STRATEGY,
        }

        working_dir = GCONF.WORKING_PATH
        file_root = f"{working_dir}/src/ginkgo/backtest"
        # BacktestConfig
        default_backtest_name = "Default Backtest"
        backtest_model = self.get_file_by_name(default_backtest_name)
        if backtest_model is None:
            with open(f"{file_root}/backtest_config.yml", "rb") as file:
                content = file.read()
                item = MFile()
                item.type = FILE_TYPES.BACKTEST
                item.file_name = default_backtest_name
                item.content = content
                self.add(item)
                GLOG.DEBUG("Add DefaultStrategy.yml")
        for i in file_map:
            walk_through(i)

    def add_backtest(self, backtest_id: str, content: bytes) -> str:
        item = MBacktest()
        item.set(backtest_id, datetime.datetime.now(), content)
        id = item.uuid
        self.add(item)
        return id

    def add_liveportfolio(self, name: str, engine_id: str, content: bytes) -> str:
        item = MLivePortfolio()
        conf = yaml.safe_load(content)

        # risk manager
        risk_conf = conf["risk_manager"]
        old_risk_id = risk_conf["id"]
        risk_file = self.get_file_by_id(old_risk_id)
        risk_name = risk_file.file_name
        new_risk_name = f"{risk_name}_{name}"
        new_risk_name = new_risk_name[:35]
        new_risk_id = self.copy_file(
            FILE_TYPES.RISKMANAGER, new_risk_name, old_risk_id, True
        )
        conf["risk_manager"]["id"] = new_risk_id

        # selector
        select_conf = conf["selector"]
        old_select_id = select_conf["id"]
        select_file = self.get_file_by_id(old_select_id)
        select_name = select_file.file_name
        new_select_name = f"{select_name}_{name}"
        new_select_name = new_select_name[:35]
        new_select_id = self.copy_file(
            FILE_TYPES.SELECTOR, new_select_name, old_select_id, True
        )
        conf["selector"]["id"] = new_select_id

        # sizer
        sizer_conf = conf["sizer"]
        old_sizer_id = sizer_conf["id"]
        sizer_file = self.get_file_by_id(old_sizer_id)
        sizer_name = sizer_file.file_name
        new_sizer_name = f"{sizer_name}_{name}"
        new_sizer_name = new_sizer_name[:35]
        new_sizer_id = self.copy_file(
            FILE_TYPES.SIZER, new_sizer_name, old_sizer_id, True
        )
        conf["sizer"]["id"] = new_sizer_id

        # strategies
        for i in conf["strategies"]:
            id = i["id"]
            file = self.get_file_by_id(id)
            file_name = file.file_name
            new_name = f"{file_name}_{name}"
            new_name = new_name[:35]
            new_file_id = self.copy_file(FILE_TYPES.STRATEGY, new_name, id, True)
            i["id"] = new_file_id

        # remove analyzers
        del conf["analyzers"]
        print(conf)

        res_id = item.uuid
        content = yaml.dump(conf).encode("utf-8")
        item.set(name, engine_id, datetime.datetime.now(), content)

        self.add(item)
        return res_id

    def get_liveportfolio(self, engine_id: str, engine=None) -> MLivePortfolio:
        db = engine if engine else self.get_driver(MLivePortfolio)
        r = (
            db.session.query(MLivePortfolio)
            .filter(MLivePortfolio.engine_id == engine_id)
            .filter(MLivePortfolio.isdel == False)
            .first()
        )
        return r

    def get_liveportfolio_df(self, engine_id: str, engine=None) -> MLivePortfolio:
        db = engine if engine else self.get_driver(MLivePortfolio)
        r = (
            db.session.query(MLivePortfolio)
            .filter(MLivePortfolio.engine_id == engine_id)
            .filter(MLivePortfolio.isdel == False)
            .first()
        )
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def get_live_related_files(self, engine_id: str) -> list:
        res = []
        file = self.get_liveportfolio(engine_id)
        if file is None:
            return
        content = file.content
        content = yaml.safe_load(file.content.decode("utf-8"))
        res.append(content["risk_manager"]["id"])
        res.append(content["selector"]["id"])
        res.append(content["sizer"]["id"])
        for i in content["strategies"]:
            res.append(i["id"])
        return res

    def del_liveportfolio_related(self, engine_id: str) -> bool:
        files = self.get_live_related_files(engine_id)
        for i in files:
            r = self.remove_file(i)
            if r:
                print(f"Remove file {i}")
            else:
                print(f"File {i} not exist, Remove Failed.")

    def del_liveportfolio(self, engine_id: str) -> bool:
        """
        Del just modify the is_del.
        Remove will erase the data from db.
        """
        db = self.get_driver(MLivePortfolio)
        r = (
            db.session.query(MLivePortfolio)
            .filter(MLivePortfolio.uuid == engine_id)
            .filter(MLivePortfolio.isdel == False)
            .first()
        )
        if r is None:
            return False
        r.update = datetime.datetime.now()
        r.isdel = True
        # Remove from db
        # TODO Remove all related file
        db.session.commit()
        db.session.close()
        return True

    def add_liveportfolio_from_backtest(self, backtest_id: str, name: str) -> None:
        res = self.get_backtest_record(backtest_id)
        if res is None:
            GLOG.WARN(f"No backtest with id {backtest_id}")
            return
        content = res.content

        id = uuid.uuid4().hex
        self.add_liveportfolio(name, id, content)

    def remove_liveportfolio(
        self,
        id: str,
    ) -> None:
        db = self.get_driver(MLivePortfolio)
        try:
            db.session.query(MLivePortfolio).filter(MLivePortfolio.uuid == id).delete()
            db.session.commit()
            db.session.close()
            return True
        except Exception as e:
            print(e)
            return False

    def get_liveportfolio_pagination(
        self, page: int = 0, size: int = 100, engine=None
    ) -> MLivePortfolio:
        db = engine if engine else self.get_driver(MLivePortfolio)
        r = (
            db.session.query(MLivePortfolio)
            .filter(MLivePortfolio.isdel == False)
            .order_by(MLivePortfolio.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        db.session.close()
        return r

    def get_liveportfolio_df_pagination(
        self, page: int = 0, size: int = 100, engine=None
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MLivePortfolio)
        r = (
            db.session.query(MLivePortfolio)
            .filter(MLivePortfolio.isdel == False)
            .order_by(MLivePortfolio.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="start_at", ascending=False)
        db.session.close()
        return df

    def add_signal(
        self,
        portfolio_id: str,
        timestamp: any,
        code: str,
        direction: DIRECTION_TYPES,
        reason: str,
    ) -> str:
        item = MSignal()
        item.set(portfolio_id, timestamp, code, direction, reason)
        id = item.uuid
        self.add(item)
        return id

    def remove_backtest(self, backtest_id: str) -> bool:
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.uuid == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is None:
            return False
        db.session.delete(r)
        db.session.commit()
        db.session.close()
        return True

    def finish_backtest(self, backtest_id: str) -> bool:
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is None:
            GLOG.DEBUG(f"Can not find backtest {backtest_id} in database.")
            return False
        r.finish(datetime.datetime.now())
        db.session.commit()
        db.session.close()
        GLOG.DEBUG(f"Backtest {backtest_id} finished.")
        return True

    def remove_orders(self, backtest_id: str) -> int:
        db = self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.backtest_id == backtest_id)
            .filter(MOrder.isdel == False)
            .all()
        )
        count = len(r)
        if len(r) > 0:
            for i in r:
                db.session.delete(i)
            db.session.commit()
        db.session.close()
        return count

    def remove_orderrecord_by_id(self, id: str) -> bool:
        db = self.get_driver(MOrderRecord)
        try:
            db.session.query(MOrderRecord).filter(MOrderRecord.uuid == id).delete()
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            db.session.close()
            self.clean_db()

    def remove_orderrecords_by_portfolio(self, id: str) -> bool:
        db = self.get_driver(MOrderRecord)
        try:
            db.session.query(MOrderRecord).filter(
                MOrderRecord.portfolio_id == id
            ).delete()
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            db.session.close()
            self.clean_db()

    def remove_analyzers(self, backtest_id: str) -> int:
        db = self.get_driver(MAnalyzer)
        try:
            r = (
                db.session.query(MAnalyzer)
                .filter(MAnalyzer.backtest_id == backtest_id)
                .all()
            )
            count = len(r)
            db.session.query(MAnalyzer).filter(
                MAnalyzer.backtest_id == backtest_id
            ).delete()
            return count
        except Exception as e:
            print(e)
            return 0
        finally:
            db.session.close()
            self.clean_db()

    def update_backtest_worth(self, backtest_id: str, worth: float) -> bool:
        if backtest_id == "":
            GLOG.ERROR("Can not update the backtest record with empty backtest_id.")
            return False
        if not isinstance(worth, (int, float)):
            GLOG.ERROR(f"Can not update the backtest record with {type(worth)}.")
            return False
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is None:
            return False
        else:
            r.profit = worth
            db.session.commit()
            return True

    def finish_backtest(self, backtest_id: str) -> bool:
        if backtest_id == "":
            GLOG.DEBUG("Can not finish the backtest record with empty backtest_id.")
            return False
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is None:
            return False
        else:
            r.finish(datetime.datetime.now())
            db.session.commit()
            return True

    def get_backtest_record_by_backtest(self, backtest_id: str) -> MBacktest:
        db = self.get_driver(MBacktest)
        if backtest_id == "":
            GLOG.DEBUG("Can not get backtest record with empty backtest_id.")
            return
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.uuid == backtest_id)
            .filter(MBacktest.isdel == False)
            .order_by(MBacktest.start_at.desc())
            .first()
        )
        return r

    def get_backtest_record(self, backtest_id: str) -> MBacktest:
        db = self.get_driver(MBacktest)
        if backtest_id == "":
            GLOG.DEBUG("Can not get backtest record with empty backtest_id.")
            return
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.uuid == backtest_id)
            .filter(MBacktest.isdel == False)
            .order_by(MBacktest.start_at.desc())
            .first()
        )
        return r

    def get_backtest_record_pagination(
        self, page: int = 0, size: int = 100, engine=None
    ) -> MBacktest:
        db = engine if engine else self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.isdel == False)
            .order_by(MBacktest.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        db.session.close()
        return r

    def get_backtest_record_df_pagination(
        self, page: int = 0, size: int = 100, engine=None
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.isdel == False)
            .order_by(MBacktest.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="start_at", ascending=False)
        db.session.close()
        return df

    def get_backtest_list_df(self, backtest_id: str = "") -> pd.DataFrame:
        db = self.get_driver(MBacktest)
        if backtest_id == "":
            r = db.session.query(MBacktest).filter(MBacktest.isdel == False)
        else:
            r = (
                db.session.query(MBacktest)
                .filter(MBacktest.backtest_id == backtest_id)
                .filter(MBacktest.isdel == False)
                .order_by(MBacktest.start_at.desc())
            )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="start_at", ascending=False)
        return df

    def add_analyzer(
        self,
        backtest_id: str,
        timestamp: any,
        value: float,
        name: str,
        analyzer_id: str,
    ) -> None:
        db = self.get_driver(MAnalyzer)
        item = MAnalyzer()
        item.set(backtest_id, timestamp, value, name, analyzer_id)
        self.add(item)

    def get_analyzers_df_by_backtest(
        self, backtest_id: str, engine=None
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MAnalyzer)
        r = (
            db.session.query(MAnalyzer)
            .filter(MAnalyzer.backtest_id == backtest_id)
            .filter(MAnalyzer.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)

        if df.shape[0] == 0:
            GLOG.DEBUG("Try get analyzer df by backtest, but no order found.")
            return pd.DataFrame()
        GLOG.DEBUG(f"Get Analyzer DF with backtest: {backtest_id}")
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)

        return df

    def get_analyzer_df_by_backtest(
        self, backtest_id: str, analyzer_id: str, engine=None
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MAnalyzer)
        r = (
            db.session.query(MAnalyzer)
            .filter(MAnalyzer.backtest_id == backtest_id)
            .filter(MAnalyzer.analyzer_id == analyzer_id)
            .filter(MAnalyzer.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)

        if df.shape[0] == 0:
            GLOG.DEBUG("Try get analyzer df by backtest, but no order found.")
            return pd.DataFrame()
        GLOG.DEBUG(f"Get Analyzer DF with backtest: {backtest_id}")
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)

        return df

    def add_order_record(
        self,
        portfolio_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        transaction_price: float,
        volume: int,
        remain: float,
        fee: float,
        timestamp: any,
        engine=None,
    ) -> None:
        db = engine if engine else self.get_driver(MOrderRecord)
        item = MOrderRecord()
        item.set(
            portfolio_id,
            code,
            direction,
            order_type,
            volume,
            transaction_price,
            remain,
            fee,
            timestamp,
        )
        self.add(item)

    def update_order_record(
        self,
        id: str,
        code: str,
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        transaction_price: float,
        volume: int,
        remain: float,
        fee: float,
        timestamp: any,
        engine=None,
    ) -> None:
        db = engine if engine else self.get_driver(MOrderRecord)
        r = db.session.query(MOrderRecord).filter(MOrderRecord.uuid == id).first()
        pid = r.portfolio_id
        if r is None:
            return
        res = self.remove_orderrecord_by_id(id)
        if not res:
            return

        self.add_order_record(
            pid,
            code,
            direction,
            ORDER_TYPES.LIMITORDER,
            transaction_price,
            volume,
            0,
            fee,
            timestamp,
        )

        db.session.commit()
        db.session.close()
        self.clean_db()

    def get_orderrecord_pagination(
        self,
        portfolio_id: str,
        timestart: any,
        timeend: any,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MOrderRecord)
        timestart = datetime_normalize(timestart)
        timeend = datetime_normalize(timeend)
        r = (
            db.session.query(MOrderRecord)
            .filter(MOrderRecord.portfolio_id == portfolio_id)
            .filter(MOrderRecord.timestamp >= timestart)
            .filter(MOrderRecord.timestamp <= timeend)
            .filter(MOrderRecord.isdel == False)
            .order_by(MOrderRecord.create)
            .offset(page * size)
            .limit(size)
        )
        return r

    def get_orderrecord_df_pagination(
        self,
        portfolio_id: str,
        timestart: any,
        timeend: any,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MOrderRecord)
        timestart = datetime_normalize(timestart)
        timeend = datetime_normalize(timeend)
        r = (
            db.session.query(MOrderRecord)
            .filter(MOrderRecord.portfolio_id == portfolio_id)
            .filter(MOrderRecord.timestamp >= timestart)
            .filter(MOrderRecord.timestamp <= timeend)
            .filter(MOrderRecord.isdel == False)
            .order_by(MOrderRecord.create)
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df["code"] = df["code"].str.replace("\x00", "")
        df["portfolio_id"] = df["portfolio_id"].str.replace("\x00", "")
        db.session.close()
        return df

    def add_position_record(
        self,
        portfolio_id: str,
        timestamp: any,
        code: str,
        volume: int,
        cost: float,
    ) -> None:
        item = MPositionRecord()
        item.set(portfolio_id, timestamp, code, volume, cost)
        GDATA.add(item)

    def add_position_records(
        self, portfolio_id: str, timestamp: any, positions: list
    ) -> None:
        for i in positions:
            if not isinstance(i, Position):
                GLOG.DEBUG(f"Only support add Position")
                return
        l = []
        for i in positions:
            item = MPositionRecord()
            item.set(portfolio_id, timestamp, i.code, i.volume, i.cost)
            l.append(item)
        self.add_all(l)

    def get_positionlives_pagination(
        self,
        portfolio_id: str,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MPositionLive)
        r = (
            db.session.query(MPositionLive)
            .filter(MPositionLive.portfolio_id == portfolio_id)
            .filter(MPositionLive.isdel == False)
            .offset(page * size)
            .limit(size)
            .all()
        )
        db.session.close()
        return r

    def get_positionlive_via_code(
        self,
        portfolio_id: str,
        code: str,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MPositionLive)
        r = (
            db.session.query(MPositionLive)
            .filter(MPositionLive.portfolio_id == portfolio_id)
            .filter(MPositionLive.code == code)
            .filter(MPositionLive.isdel == False)
            .first()
        )
        db.session.close()
        return r

    def update_positionlive(
        self,
        portfolio_id: str,
        code: str,
        price: float,
        cost: float,
        volume: int,
        frozen: float,
        fee: float,
        engine=None,
    ) -> None:
        db = engine if engine else self.get_driver(MPositionLive)
        p = (
            db.session.query(MPositionLive)
            .filter(MPositionLive.portfolio_id == portfolio_id)
            .filter(MPositionLive.code == code)
            .filter(MPositionLive.isdel == False)
            .first()
        )
        if p is None:
            GLOG.WARN(f"POSITION about {code} in PORTFOLIO {portfolio_id} not exist.")
            return
        try:
            p.price = float(price)
            p.cost = float(cost)
            p.volume = int(volume)
            p.frozen = int(frozen)
            p.fee = float(fee)
            p.update = datetime.datetime.now()
            db.session.commit()
            db.session.close()
        except Exception as e:
            print(e)

    def add_positionlive(
        self,
        portfolio_id: str,
        code: str,
        price: float,
        volume: int,
        cost: float,
    ):
        item = MPositionLive()
        item.set(portfolio_id, datetime.datetime.now(), code, price, cost, volume)
        self.add(item)

    def remove_positionlives(self, portfolio_id: str, engine=None):
        db = engine if engine else self.get_driver(MPositionLive)
        db.session.query(MPositionLive).filter(
            MPositionLive.portfolio_id == portfolio_id
        ).delete()
        GLOG.DEBUG(f"Remove positions about PORTFOLIO:{portfolio_id}.")

    def get_positionrecords_pagination(
        self,
        backtest_id: str,
        timestamp: any,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        date_start = datetime_normalize(timestamp)
        date_end = datetime_normalize(timestamp) + datetime.timedelta(days=1)
        db = engine if engine else self.get_driver(MPositionRecord)
        r = (
            db.session.query(MPositionRecord)
            .filter(MPositionRecord.portfolio_id == portfolio_id)
            .filter(MPositionRecord.timestamp >= date_start)
            .filter(MPositionRecord.timestamp < date_end)
            .filter(MPositionRecord.isdel == False)
            .offset(page * size)
            .limit(size)
            .all()
        )
        db.session.close()
        return r

    def remove_positions(self, backtest_id: str, engine=None) -> int:
        db = engine if engine else self.get_driver(MPositionRecord)
        r = (
            db.session.query(MPositionRecord)
            .filter(MPositionRecord.portfolio_id == backtest_id)
            .filter(MPositionRecord.isdel == False)
            .all()
        )
        count = 0
        for i in r:
            db.session.delete(i)
            count += 1
        db.session.commit()
        db.session.close()
        return count

    def set_live_status(self, engine_id: str, status: str) -> None:
        self.get_redis().hset(self._live_status_name, engine_id, status)

    def remove_live_status(self, engine_id: str) -> None:
        self.get_redis().hdel(self._live_status_name, engine_id)
        pass

    def get_live_status(self) -> dict:
        data = self.get_redis().hgetall(self._live_status_name)
        return {
            key.decode("utf-8"): value.decode("utf-8") for key, value in data.items()
        }

    def get_live_status_by_id(self, engine_id: str) -> str:
        status = self.get_redis().hget(self._live_status_name, engine_id)
        return status.decode("utf-8") if status else None

    def clean_live_status(self) -> dict:
        self.clean_liveengine()
        live = self.get_liveengine()
        status = self.get_live_status()
        clean_list = []
        for i in status:
            if i in live:
                continue
            clean_list.append(i)
        for i in clean_list:
            self.remove_live_status(i)
        return self.get_live_status()

    def add_liveengine(self, engine_id: str, pid: int) -> None:
        self.clean_liveengine()
        self.remove_liveengine(engine_id)
        self.get_redis().hset(self._live_engine_pid_name, engine_id, pid)

    def get_liveengine(self) -> dict:
        data = self.get_redis().hgetall(self._live_engine_pid_name)
        return {
            key.decode("utf-8"): value.decode("utf-8") for key, value in data.items()
        }

    def remove_liveengine(self, engine_id: str) -> None:
        pid = self.get_pid_of_liveengine(engine_id)
        if pid is not None:
            GLOG.WARN(f"{engine_id} exist, try kill the Proc: {pid}")
            try:
                proc = psutil.Process(int(pid))
                if proc.is_running():
                    os.kill(int(pid), signal.SIGKILL)
                    GLOG.WARN(f"Killed the Proc: {pid}")
            except Exception as e:
                pass
        self.get_redis().hdel(self._live_engine_pid_name, engine_id)

    def clean_liveengine(self) -> None:
        res = self.get_liveengine()
        clean_list = []
        accept_status = ["running", "sleeping"]
        for engine_id in res:
            pid = self.get_pid_of_liveengine(engine_id)
            try:
                proc = psutil.Process(int(pid))
                proc_status = proc.status()
                if proc_status not in accept_status:
                    clean_list.append(engine_id)
            except psutil.NoSuchProcess:
                clean_list.append(engine_id)
            except psutil.AccessDenied:
                clean_list.append(engine_id)
            except Exception as e:
                clean_list.append(engine_id)
        for i in clean_list:
            self.remove_liveengine(i)

    def get_pid_of_liveengine(self, engine_id: str) -> int:
        pid = self.get_redis().hget(self._live_engine_pid_name, engine_id)
        return int(pid) if pid else None


GDATA = GinkgoData()
