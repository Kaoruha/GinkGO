import time
import zlib
import pickle
import types
import datetime
import os
import pandas as pd
import numpy as np
import multiprocessing
import threading
from sqlalchemy import DDL
from rich.console import Console
from ginkgo.data.models import (
    MAnalyzer,
    MOrder,
    MBar,
    MStockInfo,
    MTradeDay,
    MAdjustfactor,
    MClickBase,
    MMysqlBase,
    MTick,
    MFile,
    MBacktest,
)
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize, str2bool
from ginkgo.enums import (
    MARKET_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
    TICKDIRECTION_TYPES,
    FILE_TYPES,
)
from ginkgo.data.sources import GinkgoBaoStock, GinkgoTushare, GinkgoTDX
from ginkgo.data.drivers import GinkgoClickhouse, GinkgoMysql, GinkgoRedis


console = Console()


class GinkgoData(object):
    """
    Data Module
    """

    def __init__(self):
        self._click_models = []
        self._mysql_models = []
        self.get_models()
        self.batch_size = 500
        self.cpu_ratio = 0.5
        self.redis_expiration_time = 60 * 60 * 6
        try:
            self.cpu_ratio = GCONF.CPURATIO
        except Exception as e:
            self.cpu_ratio = 0.8
            print(e)
        self.tick_models = {}
        self.cache_daybar_count = 0
        self.cache_daybar_max = 4
        self.redis_queue = multiprocessing.Manager().Queue(20)
        self.redis_lock = multiprocessing.Manager().Lock()

    def get_daybar_redis_cache_name(self, code: str) -> str:
        pass

    def get_stockinfo_redis_cache_name(self, code: str) -> str:
        pass

    def start_listen_redis_handler(self) -> None:
        acquired = self.redis_lock.acquire(timeout=1)
        if not acquired:
            GLOG.WARN("Redis listener already started.")
            return
        # Build a Multiprocessing Pool to listen to a queue.
        count = 4
        p = multiprocessing.Pool(count)
        for i in range(count):
            res = p.apply_async(
                self.redis_handler,
                args=(self.redis_queue,),
                callback=self.redis_handler_done(),
            )
        p.close()

    def redis_handler_done(self):
        pass

    def redis_handler(self, q) -> None:
        print(
            f"ProcessName: {multiprocessing.current_process().name}  PID: {os.getpid()}"
        )

        while True:
            print(
                f"Current redis: {self.redis_queue.qsize()}   {self.redis_queue}  {self}"
            )
            if q.empty():
                # print("empty")
                time.sleep(2)
                continue
            try:
                item = q.get()
                data_type = item[0]
                code = item[1]
                print(item)
                print(f"dealing with {data_type} {data}")
                # TODO decode the data , and do cache
            except Exception as e:
                print(e)

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

    def get_mysql(self):
        return GinkgoMysql(
            user=GCONF.MYSQLUSER,
            pwd=GCONF.MYSQLPWD,
            host=GCONF.MYSQLHOST,
            port=GCONF.MYSQLPORT,
            db=GCONF.MYSQLDB,
        )

    def get_click(self):
        return GinkgoClickhouse(
            user=GCONF.CLICKUSER,
            pwd=GCONF.CLICKPWD,
            host=GCONF.CLICKHOST,
            port=GCONF.CLICKPORT,
            db=GCONF.CLICKDB,
        )

    def get_redis(self):
        return GinkgoRedis(GCONF.REDISHOST, GCONF.REDISPORT).redis

    def add(self, value) -> None:
        driver = self.get_driver(value)
        driver.session.add(value)
        driver.session.commit()

    def add_all(self, values) -> None:
        """
        Add multi data into session
        """
        # TODO support different database engine.
        # Now is for clickhouse.
        click_list = []
        mysql_list = []
        click_driver = self.get_click()
        mysql_driver = self.get_mysql()
        for i in values:
            if isinstance(i, MClickBase):
                click_list.append(i)
            elif isinstance(i, MMysqlBase):
                mysql_list.append(i)
        if len(click_list) > 0:
            click_driver.session.add_all(click_list)
            click_driver.session.commit()
        if len(mysql_list) > 0:
            mysql_driver.session.add_all(mysql_list)
            mysql_driver.session.commit()

    def get_tick_model(self, code: str) -> type:
        """
        Tick data can not be stored in one table.
        Do database partitioning first.
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
        self._click_models = []
        self._mysql_models = []
        for i in MClickBase.__subclasses__():
            if i.__abstract__ == True:
                continue
            if i not in self._click_models:
                self._click_models.append(i)

        for i in MMysqlBase.__subclasses__():
            if i.__abstract__ == True:
                continue
            if i not in self._mysql_models:
                self._mysql_models.append(i)

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
        GLOG.INFO(f"{type(self)} create all tables.")

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
        db = engine if engine else self.get_driver(model)
        if db is None:
            return 0
        return db.get_table_size(model)

    def get_order(self, order_id: str, engine=None) -> MOrder:
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

    def get_order_df(self, order_id: str, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)

        if df.shape[0] > 1:
            GLOG.ERROR(
                f"Order_id :{order_id} has {df.shape[0]} records, please check the code and clean the database."
            )
        elif df.shape[0] == 0:
            return pd.DataFrame()
        print("Get Order DF")
        print(df)

        df = df.iloc[0, :]
        df.code = df.code.strip(b"\x00".decode())
        return df

    def get_order_df_by_backtest(self, backtest_id: str, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MOrder)
        r = (
            db.session.query(MOrder)
            .filter(MOrder.backtest_id == backtest_id)
            .filter(MOrder.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)

        if df.shape[0] == 0:
            GLOG.DEBUG("Try get order df by backtest, but no order found.")
            return pd.DataFrame()
        GLOG.DEBUG(f"Get Order DF with backtest: {backtest_id}")
        print(df)

        df = df.iloc[0, :]
        df.code = df.code.strip(b"\x00".decode())
        return df

    def calculate_adjustfactor(self, code, df) -> pd.DataFrame:
        GLOG.DEBUG(f"Cal {code} Adjustfactor.")
        if df.shape[0] == 0:
            return pd.DataFrame()
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        date_start = df.loc[0, ["timestamp"]].values[0]
        date_end = df.loc[df.shape[0] - 1, ["timestamp"]].values[0]
        ad = self.get_adjustfactor_df_cached(
            code, date_start=date_start, date_end=date_end
        )
        if ad.shape[0] == 0:
            return df
        ad = ad.sort_values(by="timestamp", ascending=True)
        ad.reset_index(drop=True, inplace=True)
        date = datetime_normalize(date_start)
        new_ad = pd.DataFrame(columns=["timestamp", "adjustfactor"])
        end = datetime_normalize(date_end)
        compare = 0
        for i, r in df.iterrows():
            date = r["timestamp"]
            if (
                date >= ad.loc[compare, ["timestamp"]].values[0]
                and compare < ad.shape[0] - 1
            ):
                compare = compare + 1
            factor = ad.loc[compare, ["adjustfactor"]].values[0]
            new_ad.loc[i] = {"timestamp": date, "adjustfactor": factor}
        df["open"] = df["open"] / new_ad["adjustfactor"]
        df["high"] = df["high"] / new_ad["adjustfactor"]
        df["low"] = df["low"] / new_ad["adjustfactor"]
        df["close"] = df["close"] / new_ad["adjustfactor"]
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

    def get_stock_info_df(self, code: str = None, engine=None) -> pd.DataFrame:
        GLOG.DEBUG(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        if code == "" or code is None:
            r = db.session.query(MStockInfo).filter(MStockInfo.isdel == False)
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="code", ascending=True)
        else:
            r = (
                db.session.query(MStockInfo)
                .filter(MStockInfo.code == code)
                .filter(MStockInfo.isdel == False)
            )
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="code", ascending=True)
        return df

    def get_stock_info_df_cached(self, code: str = None, engine=None) -> pd.DataFrame:
        GLOG.DEBUG(f"Try get Stockinfo df cached about {code}.")
        cache_name = "stockinfo"
        temp_redis = self.get_redis()
        db = engine if engine else self.get_driver(MStockInfo)
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name)
            df = pickle.loads(cache)
        else:
            r = db.session.query(MStockInfo).filter(MStockInfo.isdel == False)
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="code", ascending=True)
            if df.shape[0] > 0:
                temp_redis.setex(
                    cache_name, self.redis_expiration_time, pickle.dumps(df)
                )
        if df.shape[0] > 0:
            if code == "" or code is None:
                return df
            else:
                return df[df.code == code]
        else:
            return pd.DataFrame()

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
        return df

    def get_trade_calendar_df_cached(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> pd.DataFrame:
        GLOG.DEBUG(
            f"Try get Trade Calendar df cached. {market} from {date_start} to {date_end}."
        )
        cache_name = f"trade_calendar%{market}"
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        temp_redis = self.get_redis()
        db = engine if engine else self.get_driver(MTradeDay)
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name)
            df = pickle.loads(cache)
        else:
            r = (
                db.session.query(MTradeDay)
                .filter(MTradeDay.market == market)
                .filter(MTradeDay.isdel == False)
            )
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="timestamp", ascending=True)
            df.reset_index(drop=True, inplace=True)
            if df.shape[0] > 0:
                temp_redis.setex(
                    cache_name, self.redis_expiration_time, pickle.dumps(df)
                )
        if df.shape[0] > 0:
            date_range = pd.date_range(start=date_start, end=date_end)
            df_filtered = df[df.timestamp.isin(date_range)]
            df_filtered.reset_index(drop=True, inplace=True)
            return df_filtered

        else:
            return pd.DataFrame()

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
            .filter(MBar.timestamp >= date_start)
            .filter(MBar.timestamp <= date_end)
            .filter(MBar.isdel == False)
            .all()
        )

        return r

    def get_daybar_df(
        self,
        code: str,
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
        r = (
            db.session.query(MBar)
            .filter(MBar.code == code)
            .filter(MBar.timestamp >= date_start)
            .filter(MBar.timestamp <= date_end)
            .filter(MBar.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        if df.shape[0] == 0:
            return pd.DataFrame()
        else:
            return self.calculate_adjustfactor(code, df)
        # TODO Start a thread store the data in redis cache

    def get_daybar_df_cached(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        adjust: int = 1,  # 0 no adjust, 1 back adjust 2 forward adjust
        engine=None,
    ) -> pd.DataFrame:
        """
        Get the daybar with back adjust.
        Will try get from cache first.
        """
        GLOG.DEBUG(
            f"Try get DAYBAR df cached about {code} from {date_start} to {date_end}."
        )
        cache_name = f"day%{code}"
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        temp_redis = self.get_redis()
        db = engine if engine else self.get_driver(MBar)
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name)
            df = pickle.loads(cache)
            if df.shape[0] > 0:
                date_range = pd.date_range(start=date_start, end=date_end)
                df_filtered = df[df.timestamp.isin(date_range)]
                df_filtered.reset_index(drop=True, inplace=True)
                return df_filtered
            else:
                return pd.DataFrame()
        else:
            try:
                self.redis_queue.put(["daybar", code], block=False)
                print(
                    f"After redis put , qsize: {self.redis_queue.qsize()}  {self.redis_queue}  {self}"
                )
            except Exception as e:
                pass
            return self.get_daybar_df(code, date_start, date_end)

    def cache_daybar_df(self, code: str, engine=None):
        self.is_daybar_caching = True
        try:
            cache_name = f"day%{code}"
            temp_redis = self.get_redis()
            if temp_redis.exists(cache_name):
                self.cache_daybar_count -= 1
                return
            db = engine if engine else self.get_driver(MBar)
            r = (
                db.session.query(MBar)
                .filter(MBar.code == code)
                .filter(MBar.isdel == False)
            )
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="timestamp", ascending=True)
            df.reset_index(drop=True, inplace=True)
            df = self.calculate_adjustfactor(code, df)
            if df.shape[0] > 0:
                temp_redis.setex(
                    cache_name, self.redis_expiration_time, pickle.dumps(df)
                )
            self.cache_daybar_count -= 1
        except Exception as e:
            print(e)
            self.cache_daybar_count -= 1

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
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def get_adjustfactor_df_cached(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.DEBUG(
            f"Try get ADJUSTFACTOR df cached about {code} from {date_start} to {date_end}."
        )
        cache_name = f"adf%{code}"
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        temp_redis = self.get_redis()
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name)
            df = pickle.loads(cache)
        else:
            db = engine if engine else self.get_driver(MAdjustfactor)
            r = (
                db.session.query(MAdjustfactor)
                .filter(MAdjustfactor.code == code)
                .filter(MAdjustfactor.isdel == False)
            )
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="timestamp", ascending=True)
            df.reset_index(drop=True, inplace=True)
            if df.shape[0] > 0:
                temp_redis.setex(
                    cache_name, self.redis_expiration_time, pickle.dumps(df)
                )
        if df.shape[0] > 0:
            date_range = pd.date_range(start=date_start, end=date_end)
            df_filtered = df[df.timestamp.isin(date_range)]
            df_filtered.reset_index(drop=True, inplace=True)
            return df_filtered
        else:
            return pd.DataFrame()

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
        if r:
            return True
        else:
            return False

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

    def get_tick_df(
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
        # TODO adjust
        return df

    def get_tick_df_cached(
        self, code: str, date_start: any, date_end: any, engine=None
    ) -> pd.DataFrame:
        GLOG.INFO(
            f"Try get TICK df cached about {code} from {date_start} to {date_end}."
        )
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return pd.DataFrame()
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        # TODO Optimize the read, read the entire of tick talbe is too slow.
        cache_name = f"tick%{code}"
        temp_redis = self.get_redis()
        db = engine if engine else self.get_driver(model)
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name)
            df = pickle.loads(cache)
        else:
            r = (
                db.session.query(model).filter(model.code == code)
                # .filter(model.timestamp >= date_start)
                # .filter(model.timestamp <= date_end)
                .filter(model.isdel == False)
            )
            df = pd.read_sql(r.statement, db.engine)
            df = df.sort_values(by="timestamp", ascending=True)
            df.reset_index(drop=True, inplace=True)
            df = self.calculate_adjustfactor(code, df)
            if df.shape[0] > 0:
                temp_redis.setex(
                    cache_name, self.redis_expiration_time, pickle.dumps(df)
                )
        if df.shape[0] > 0:
            # TODO cal adjustfactor
            date_range = pd.date_range(start=date_start, end=date_end)
            df_filtered = df[df.timestamp.isin(date_range)]
            df_filtered.reset_index(drop=True, inplace=True)
            return df_filtered
        else:
            return pd.DataFrame

    def del_tick(self, code: str, date: any) -> None:
        # TODO
        pass

    def update_tick(self, code: str, fast_mode: bool = False, engine=None) -> None:
        cached_name = f"{code}_tick_updated"
        temp_redis = self.get_redis()
        if temp_redis.exists(cached_name):
            updated = temp_redis.get(cached_name)
            GLOG.INFO(
                f"Tick {code} Updated at {updated.decode('utf-8')}. No need to update."
            )
            return
        GLOG.INFO(f"Updating TICK {code}.")
        list_date = self.get_stock_info_df_cached(code).list_date.values[0]
        list_date = pd.Timestamp(list_date).to_pydatetime()
        # CreateTable
        model = self.get_tick_model(code)
        self.create_table(model)
        db = engine if engine else self.get_driver(model)
        # Try get
        t0 = datetime.datetime.now()
        insert_count = 0
        tdx = GinkgoTDX()
        nodata_count = 0
        nodata_max = 360
        date = datetime.datetime.now()
        while True:
            # Break
            if date < list_date:
                break
            if nodata_count > nodata_max:
                break
            # Query database
            date_start = date.strftime("%Y%m%d")
            date_end = (date + datetime.timedelta(days=1)).strftime("%Y%m%d")
            GLOG.DEBUG(f"Trying to update {code} Tick on {date}")
            if self.is_tick_indb(code, date_start):
                GLOG.WARN(f"{code} Tick on {date} is in database. Go next")
                date = date + datetime.timedelta(days=-1)
                nodata_count = nodata_count + 1 if fast_mode else 0
                continue
            # Check is market open today
            open_day = self.get_trade_calendar_df_cached(
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
                GLOG.WARN(f"{code} No data on {date} from remote.")
                date = date + datetime.timedelta(days=-1)
                nodata_count = nodata_count + 1 if fast_mode else 0
                continue
            GLOG.DEBUG(f"Got {rs.shape} records.")

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
            GLOG.WARN(f"Insert {code} Tick {len(l)}.")
            nodata_count = 0
            insert_count += len(l)
            # ReCheck
            if self.is_tick_indb(code, date_start):
                GLOG.DEBUG(f"{code} {date_start} Insert Recheck Successful.")
            else:
                GLOG.ERROR(
                    f"{code} {date_start} Insert Failed. Still no data in database."
                )
            date = date + datetime.timedelta(days=-1)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Updating Tick {code} complete. Cost: {t1-t0}")
        if insert_count > 0:
            self.update_redis_tick(code)
        temp_redis.setex(
            cached_name,
            60 * 60 * 24,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def update_all_cn_tick_aysnc(self, fast_mode: bool = False) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df_cached()
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
        cached_name = "cn_stockinfo_updated"
        temp_redis = self.get_redis()
        if temp_redis.exists(cached_name):
            updated = temp_redis.get(cached_name)
            GLOG.INFO(
                f"StockInfo Updated at {updated.decode('utf-8')}. No need to update."
            )
            return
        db = engine if engine else self.get_driver(MStockInfo)
        size = db.get_table_size(MStockInfo)
        GLOG.INFO(f"Current Stock Info Size: {size}")
        t0 = datetime.datetime.now()
        update_count = 0
        insert_count = 0
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_info()
        l = []
        for i, r in df.iterrows():
            msg = f"UpdatingStockInfo {i}/{df.shape[0]}"
            print(msg, end="\r")
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
        GLOG.WARN(
            f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )
        size = db.get_table_size(MStockInfo)
        GLOG.INFO(f"After Update Stock Info Size: {size}")
        self.update_redis_stockinfo()
        temp_redis.setex(
            cached_name,
            60 * 60 * 4,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def update_trade_calendar(self) -> None:
        """
        Update all Makets' Calendar
        """
        GLOG.INFO("Updating Trade Calendar")
        self.update_cn_trade_calendar()

    def update_cn_trade_calendar(self) -> None:
        market = MARKET_TYPES.CHINA
        cached_name = f"trade_calendar%{market}updateat"
        temp_redis = self.get_redis()
        if temp_redis.exists(cached_name):
            updated = temp_redis.get(cached_name)
            GLOG.INFO(
                f"Calendar Updated at {updated.decode('utf-8')}. No need to update."
            )
            return
        GLOG.INFO("Updating CN Calendar.")
        db = self.get_driver(MTradeDay)
        size = db.get_table_size(MTradeDay)
        GLOG.DEBUG(f"Current Trade Calendar Size: {size}")
        t0 = datetime.datetime.now()
        update_count = 0
        insert_count = 0
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_trade_day()
        if df is None:
            GLOG.ERROR("Tushare get no data. Update CN TradeCalendar Failed.")
            return
        l = []
        for i, r in df.iterrows():
            msg = f"Updating TradeCalendar {i}/{df.shape[0]}"
            print(msg, end="\r")
            item = MTradeDay()
            date = datetime_normalize(r["cal_date"])
            market = MARKET_TYPES.CHINA
            is_open = str2bool(r["is_open"])
            item.set(market, is_open, date)
            item.set_source(SOURCE_TYPES.TUSHARE)
            q = self.get_trade_calendar(market, date, date, db)
            # Check DB, if exist update
            if len(q) >= 1:
                if len(q) >= 2:
                    GLOG.ERROR(f"Trade Calendar have {len(q)} {market} date on {date}")
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
                    GLOG.DEBUG(f"Update {item2.timestamp} {item2.market} TradeCalendar")

            if len(q) == 0:
                # Not Exist in db
                l.append(item)
                if len(l) >= self.batch_size:
                    self.add_all(l)
                    insert_count += len(l)
                    GLOG.DEBUG(f"Insert {len(l)} Trade Calendar.")
                    l = []
        self.add_all(l)
        GLOG.INFO(f"Insert {len(l)} Trade Calendar.")
        insert_count += len(l)
        t1 = datetime.datetime.now()
        GLOG.WARN(
            f"TradeCalendar Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )
        size = db.get_table_size(MTradeDay)
        GLOG.WARN(f"After Update Trade Calendar Size: {size}")
        self.update_redis_tradecalender(MARKET_TYPES.CHINA)
        temp_redis.setex(
            cached_name,
            60 * 60 * 24,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def update_cn_daybar(self, code: str) -> None:
        cached_name = f"{code}_daybar_updated"
        temp_redis = self.get_redis()
        if temp_redis.exists(cached_name):
            updated = temp_redis.get(cached_name)
            GLOG.INFO(
                f"Daybar {code} Updated at {updated.decode('utf-8')}. No need to update."
            )
            return
        GLOG.INFO(f"Updating CN DAYBAR about {code}.")
        # Get the stock info of code
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df_cached(code)
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

        missing_period = [
            [None, None],
        ]

        trade_calendar = self.get_trade_calendar_df_cached(
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
        old_df = self.get_daybar_df(code)
        old_timestamp = old_df.timestamp.values if old_df.shape[0] > 0 else []
        for i, r in trade_calendar.iterrows():
            trade_calendar.loc[i, "in_db"] = r["timestamp"] in old_timestamp
        missing_period = [
            [None, None],
        ]
        last_missing = None
        for i, r in trade_calendar.iterrows():
            current = str(r["timestamp"])
            current = datetime_normalize(current)
            print(f"Daybar Calendar Check {current}  {code}", end="\r")
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

        # fetch the data and insert to db
        tu = GinkgoTushare()
        l = []
        insert_count = 0
        update_count = 0
        for period in missing_period:
            if period[0] is None:
                break
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
        # Update Redis
        if insert_count > 0:
            self.update_redis_daybar(code)

        temp_redis.setex(
            cached_name,
            60 * 60 * 24,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def update_redis_stockinfo(self) -> None:
        # TODO Sync the redis cache name laod and set
        cache_name = "stockinfo"
        temp_redis = self.get_redis()
        if not temp_redis.exists(cache_name):
            return
        db = self.get_click()
        r = db.session.query(MStockInfo).filter(MStockInfo.isdel == False)
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        if df.shape[0] > 0:
            temp_redis.setex(cache_name, self.redis_expiration_time, pickle.dumps(df))
            GLOG.INFO(f"Update Redis STOCKINFO.")

    def update_redis_adjustfactor(self, code: str) -> None:
        # TODO Sync the redis cache name laod and set
        cache_name = f"adf%{code}"
        temp_redis = self.get_redis()
        if not temp_redis.exists(cache_name):
            return
        r = (
            MYSQLDRIVER.session.query(MAdjustfactor)
            .filter(MAdjustfactor.code == code)
            .filter(MAdjustfactor.isdel == False)
        )
        df = pd.read_sql(r.statement, MYSQLDRIVER.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        if df.shape[0] > 0:
            temp_redis.setex(cache_name, self.redis_expiration_time, pickle.dumps(df))
            GLOG.INFO(f"Update Redis ADJUSTFACTOR {code}")

    def update_redis_tradecalender(self, market: MARKET_TYPES) -> None:
        # TODO Sync the redis cache name laod and set
        cache_name = f"trade_calendar%{market}"
        temp_redis = self.get_redis()
        db = self.get_click()
        if not temp_redis.exists(cache_name):
            return
        r = (
            db.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        if df.shape[0] > 0:
            temp_redis.setex(cache_name, self.redis_expiration_time, pickle.dumps(df))
            GLOG.INFO(f"Update Redis TRADECALENDER {market}")

    def update_redis_daybar(self, code: str) -> None:
        # TODO Sync the redis cache name laod and set
        cache_name = f"day%{code}"
        temp_redis = self.get_redis()
        if not temp_redis.exists(cache_name):
            return
        db = self.get_click()
        r = db.session.query(MBar).filter(MBar.code == code).filter(MBar.isdel == False)
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        df = self.calculate_adjustfactor(code, df)
        if df.shape[0] > 0:
            temp_redis.setex(cache_name, self.redis_expiration_time, pickle.dumps(df))
            GLOG.INFO(f"Update Redis DAYBAR {code}")

    def update_redis_tick(self, code: str) -> None:
        # TODO Sync the redis cache name laod and set
        cache_name = f"tick%{code}"
        temp_redis = self.get_redis()
        if not temp_redis.exists(cache_name):
            return
        db = self.get_click()
        r = (
            db.session.query(model)
            .filter(model.code == code)
            .filter(model.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        df = self.calculate_adjustfactor(code, df)
        if df.shape[0] > 0:
            temp_redis.setex(cache_name, self.redis_expiration_time, pickle.dumps(df))
            GLOG.INFO(f"Update Redis TICK {code}")

    def update_all_cn_daybar(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df_cached()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_cn_daybar(code)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update ALL CN Daybar cost {t1-t0}")

    def update_all_cn_daybar_aysnc(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df_cached()
        if info.shape[0] == 0:
            GLOG.WARN(f"Stock Info is empty.")
            console.print(
                f":zipper-mouth_face: Please run [steel_blue1]ginkgo data update --stockinfo[/steel_blue1] first."
            )

        l = []
        cpu_count = multiprocessing.cpu_count()
        cpu_count = int(cpu_count * self.cpu_ratio)
        for i, r in info.iterrows():
            code = r["code"]
            l.append(code)

        p = multiprocessing.Pool(cpu_count)

        for code in l:
            res = p.apply_async(self.update_cn_daybar, args=(code,))

        p.close()
        p.join()
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update All CN Daybar Done. Cost: {t1-t0}")

    def update_cn_adjustfactor(self, code: str) -> None:
        cached_name = f"{code}_adjustfactor_updated"
        temp_redis = self.get_redis()
        if temp_redis.exists(cached_name):
            updated = temp_redis.get(cached_name)
            GLOG.INFO(
                f"Adjustfactor {code} Updated at {updated.decode('utf-8')}. No need to update."
            )
            return
        t0 = datetime.datetime.now()
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_adjustfactor(code)
        insert_count = 0
        update_count = 0
        driver = self.get_mysql()
        l = []
        for i, r in df.iterrows():
            code = r["ts_code"]
            date = datetime_normalize(r["trade_date"])
            factor = r["adj_factor"]
            GLOG.DEBUG(f"AdjustFactor Check {date}  {code}")

            # Check ad if exist in database
            # Data in database
            q = self.get_adjustfactor(code, date, date)
            # If exist, update
            if len(q) >= 1:
                # TODO Database seem not have duplicated data. But get_adjustfactor function return multi.
                if len(q) >= 2:
                    GLOG.ERROR(
                        f"Should not have {len(q)} {code} AdjustFactor on {date}"
                    )
                for item in q:
                    if (
                        item.code == code
                        and item.timestamp == date
                        and float(item.adjustfactor) == factor
                    ):
                        GLOG.DEBUG(f"Ignore Adjustfactor {code} {date}")
                        continue
                    item.adjustfactor = factor
                    item.update = datetime.datetime.now()
                    update_count += 1
                    driver.session.commit()
                    GLOG.DEBUG(f"Update {code} {date} AdjustFactor")

            # If not exist, new insert
            elif len(q) == 0:
                # Insert
                adjs = self.get_adjustfactor(code, GCONF.DEFAULTSTART, date)
                if len(adjs) == 0 or adjs is None:
                    o = MAdjustfactor()
                    o.set_source(SOURCE_TYPES.TUSHARE)
                    o.set(code, 1.0, 1.0, factor, date)
                    l.append(o)
                elif len(adjs) > 0:
                    latest = adjs[-1]
                    if float(latest.adjustfactor) == factor:
                        latest.update_time(date)
                        update_count += 1
                        driver.session.commit()
                    else:
                        o = MAdjustfactor()
                        o.set_source(SOURCE_TYPES.TUSHARE)
                        o.set(code, 1.0, 1.0, factor, date)
                        l.append(o)
            if len(l) > self.batch_size:
                driver.session.add_all(l)
                driver.session.commit()
                insert_count += len(l)
                GLOG.DEBUG(f"Insert {len(l)} {code} AdjustFactor.")
                l = []
        if len(l) > 0:
            driver.session.add_all(l)
            driver.session.commit()
            insert_count += len(l)
            GLOG.DEBUG(f"Insert {len(l)} {code} AdjustFactor.")
        t1 = datetime.datetime.now()
        GLOG.WARN(
            f"AdjustFactor {code} Update: {update_count} Insert: {insert_count} Cost: {t1-t0}"
        )
        temp_redis.setex(
            cached_name,
            60 * 60 * 24,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def update_all_cn_adjustfactor(self):
        GLOG.DEBUG(f"Begin to update all CN AdjustFactor")
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df_cached()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_cn_adjustfactor(code)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update ALL CN AdjustFactor cost {t1-t0}")

    def update_all_cn_adjustfactor_aysnc(self):
        GLOG.INFO(f"Begin to update all cn adjust factors")
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df_cached()
        l = []
        cpu_count = multiprocessing.cpu_count()
        cpu_count = int(cpu_count * self.cpu_ratio)
        for i, r in info.iterrows():
            code = r["code"]
            l.append(code)

        p = multiprocessing.Pool(cpu_count)

        for code in l:
            res = p.apply_async(self.update_cn_adjustfactor, args=(code,))

        p.close()
        p.join()
        t1 = datetime.datetime.now()
        size = self.get_mysql().get_table_size(MAdjustfactor)
        GLOG.WARN(f"Update ALL CN AdjustFactor cost {t1-t0}")
        GLOG.WARN(f"After Update Adjustfactor Size: {size}")

    def get_file(self, id: str, engine=None) -> MFile:
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.uuid == id)
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

    def get_file_list_df(self, type: FILE_TYPES = None, engine=None):
        db = engine if engine else self.get_driver(MFile)
        if type is None:
            r = db.session.query(MFile).filter(MFile.isdel == False)
        else:
            r = (
                db.session.query(MFile)
                .filter(MFile.type == type)
                .filter(MFile.isdel == False)
            )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="update", ascending=False)
        # df.name = df.name.strip(b"\x00".decode())
        return df

    def get_file_list_df_fuzzy(self, filter: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.file_name.like(f"%{filter}%"))
            .filter(MFile.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="update", ascending=False)
        # df.name = df.name.strip(b"\x00".decode())
        return df

    def update_file(
        self, id: str, type: FILE_TYPES, name: str, content: bytes, engine=None
    ):
        db = engine if engine else self.get_driver(MFile)
        r = (
            db.session.query(MFile)
            .filter(MFile.uuid == id)
            .filter(MFile.isdel == False)
            .first()
        )
        if r is not None:
            r.type = type
            r.name = name
            r.content = content
            r.update = datetime.datetime.now()
            db.session.commit()

    def copy_file(self, type: FILE_TYPES, name: str, source: str) -> MFile:
        file = self.get_file(source)
        if file is None:
            GLOG.DEBUG(f"File {source} not exist. Copy failed.")
            return
        item = MFile()
        item.type = type
        item.file_name = name
        item.content = file.content
        self.add(item)
        return item

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
        if r is not None:
            r.update = datetime.datetime.now()
            r.isdel = True
            db.session.commit()
            return True
        else:
            return False

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
                        print(f"Add {file_name}")

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
                print("Add DefaultStrategy.yml")
        for i in file_map:
            walk_through(i)

    def add_backtest(self, backtest_id: str, content: bytes) -> None:
        item = MBacktest()
        item.set(backtest_id, datetime.datetime.now(), content)
        self.add(item)

    def remove_backtest(self, backtest_id: str) -> bool:
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is None:
            return False
        r.update = datetime.datetime.now()
        r.isdel = True
        db.session.commit()
        return True

    def finish_backtest(self, backtest_id: str) -> None:
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is None:
            GLOG.DEBUG(f"Can not find backtest {backtest_id} in database.")
            return
        r.finish(datetime.datetime.now())
        db.session.commit()
        GLOG.DEBUG(f"Backtest {backtest_id} finished.")

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
        return count

    def remove_analyzers(self, backtest_id: str) -> None:
        db = self.get_driver(MAnalyzer)

        r = (
            db.session.query(MAnalyzer)
            .filter(MAnalyzer.backtest_id == backtest_id)
            .filter(MAnalyzer.isdel == False)
            .all()
        )
        count = len(r)
        if count > 0:
            db.session.query(MAnalyzer).filter(
                MAnalyzer.backtest_id == backtest_id
            ).filter(MAnalyzer.isdel == False).delete()
        return count

    def update_backtest_profit(self, backtest_id: str, profit: float) -> None:
        if backtest_id == "":
            GLOG.DEBUG("Can not update the backtest record with empty backtest_id.")
            return
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is not None:
            r.profit = profit
            db.session.commit()

    def finish_backtest(self, backtest_id: str) -> None:
        if backtest_id == "":
            GLOG.DEBUG("Can not finish the backtest record with empty backtest_id.")
            return
        db = self.get_driver(MBacktest)
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .first()
        )
        if r is not None:
            r.finish(datetime.datetime.now())
            db.session.commit()

    def get_backtest_record(self, backtest_id: str) -> None:
        db = self.get_driver(MBacktest)
        if backtest_id == "":
            GLOG.DEBUG("Can not get backtest record with empty backtest_id.")
            return
        r = (
            db.session.query(MBacktest)
            .filter(MBacktest.backtest_id == backtest_id)
            .filter(MBacktest.isdel == False)
            .order_by(MBacktest.start_at.desc())
            .first()
        )
        return r

    def get_backtest_list_df(self, backtest_id: str = "") -> None:
        db = self.get_driver(MBacktest)
        if backtest_id != "":
            r = (
                db.session.query(MBacktest)
                .filter(MBacktest.backtest_id == backtest_id)
                .filter(MBacktest.isdel == False)
                .order_by(MBacktest.start_at.desc())
            )
        else:
            r = db.session.query(MBacktest).filter(MBacktest.isdel == False)
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

    def get_analyzer_df_by_backtest(
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

    def remove_from_redis(self, key: str):
        temp_redis = self.get_redis()
        if temp_redis.exists(key):
            temp_redis.delete(key)
            GLOG.WARN(f"Remove {key} from redis.")
        else:
            GLOG.WARN(f"{key} not exist in redis.")


GDATA = GinkgoData()
