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
from sqlalchemy import or_, and_

from ginkgo.data.models import (
    MAnalyzerRecord,
    MSignal,
    MOrder,
    MOrderRecord,
    MPositionRecord,
    MBar,
    MStockInfo,
    MTradeDay,
    MTransferRecord,
    MAdjustfactor,
    MTick,
    MFile,
    MPortfolio,
)

from ginkgo.libs.ginkgo_logger import GLOG, GinkgoLogger
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
from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
from ginkgo.data.drivers import create_mysql_connection, create_click_connection, kafka_topic_llen
from ginkgo.libs.ginkgo_ps import find_process_by_keyword
from ginkgo.backtest.position import Position
from ginkgo.backtest.order import Order
from ginkgo.notifier.notifier_beep import beep

data_logger = GinkgoLogger("ginkgo_data_", "ginkgo_data.log")


console = Console()


class GinkgoData(object):
    """
    Data Module
    """

    def __init__(self):
        self.dataworker_pool_name = "ginkgo_dataworker"  # Conf
        self._click_models = []
        self._mysql_models = []
        # self.get_models()
        self.batch_size = 500
        self.cpu_ratio = 0.5
        self.redis_expiration_time = 60 * 60 * 6
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
        self.get_kafka_producer().send("ginkgo_main_control", {"type": "run_live", "id": str(id)})

    def send_signal_stop_live(self, id: str) -> None:
        self.get_kafka_producer().send("ginkgo_main_control", {"type": "stop_live", "id": str(id)})

    def send_signal_run_backtest(self, id: str) -> None:
        self.get_kafka_producer().send("ginkgo_main_control", {"type": "backtest", "id": str(id)})

    def send_signal_stop_dataworker(self):
        self.get_kafka_producer().send("ginkgo_data_update", {"type": "kill", "code": "blabla"})

    def send_signal_test_dataworker(self):
        self.get_kafka_producer().send("ginkgo_data_update", {"type": "other", "code": "blabla1"})

    def send_signal_update_adjust(self, code: str = "", fast: bool = True) -> None:
        if code == "":
            self.get_kafka_producer().send("ginkgo_data_update", {"type": "adjust", "code": "all", "fast": fast})
        else:
            self.get_kafka_producer().send("ginkgo_data_update", {"type": "adjust", "code": code, "fast": fast})
        GLOG.INFO(f"Send Signal to update {code} adjustfacotr.")

    def send_signal_update_calender(self) -> None:
        self.get_kafka_producer().send("ginkgo_data_update", {"type": "calender", "code": "None", "fast": True})

    def send_signal_update_stockinfo(self) -> None:
        self.get_kafka_producer().send("ginkgo_data_update", {"type": "stockinfo", "code": "None", "fast": True})

    def send_signal_update_bar(self, code: str, fast_mode: bool = True) -> None:
        self.get_kafka_producer().send("ginkgo_data_update", {"type": "bar", "code": code, "fast": fast_mode})

    def send_signal_update_all_bar(self, fast_mode: bool = True) -> None:
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.send_signal_update_bar(code, fast_mode)

    def send_signal_update_tick(self, code: str, fast_mode: bool = True) -> None:
        self.get_kafka_producer().send("ginkgo_data_update", {"type": "tick", "code": code, "fast": fast_mode})

    def send_signal_update_all_tick(self, fast_mode: bool = True) -> None:
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.send_signal_update_tick(code, fast_mode)

    def send_signal_to_liveengine(self, engine_id: str, command: str) -> None:
        self.get_kafka_producer().send(
            self._live_engine_control_name,
            {"engine_id": engine_id, "command": command, "ttr": 0},
        )

    # Operation about Database >>

    # def get_models(self) -> None:
    #     """
    #     Read all py files under /data/models
    #     Args:
    #         None
    #     Returns:
    #         All Models of sqlalchemy
    #     """
    #     GLOG.INFO(f"Try to read all models.")
    #     click_count = 0
    #     mysql_count = 0
    #     self._click_models = []
    #     self._mysql_models = []
    #     for i in MClickBase.__subclasses__():
    #         if i.__abstract__ == True:
    #             continue
    #         if i not in self._click_models:
    #             self._click_models.append(i)
    #             click_count += 1

    #     for i in MMysqlBase.__subclasses__():
    #         if i.__abstract__ == True:
    #             continue
    #         if i not in self._mysql_models:
    #             self._mysql_models.append(i)
    #             mysql_count += 1
    #     GLOG.INFO(f"Read {click_count} clickhouse models.")
    #     GLOG.INFO(f"Read {mysql_count} mysql models.")

    # << Operation about Database

    # CRUD of ORDER >>
    def get_order_by_id(self, order_id: str, engine=None) -> Order:
        GLOG.INFO(f"Try to get Order about {order_id}.")
        data = self.get_order_df_by_id(order_id).iloc[0]
        o = Order()
        o.set(data)
        return o

    def update_order(self, order: Order, engine=None) -> None:
        db = engine if engine else self.get_driver(MOrder)
        order_id = order.uuid
        r = db.session.query(MOrder).filter(MOrder.uuid == order_id).filter(MOrder.isdel == False).first()
        if r is None:
            db.session.close()
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
        GLOG.INFO(f"Try to get Signal about {portfolio_id}.")
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
        GLOG.INFO(f"Try to get Signal about {portfolio_id}.")
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
        GLOG.INFO(f"Try to get OrderRecord about {backtest_id} {code}.")
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
        GLOG.INFO(f"Try to get Order about {backtest_id}.")
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

    def get_order_by_backtest_pagination(self, backtest_id: str, page: int = 0, size: int = 100, engine=None) -> MOrder:
        GLOG.INFO(f"Try to get Order about {order_id}.")
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
            db.session.close()
            return []
        for i in r:
            i.code = i.code.strip(b"\x00".decode())
        db.session.close()
        return r

    def get_order_df_by_backtest_pagination(
        self, backtest_id: str, page: int = 0, size: int = 100, engine=None
    ) -> MOrder:
        GLOG.INFO(f"Try to get Order about {order_id}.")
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
        GLOG.INFO(f"Try to get Order about {order_id}.")
        db = engine if engine else self.get_driver(MOrder)
        r = db.session.query(MOrder).filter(MOrder.uuid == order_id).filter(MOrder.isdel == False).first()
        if r is not None:
            r.code = r.code.strip(b"\x00".decode())
        db.session.close()
        return r

    def get_order_df_by_id(self, order_id: str, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MOrder)
        r = db.session.query(MOrder).filter(MOrder.uuid == order_id).filter(MOrder.isdel == False)
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()

        if df.shape[0] > 1:
            GLOG.ERROR(f"Order_id :{order_id} has {df.shape[0]} records, please check the code and clean the database.")
            # TODO clean the database
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        db.session.close()
        return df

    def get_order_df(self, order_id: str, engine=None) -> pd.DataFrame:
        """
        Deprecated. Use get_order_df_by_id
        """
        db = engine if engine else self.get_driver(MOrder)
        r = db.session.query(MOrder).filter(MOrder.uuid == order_id).filter(MOrder.isdel == False)
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()

        if df.shape[0] > 1:
            GLOG.ERROR(f"Order_id :{order_id} has {df.shape[0]} records, please check the code and clean the database.")
            # TODO clean the database
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        db.session.close()
        return df

    def get_order_df_by_portfolioid(self, portfolio_id: str, engine=None) -> pd.DataFrame:
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
            GLOG.INFO("Try get order df by backtest, but no order found.")
            db.session.close()
            return pd.DataFrame()
        GLOG.INFO(f"Get Order DF with backtest: {backtest_id}")
        GLOG.INFO(df)
        df["code"] = df["code"].apply(lambda x: x.strip("\x00"))
        db.session.close()
        return df

    # << CRUD of ORDER

    # Filter with ADJUSTFACTOR >>

    def filter_with_adjustfactor(self, code: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the OHLC with adjustfactor.
        """
        GLOG.INFO(f"Cal {code} Adjustfactor.")
        if df.shape[0] == 0:
            GLOG.INFO(f"You should not pass a empty dataframe.")
            return pd.DataFrame()
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        date_start = df.loc[0, ["timestamp"]].values[0]
        date_end = df.loc[df.shape[0] - 1, ["timestamp"]].values[0]
        ad = self.get_adjustfactor_df(code, date_start=GCONF.DEFAULTSTART, date_end=GCONF.DEFAULTEND)
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
        GLOG.INFO(f"Get Stockinfo about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        r = db.session.query(MStockInfo).filter(MStockInfo.code == code).filter(MStockInfo.isdel == False).first()
        db.session.close()
        return r

    def get_stock_info_df_by_code(self, code: str = None, engine=None) -> pd.DataFrame:
        GLOG.INFO(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        r = db.session.query(MStockInfo).filter(MStockInfo.code == code).filter(MStockInfo.isdel == False)
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        db.session.close()
        return df

    def get_stock_info_df_pagination(self, page: int = 0, size: int = 100, engine=None) -> pd.DataFrame:
        """
        Deprecated
        """
        GLOG.INFO(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        r = db.session.query(MStockInfo).filter(MStockInfo.isdel == False).offset(page * size).limit(size)
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        db.session.close()
        return df

    def get_stock_info_df(self, code: str = None, engine=None) -> pd.DataFrame:
        """
        Deprecated
        """
        GLOG.INFO(f"Get Stockinfo df about {code}.")
        db = engine if engine else self.get_driver(MStockInfo)
        if code == "" or code is None:
            r = db.session.query(MStockInfo).filter(MStockInfo.isdel == False)
        else:
            r = db.session.query(MStockInfo).filter(MStockInfo.code == code).filter(MStockInfo.isdel == False)
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="code", ascending=True)
        db.session.close()
        return df

    def get_stockinfo_df_fuzzy(self, filter: str, page: int = 0, size: int = 20, engine=None) -> pd.DataFrame:
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
        db.session.close()
        return df

    def get_trade_calendar(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.INFO(f"Try get Trade Calendar.")
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
        db.session.close()
        return r

    def get_trade_calendar_df(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> pd.DataFrame:
        GLOG.INFO(f"Try get Trade Calendar df.")
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
        GLOG.INFO(f"Try get DAYBAR about {code} from {date_start} to {date_end}.")
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
        db.session.close()
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
        GLOG.INFO(f"Try get DAYBAR df about {code} from {date_start} to {date_end}.")
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
        db.session.close()
        return df

    def get_adjustfactor(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        engine=None,
    ) -> list:
        GLOG.INFO(f"Try get ADJUSTFACTOR from database about {code} from {date_start} to {date_end}.")
        data_logger.INFO(f"Try get ADJUSTFACTOR from database about {code} from {date_start} to {date_end}.")
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
        db.session.close()
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
        GLOG.INFO(f"Try get ADJUSTFACTOR df about {code} from db from {date_start} to {date_end}.")
        data_logger.INFO(f"Try get ADJUSTFACTOR df about {code} from db from {date_start} to {date_end}.")
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
        db.session.close()
        return df

    def is_tick_indb(self, code: str, date: any, engine=None) -> bool:
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return False
        date = datetime_normalize(date)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
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
        GLOG.INFO(f"Try get TICK about {code} from {date_start} to {date_end}.")
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
        db.session.close()
        return r

    def get_tick_df_by_daterange(self, code: str, date_start: any, date_end: any, engine=None) -> pd.DataFrame:
        GLOG.INFO(f"Try get TICK df about {code} from {date_start} to {date_end}.")
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

    def get_tick_df(self, code: str, date_start: any, date_end: any, engine=None) -> pd.DataFrame:
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
        data_logger.DEBUG(f"Start updating TICK {code}.")
        info = self.get_stock_info_df(code)
        fast_max = 30

        # Condition 1 No data info in db.
        if info is None:
            GLOG.ERROR(f"{code} not exsit in db, please check your code or try updating the stock info")
            data_logger.ERROR(f"{code} not exsit in db, please check your code or try updating the stock info")
            return

        if info.shape[0] == 0:
            GLOG.WARN(f"{code} has no stock info in db.")
            console.print(
                f":zipper-mouth_face: Please run [steel_blue1]ginkgo data update --stockinfo[/steel_blue1] first."
            )
            return

        # CreateTable
        model = self.get_tick_model(code)
        self.create_table(model)

        db = engine if engine else self.get_driver(model)
        # Try Fetch Data

        # Condition 2 Fast Mode, Just Insert the latest period
        # Condition 3 Update and Insert
        t0 = datetime.datetime.now()
        fast_count = 0
        insert_count = 0
        tdx = GinkgoTDX()
        date_start = info.list_date.values[0]
        date_start = datetime_normalize(str(pd.Timestamp(date_start)))
        date_end = info.delist_date.values[0]
        date_end = datetime_normalize(str(pd.Timestamp(date_end)))
        today = datetime.datetime.now()
        today = today.strftime("%Y%m%d")
        today = datetime_normalize(today)

        def insert_tick_from_df(df, date):
            l = []
            model = self.get_tick_model(code)
            size0 = GDATA.get_table_size(model)
            for i, r in df.iterrows():
                timestamp = f"{today.strftime('%Y-%m-%d')} {r.timestamp}:00"
                timestamp = datetime_normalize(timestamp)
                price = float(r.price)
                volume = int(r.volume)
                buyorsell = int(r.buyorsell)
                buyorsell = TICKDIRECTION_TYPES(buyorsell)
                item = model()
                item.set(code, price, volume, buyorsell, timestamp)
                l.append(item)
            self.add_all(l)
            beep(freq=900.7, repeat=2, delay=10, length=100)
            size1 = GDATA.get_table_size(model)
            GLOG.DEBUG(f"Add {len(l)} tick about {code} on {date}, Table: {size0} -> {size1} Insert: {size1-size0}")
            data_logger.INFO(
                f"Add {len(l)} tick about {code} on {date}, Table: {size0} -> {size1} Insert: {size1-size0}"
            )
            time.sleep(2)

        def should_replace_tick(df_old, df_new):
            # Do compare
            # if same return True, else return False
            GLOG.INFO(f"Check data about {df_old.shape} and {df_new.shape}")
            beep(freq=1200.7, repeat=1, delay=10, length=200)
            df_old.sort_values(
                by=["timestamp", "volume", "price"],
                ascending=[True, True, True],
                inplace=True,
            )
            df_old.reset_index(drop=True, inplace=True)
            df_new.sort_values(
                by=["timestamp", "volume", "price"],
                ascending=[True, True, True],
                inplace=True,
            )
            df_new.reset_index(drop=True, inplace=True)
            t0 = datetime.datetime.now()
            res = False
            for i, r in df_new.iterrows():
                data1 = df_old.loc[i]
                data2 = df_new.loc[i]
                date1 = data1.timestamp.strftime("%H:%M")
                date2 = data2.timestamp
                c1 = date1 == date2
                if not c1:
                    res = True
                    break
                price1 = data1.price
                price2 = data2.price
                c2 = abs(price1 - price2) < GCONF.EPSILON
                if not c2:
                    res = True
                    break
                volume1 = data1.volume
                volume2 = data2.volume
                c3 = volume1 == volume2
                if not c3:
                    res = True
                    break
            t1 = datetime.datetime.now()
            GLOG.DEBUG(f"Comparing df done, cost {t1-t0}. {'REPLACE' if res else 'NOTHING NEW'}")
            data_logger.DEBUG(f"Comparing df done, cost {t1-t0}. {'REPLACE' if res else 'NOTHING NEW'}")
            beep(freq=300.7, repeat=1, delay=10, length=50)
            return res

        while True:
            if fast_count >= fast_max:
                data_logger.INFO(f"There is no data about {code} to update {fast_count}/{fast_max}. Exit {today}.")
                GLOG.INFO(f"There is no data about {code} to update {fast_count}/{fast_max}. Exit {today}.")
                break
            # Check everyday from today back to list date.
            if today < date_start:
                break
            df = tdx.fetch_history_transaction(code, today)
            # No data from remote, go next
            if df.shape[0] == 0:
                origin_date = today
                today = today + datetime.timedelta(days=-1)
                if fast_mode:
                    fast_count += 1
                GLOG.INFO(f"There is nodata at {origin_date} from remote. Go next {today}.")
                data_logger.INFO(f"There is nodata at {origin_date} from remote. Go next {today}.")
                continue
            GLOG.INFO(f"Got {df.shape[0]} records on {today} from remote.")
            data_logger.INFO(f"Got {df.shape[0]} records on {today} from remote.")

            df_old = self.get_tick_df_by_daterange(
                code,
                today,
                today + datetime.timedelta(days=1) + datetime.timedelta(seconds=-1),
            )
            # No data in db, do insert
            if df_old.shape[0] == 0:
                GLOG.INFO(f"No tick data in db about {code} on {today}, Do insert.")
                data_logger.INFO(f"No tick data in db about {code} on {today}, Do insert.")
                insert_tick_from_df(df, today)
                fast_count = 0

            # Already has data in db
            need_replace = True
            # Same size , check if need to erase the data in db
            if df_old.shape[0] == df.shape[0]:
                # if fastmode, go next
                if fast_mode:
                    GLOG.INFO(
                        f"In Fast mode, {today} has the same shape between remote and db. {fast_count}/{fast_max}"
                    )
                    data_logger.INFO(
                        f"In Fast mode, {today} has the same shape between remote and db. {fast_count}/{fast_max}"
                    )
                    today = today + datetime.timedelta(days=-1)
                    fast_count += 1
                    continue
                # not fastmode, do check
                need_replace = should_replace_tick(df_old, df)

            if need_replace:
                self.remove_tick(code, today)
                insert_tick_from_df(df, today)
                fast_count = 0
            today = today + datetime.timedelta(days=-1)
        t1 = datetime.datetime.now()
        GLOG.INFO(f"Updating tick about {code} complete, cost {t1-t0}.")
        data_logger.INFO(f"Updating tick about {code} complete, cost {t1-t0}.")

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
        data_logger.DEBUG(f"Current Stock Info Size: {size}")
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
        data_logger.DEBUG(f"Insert {len(l)} stock info.")
        t1 = datetime.datetime.now()
        data_logger.DEBUG(f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}")
        GLOG.DEBUG(f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}")
        size = db.get_table_size(MStockInfo)
        GLOG.DEBUG(f"After Update Stock Info Size: {size}")
        data_logger.DEBUG(f"After Update Stock Info Size: {size}")
        db.session.close()

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
        GLOG.INFO(f"Current Trade Calendar Size: {size}")
        data_logger.INFO(f"Current Trade Calendar Size: {size}")
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
                data_logger.ERROR("Tushare get no data. Update CN TradeCalendar Failed.")
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
                        data_logger.ERROR(f"Trade Calendar have {len(q)} {market} date on {date}")
                        GLOG.ERROR(f"Trade Calendar have {len(q)} {market} date on {date}")
                    for item2 in q:
                        if item2.timestamp == date and item2.market == market and str2bool(item2.is_open) == is_open:
                            GLOG.INFO(f"Ignore TradeCalendar {date} {market}")
                            data_logger.INFO(f"Ignore TradeCalendar {date} {market}")
                            continue
                        item2.timestamp = date
                        item2.market = market
                        item2.is_open = is_open
                        item2.update = datetime.datetime.now()
                        update_count += 1
                        db.session.commit()
                        data_logger.INFO(f"Update {item2.timestamp} {item2.market} TradeCalendar")
                        GLOG.INFO(f"Update {item2.timestamp} {item2.market} TradeCalendar")

                if len(q) == 0:
                    # Not Exist in db
                    l.append(item)
                    if len(l) >= self.batch_size:
                        self.add_all(l)
                        insert_count += len(l)
                        GLOG.INFO(f"Insert {len(l)} Trade Calendar.")
                        data_logger.INFO(f"Insert {len(l)} Trade Calendar.")
                        l = []
            self.add_all(l)
        GLOG.INFO(f"Insert {len(l)} Trade Calendar.")
        data_logger.INFO(f"Insert {len(l)} Trade Calendar.")
        insert_count += len(l)
        t1 = datetime.datetime.now()
        data_logger.INFO(f"TradeCalendar Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}")
        GLOG.INFO(f"TradeCalendar Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}")
        size = db.get_table_size(MTradeDay)
        db.session.close()
        GLOG.INFO(f"After Update Trade Calendar Size: {size}")
        data_logger.INFO(f"After Update Trade Calendar Size: {size}")

    def update_cn_daybar(self, code: str, fast_mode: bool = False) -> None:
        GLOG.INFO(f"Updating CN DAYBAR about {code}.")
        data_logger.INFO(f"Updating CN DAYBAR about {code}.")
        # Get the stock info of code
        t0 = datetime.datetime.now()
        GLOG.INFO(f"Get stock info about {code}")
        data_logger.INFO(f"Get stock info about {code}")
        info = self.get_stock_info_df(code)

        # Condition 1 No data info in db.
        if info is None:
            GLOG.ERROR(f"{code} not exsit in db, please check your code or try updating the stock info")
            data_logger.ERROR(f"{code} not exsit in db, please check your code or try updating the stock info")
            return

        if info.shape[0] == 0:
            GLOG.WARN(f"{code} has no stock info in db.")
            console.print(
                f":zipper-mouth_face: Please run [steel_blue1]ginkgo data update --stockinfo[/steel_blue1] first."
            )
            return

        # Condition 2 Fast Mode, Just Insert the latest period.
        driver = self.get_driver(MBar)
        tu = GinkgoTushare()
        update_count = 0
        insert_count = 0
        date_start = info.list_date.values[0]
        date_start = datetime_normalize(str(pd.Timestamp(date_start)))
        date_end = info.delist_date.values[0]
        date_end = datetime_normalize(str(pd.Timestamp(date_end)))
        today = datetime.datetime.now()
        if today < date_end:
            date_end = today
        if fast_mode:
            old_df = self.get_daybar_df(code)
            latest_date = old_df.iloc[-1]["timestamp"]
            # TODO get missing period
            p = date_end - latest_date
            if p < datetime.timedelta(days=1):
                return
            l = []
            # TODO fetch data
            rs = tu.fetch_cn_stock_daybar(code, latest_date, date_end)
            if rs.shape[0] == 0:
                data_logger.INFO(f"No new data about {code} from remote.")
                return
            # TODO insert
            for i, r in rs.iterrows():
                date = datetime_normalize(r["trade_date"])
                query = self.get_daybar_df(code, date, date)
                if query.shape[0] > 0:
                    continue
                # New Insert
                item = MBar()
                item.set_source(SOURCE_TYPES.TUSHARE)
                item.set(
                    code,
                    r["open"],
                    r["high"],
                    r["low"],
                    r["close"],
                    r["vol"],
                    FREQUENCY_TYPES.DAY,
                    date,
                )
                l.append(item)
                if len(l) >= self.batch_size:
                    driver.session.add_all(l)
                    driver.session.commit()
                    beep(freq=900.7, repeat=2, delay=10, length=100)
                    insert_count += len(l)
                    GLOG.INFO(f"Insert {len(l)} {code} Daybar.")
                    data_logger.INFO(f"Insert {len(l)} {code} Daybar.")
                    l = []
            if len(l) > 0:
                driver.session.add_all(l)
                driver.session.commit()
                insert_count += len(l)
                GLOG.INFO(f"Insert {len(l)} {code} Daybar.")
                data_logger.INFO(f"Insert {len(l)} {code} Daybar.")
            self.clean_db()
            GLOG.INFO(f"Complete updating {code} AdjustFactor.")
            data_logger.INFO(f"Complete updating {code} AdjustFactor.")
            return

        # Condition 3 Update and insert.
        GLOG.INFO(f"Updating Daybar from {date_start} to {date_end}")
        data_logger.INFO(f"Updating Daybar from {date_start} to {date_end}")
        start_pd = pd.to_datetime(date_start)
        end_pd = pd.to_datetime(date_end)
        slice_length = "400D"
        time_slices = pd.date_range(start=start_pd, end=end_pd, freq=slice_length)
        time_period = []
        for i in range(len(time_slices) - 1):
            time_period.append((time_slices[i], time_slices[i + 1]))
        time_period.append((time_slices[-1], end_pd))
        time_period.reverse()
        for period in time_period:
            update_list = []
            insert_list = []
            t1 = period[0]
            t2 = period[1]
            GLOG.INFO(f"Deleaing with {code} daybar from {t1} - {t2}")
            data_logger.INFO(f"Deleaing with {code} daybar from {t1} - {t2}")
            df_old = self.get_daybar_df(code, t1, t2)
            df = tu.fetch_cn_stock_daybar(code, t1, t2)
            # Fetch data from t1 to t2 about code
            for i, r in df.iterrows():
                have_data = df_old["timestamp"].isin([datetime_normalize(r["trade_date"])]).any()
                if have_data:
                    data_in_db = df_old[df_old["timestamp"] == datetime_normalize(r["trade_date"])]

                    is_open_same = data_in_db.open.values[0] - r.open < GCONF.EPSILON
                    if not is_open_same:
                        update_list.append(r["trade_date"])
                        continue

                    is_high_same = data_in_db.high.values[0] - r.high < GCONF.EPSILON
                    if not is_high_same:
                        update_list.append(r["trade_date"])
                        continue

                    is_low_same = data_in_db.low.values[0] - r.low < GCONF.EPSILON
                    if not is_low_same:
                        update_list.append(r["trade_date"])
                        continue

                    is_close_same = data_in_db.close.values[0] - r.close < GCONF.EPSILON
                    if not is_close_same:
                        update_list.append(r["trade_date"])
                        continue

                    is_volume_same = data_in_db.volume.values[0] - int(r.vol) < GCONF.EPSILON
                    if not is_volume_same:
                        update_list.append(r["trade_date"])
                        continue
                else:
                    insert_list.append(r["trade_date"])
            GLOG.INFO(f"To Update: {len(update_list)}")
            data_logger.INFO(f"To Update: {len(update_list)}")
            for i in update_list:
                date = datetime_normalize(i)
                print(date)
                q = self.get_daybar(code, date, date)

                if len(q) == 0:
                    print("should have data, check the code.")
                elif len(q) == 1:
                    item = q[0]
                    item.open = round(df[df["trade_date"] == i].open.values[0], 6)
                    item.high = round(df[df["trade_date"] == i].high.values[0], 6)
                    item.low = round(df[df["trade_date"] == i].low.values[0], 6)
                    item.close = round(df[df["trade_date"] == i].close.values[0], 6)
                    item.volume = int(df[df["trade_date"] == i].vol.values[0])
                    item.update = datetime.datetime.now()
                    update_count += 1
                    driver.session.commit()
                    GLOG.INFO(f"Update {code} {date} Daybar")
                    data_logger.INFO(f"Update {code} {date} Daybar")
                else:
                    # There are more than 1 record in db.
                    # Clean the data and reinsert.
                    driver.session.query(MBar).filter(MBar.code == code).filter(MBar.timestamp == date).delete()
                    driver.session.commit()
                    # add date to insert_list
                    insert_list.append(i)

            GLOG.INFO(f"To Insert: {len(insert_list)}")
            data_logger.INFO(f"To Insert: {len(insert_list)}")

            l = []
            for i in insert_list:
                date = datetime_normalize(i)
                item = MBar()
                item.set_source(SOURCE_TYPES.TUSHARE)
                o = df[df["trade_date"] == i].open.values[0]
                h = df[df["trade_date"] == i].high.values[0]
                low = df[df["trade_date"] == i].low.values[0]
                c = df[df["trade_date"] == i].close.values[0]
                v = int(df[df["trade_date"] == i].vol.values[0])
                item.set(
                    code,
                    o,
                    h,
                    low,
                    c,
                    v,
                    FREQUENCY_TYPES.DAY,
                    date,
                )
                l.append(item)
                if len(l) >= self.batch_size:
                    driver.session.add_all(l)
                    driver.session.commit()
                    beep(freq=900.7, repeat=2, delay=10, length=100)
                    insert_count += len(l)
                    GLOG.INFO(f"Insert {len(l)} {code} AdjustFactor.")
                    data_logger.INFO(f"Insert {len(l)} {code} AdjustFactor.")
                    l = []
            if len(l) > 0:
                driver.session.add_all(l)
                driver.session.commit()
                insert_count += len(l)
                GLOG.INFO(f"Insert {len(l)} {code} Daybar.")
                data_logger.INFO(f"Insert {len(l)} {code} Daybar.")
            self.clean_db()
            GLOG.INFO(f"Complete updating {code} Daybar from {t1} - {t2}.")
            data_logger.INFO(f"Complete updating {code} Daybar from {t1} - {t2}.")
            GLOG.INFO(f"Complete updating {code} Daybar from {t1} - {t2}.")
            data_logger.INFO(f"Complete updating {code} Daybar from {t1} - {t2}.")
        GLOG.INFO(f"Complete updating {code} Daybar.")
        data_logger.INFO(f"Complete updating {code} Daybar.")

    def update_all_cn_daybar(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_cn_daybar(code)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Update ALL CN Daybar cost {t1-t0}")

    def update_all_cn_daybar_aysnc(self, fast_mode=False) -> None:
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

    def update_cn_adjustfactor(self, code: str, fast_mode: bool = False, queue=None) -> None:
        t0 = datetime.datetime.now()
        GLOG.INFO(f"Updating AdjustFactor about {code}. {t0}")
        data_logger.INFO(f"Updating AdjustFactor about {code}.")
        t0 = datetime.datetime.now()
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_adjustfactor(code)
        GLOG.INFO(f"Got {df.shape[0]} Adjustfactor about {code}.")
        data_logger.INFO(f"Got {df.shape[0]} Adjustfactor about {code}.")

        # Condition 1
        # There is no data from remote.
        if df.shape[0] == 0:
            GLOG.INFO(f"There is no adjustfactor about {code} from remote. Quit updating.")
            ginkgo_logger.INFO(f"There is no adjustfactor about {code} from remote. Quit updating.")
            return

        df_old = self.get_adjustfactor_df(code, GCONF.DEFAULTSTART, GCONF.DEFAULTEND)
        # Condition 2
        # Insert and update
        insert_count = 0
        update_count = 0
        l = []
        GLOG.INFO(f"Ergodic {code} AdjustFactor.")
        data_logger.INFO(f"Ergodic {code} AdjustFactor.")
        duplicated_count = 0

        update_list = []
        insert_list = []
        for i, r in df.iterrows():
            date_raw = r["trade_date"]
            factor = r["adj_factor"]
            have_data = df_old["timestamp"].isin([datetime_normalize(date_raw)]).any()
            if have_data:
                if (
                    r["adj_factor"]
                    != df_old[df_old["timestamp"] == datetime_normalize(date_raw)]["adjustfactor"].values[0]
                ):
                    update_list.append(date_raw)
            else:
                insert_list.append(date_raw)

        GLOG.INFO(f"Will update {len(update_list)} insert {len(insert_list)} {code} AdjustFactor.")
        data_logger.INFO(f"Will update {len(update_list)} insert {len(insert_list)} {code} AdjustFactor.")
        driver = self.get_driver(MAdjustfactor)

        # Update
        for i in update_list:
            date = datetime_normalize(i)
            q = self.get_adjustfactor(code, date, date)
            if len(q) == 0:
                print("should have data, check the code.")
            elif len(q) == 1:
                item = q[0]
                item.adjustfactor = df[df["trade_date"] == i]["adj_factor"].values[0]
                item.update = datetime.datetime.now()
                update_count += 1
                driver.session.commit()
                GLOG.INFO(f"Update {code} {date} AdjustFactor")
                data_logger.INFO(f"Update {code} {date} AdjustFactor")
            else:
                # There are more than 1 record in db.
                # Clean the data and reinsert.
                db.session.query(MAdjustfactor).filter(MAdjustfactor.code == code).filter(
                    MAdjustfactor.timestamp == date
                ).delete()
                db.session.commit()
                # add date to insert_list
                insert_list.append(i)
        # Insert
        for i in insert_list:
            date = datetime_normalize(i)
            o = MAdjustfactor()
            o.set_source(SOURCE_TYPES.TUSHARE)
            o.set(code, 1.0, 1.0, df[df["trade_date"] == i]["adj_factor"].values[0], date)
            l.append(o)
            if len(l) >= self.batch_size:
                driver.session.add_all(l)
                driver.session.commit()
                beep(freq=900.7, repeat=2, delay=10, length=100)
                insert_count += len(l)
                GLOG.INFO(f"Insert {len(l)} AdjustFactor about {code}.")
                data_logger.INFO(f"Insert {len(l)} AdjustFactor about {code}.")
                l = []
        if len(l) > 0:
            driver.session.add_all(l)
            driver.session.commit()
            insert_count += len(l)
            GLOG.INFO(f"Insert {len(l)} AdjustFactor about {code}.")
            data_logger.INFO(f"Insert {len(l)} AdjustFactor about {code}.")
        self.clean_db()
        t1 = datetime.datetime.now()
        GLOG.INFO(f"Complete updating {code} AdjustFactor. Cost: {t1-t0}")
        data_logger.INFO(f"Complete updating {code} AdjustFactor. Cost: {t1-t0}")

    def update_all_cn_adjustfactor(self, fast_mode=False):
        GLOG.INFO(f"Begin to update all CN AdjustFactor")
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        info = info[100:102]
        with Progress() as progress:
            task = progress.add_task("Updating CN AdjustFactor: ", total=info.shape[0])
            for i, r in info.iterrows():
                code = r["code"]
                progress.update(
                    task,
                    advance=1,
                    description=f"Updating AdjustFactor: [light_coral]{code}[/light_coral]",
                )
                self.update_cn_adjustfactor(code, fast_mode, None)
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

    def update_all_cn_adjustfactor_aysnc(self, fast_mode=False):
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

        t = threading.Thread(target=self.start_listen, args=("Updating CN AdjustFactor", len(l), q))

        for code in l:
            res = p.apply_async(
                self.update_cn_adjustfactor,
                args=(
                    code,
                    fast_mode,
                    q,
                ),
            )

        p.close()
        t.start()
        p.join()
        t.join()
        t1 = datetime.datetime.now()
        size = self.create_mysql_connection().get_table_size(MAdjustfactor)
        GLOG.INFO(f"Update ALL CN AdjustFactor cost {t1-t0}")
        GLOG.INFO(f"After Update Adjustfactor Size: {size}")

    def get_file(self, id: str, engine=None) -> MFile:
        db = engine if engine else self.get_driver(MFile)
        r = db.session.query(MFile).filter(MFile.uuid == id).filter(MFile.isdel == False).first()
        return r

    def get_file_by_id(self, file_id: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = db.session.query(MFile).filter(MFile.uuid == file_id).filter(MFile.isdel == False).first()
        return r

    def get_file_by_backtest(self, backtest_id: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = db.session.query(MFile).filter(MFile.backtest_id == backtest_id).filter(MFile.isdel == False).first()
        return r

    def get_file_by_name(self, name: str, engine=None):
        db = engine if engine else self.get_driver(MFile)
        r = db.session.query(MFile).filter(MFile.file_name == name).filter(MFile.isdel == False).first()
        return r

    def get_file_list_df(self, type: FILE_TYPES = None, page: int = 0, size: int = 20, engine=None):
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

    def get_file_list_df_fuzzy(self, filter: str, page: int = 0, size: int = 20, engine=None):
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
        r = db.session.query(MFile).filter(MFile.uuid == id).filter(MFile.isdel == False).first()
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

    def copy_file(self, type: FILE_TYPES, name: str, source: str, is_live: bool = False) -> MFile:
        file = self.get_file(source)
        if file is None:
            GLOG.INFO(f"File {source} not exist. Copy failed.")
            return
        item = MFile()
        item.type = type
        item.file_name = name
        item.islive = is_live
        item.content = file.content
        if type == FILE_TYPES.ENGINE:
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
        r = db.session.query(MFile).filter(MFile.uuid == id).filter(MFile.isdel == False).first()
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
                        GLOG.INFO(f"Add {file_name}")

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
                item.type = FILE_TYPES.ENGINE
                item.file_name = default_backtest_name
                item.content = content
                self.add(item)
                GLOG.INFO("Add DefaultStrategy.yml")
        for i in file_map:
            walk_through(i)

    def add_backtest(self, backtest_id: str, content: bytes) -> str:
        item = MPortfolio()
        item.set(backtest_id, datetime.datetime.now(), content)
        id = item.uuid
        self.add(item)
        return id

    def add_liveportfolio(self, name: str, engine_id: str, content: bytes) -> str:
        item = MPortfolio()
        conf = yaml.safe_load(content)

        # risk manager
        risk_conf = conf["risk_manager"]
        old_risk_id = risk_conf["id"]
        risk_file = self.get_file_by_id(old_risk_id)
        risk_name = risk_file.file_name
        new_risk_name = f"{risk_name}_{name}"
        new_risk_name = new_risk_name[:35]
        new_risk_id = self.copy_file(FILE_TYPES.RISKMANAGER, new_risk_name, old_risk_id, True)
        conf["risk_manager"]["id"] = new_risk_id

        # selector
        select_conf = conf["selector"]
        old_select_id = select_conf["id"]
        select_file = self.get_file_by_id(old_select_id)
        select_name = select_file.file_name
        new_select_name = f"{select_name}_{name}"
        new_select_name = new_select_name[:35]
        new_select_id = self.copy_file(FILE_TYPES.SELECTOR, new_select_name, old_select_id, True)
        conf["selector"]["id"] = new_select_id

        # sizer
        sizer_conf = conf["sizer"]
        old_sizer_id = sizer_conf["id"]
        sizer_file = self.get_file_by_id(old_sizer_id)
        sizer_name = sizer_file.file_name
        new_sizer_name = f"{sizer_name}_{name}"
        new_sizer_name = new_sizer_name[:35]
        new_sizer_id = self.copy_file(FILE_TYPES.SIZER, new_sizer_name, old_sizer_id, True)
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

    def get_liveportfolio(self, engine_id: str, engine=None) -> MPortfolio:
        db = engine if engine else self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.engine_id == engine_id)
            .filter(MPortfolio.isdel == False)
            .first()
        )
        return r

    def get_liveportfolio_df(self, engine_id: str, engine=None) -> MPortfolio:
        db = engine if engine else self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.engine_id == engine_id)
            .filter(MPortfolio.isdel == False)
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
        db = self.get_driver(MPortfolio)
        r = db.session.query(MPortfolio).filter(MPortfolio.uuid == engine_id).filter(MPortfolio.isdel == False).first()
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
        db = self.get_driver(MPortfolio)
        try:
            db.session.query(MPortfolio).filter(MPortfolio.uuid == id).delete()
            db.session.commit()
            db.session.close()
            return True
        except Exception as e:
            print(e)
            return False

    def get_liveportfolio_pagination(self, page: int = 0, size: int = 100, engine=None) -> MPortfolio:
        db = engine if engine else self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.isdel == False)
            .order_by(MPortfolio.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        db.session.close()
        return r

    def get_liveportfolio_df_pagination(self, page: int = 0, size: int = 100, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.isdel == False)
            .order_by(MPortfolio.start_at.desc())
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
        db = self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.uuid == backtest_id)
            .filter(MPortfolio.isdel == False)
            .first()
        )
        if r is None:
            return False
        db.session.delete(r)
        db.session.commit()
        db.session.close()
        return True

    def finish_backtest(self, backtest_id: str) -> bool:
        db = self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.backtest_id == backtest_id)
            .filter(MPortfolio.isdel == False)
            .first()
        )
        if r is None:
            GLOG.INFO(f"Can not find backtest {backtest_id} in database.")
            return False
        r.finish(datetime.datetime.now())
        db.session.commit()
        db.session.close()
        GLOG.INFO(f"Backtest {backtest_id} finished.")
        return True

    def remove_orders(self, backtest_id: str) -> int:
        db = self.get_driver(MOrder)
        r = db.session.query(MOrder).filter(MOrder.backtest_id == backtest_id).filter(MOrder.isdel == False).all()
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
            db.session.query(MOrderRecord).filter(MOrderRecord.portfolio_id == id).delete()
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
            r = db.session.query(MAnalyzer).filter(MAnalyzer.backtest_id == backtest_id).all()
            count = len(r)
            db.session.query(MAnalyzer).filter(MAnalyzer.backtest_id == backtest_id).delete()
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
        db = self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.backtest_id == backtest_id)
            .filter(MPortfolio.isdel == False)
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
            GLOG.INFO("Can not finish the backtest record with empty backtest_id.")
            return False
        db = self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.backtest_id == backtest_id)
            .filter(MPortfolio.isdel == False)
            .first()
        )
        if r is None:
            return False
        else:
            r.finish(datetime.datetime.now())
            db.session.commit()
            return True

    def get_backtest_record_by_backtest(self, backtest_id: str) -> MPortfolio:
        db = self.get_driver(MPortfolio)
        if backtest_id == "":
            GLOG.INFO("Can not get backtest record with empty backtest_id.")
            return
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.uuid == backtest_id)
            .filter(MPortfolio.isdel == False)
            .order_by(MPortfolio.start_at.desc())
            .first()
        )
        return r

    def get_backtest_record(self, backtest_id: str) -> MPortfolio:
        db = self.get_driver(MPortfolio)
        if backtest_id == "":
            GLOG.INFO("Can not get backtest record with empty backtest_id.")
            return
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.uuid == backtest_id)
            .filter(MPortfolio.isdel == False)
            .order_by(MPortfolio.start_at.desc())
            .first()
        )
        return r

    def get_backtest_record_pagination(self, page: int = 0, size: int = 100, engine=None) -> MPortfolio:
        db = engine if engine else self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.isdel == False)
            .order_by(MPortfolio.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        db.session.close()
        return r

    def get_backtest_record_df_pagination(self, page: int = 0, size: int = 100, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MPortfolio)
        r = (
            db.session.query(MPortfolio)
            .filter(MPortfolio.isdel == False)
            .order_by(MPortfolio.start_at.desc())
            .offset(page * size)
            .limit(size)
        )
        df = pd.read_sql(r.statement, db.engine)
        df = df.sort_values(by="start_at", ascending=False)
        db.session.close()
        return df

    def get_backtest_list_df(self, backtest_id: str = "") -> pd.DataFrame:
        db = self.get_driver(MPortfolio)
        if backtest_id == "":
            r = db.session.query(MPortfolio).filter(MPortfolio.isdel == False)
        else:
            r = (
                db.session.query(MPortfolio)
                .filter(MPortfolio.backtest_id == backtest_id)
                .filter(MPortfolio.isdel == False)
                .order_by(MPortfolio.start_at.desc())
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

    def get_analyzers_df_by_backtest(self, backtest_id: str, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MAnalyzer)
        r = db.session.query(MAnalyzer).filter(MAnalyzer.backtest_id == backtest_id).filter(MAnalyzer.isdel == False)
        df = pd.read_sql(r.statement, db.engine)

        if df.shape[0] == 0:
            GLOG.INFO("Try get analyzer df by backtest, but no order found.")
            return pd.DataFrame()
        GLOG.INFO(f"Get Analyzer DF with backtest: {backtest_id}")
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)

        return df

    def get_analyzer_df_by_backtest(self, backtest_id: str, analyzer_id: str, engine=None) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MAnalyzer)
        r = (
            db.session.query(MAnalyzer)
            .filter(MAnalyzer.backtest_id == backtest_id)
            .filter(MAnalyzer.analyzer_id == analyzer_id)
            .filter(MAnalyzer.isdel == False)
        )
        df = pd.read_sql(r.statement, db.engine)

        if df.shape[0] == 0:
            GLOG.INFO("Try get analyzer df by backtest, but no order found.")
            return pd.DataFrame()
        GLOG.INFO(f"Get Analyzer DF with backtest: {backtest_id}")
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
        date_start: any = None,
        date_end: any = None,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MOrderRecord)
        filters = [
            MOrderRecord.portfolio_id == portfolio_id,
            MOrderRecord.isdel == False,
        ]
        if date_start is not None:
            date_start = datetime_normalize(date_start)
            filters.append(MOrderRecord.timestamp >= date_start)

        if date_end is not None:
            date_end = datetime_normalize(date_end)
            filters.append(MOrderRecord.timestamp < date_end)
        r = db.session.query(MOrderRecord).filter(and_(*filters)).offset(page * size).limit(size)

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

    def add_position_records(self, portfolio_id: str, timestamp: any, positions: list) -> None:
        for i in positions:
            if not isinstance(i, Position):
                GLOG.INFO(f"Only support add Position")
                return
        l = []
        for i in positions:
            item = MPositionRecord()
            item.set(portfolio_id, timestamp, i.code, i.volume, i.cost)
            l.append(item)
        self.add_all(l)

    def get_positionrecords_pagination(
        self,
        backtest_id: str,
        date_start: any = None,
        date_end: any = None,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MPositionRecord)
        filters = [
            MPositionRecord.portfolio_id == backtest_id,
            MPositionRecord.isdel == False,
        ]
        if date_start is not None:
            date_start = datetime_normalize(date_start)
            filters.append(MPositionRecord.timestamp >= date_start)

        if date_end is not None:
            date_end = datetime_normalize(date_end)
            filters.append(MPositionRecord.timestamp < date_end)

        r = db.session.query(MPositionRecord).filter(and_(*filters)).offset(page * size).limit(size).all()
        db.session.close()
        return r

    def get_positionrecords_df_pagination(
        self,
        backtest_id: str,
        date_start: any = None,
        date_end: any = None,
        page: int = 0,
        size: int = 1000,
        engine=None,
    ):
        db = engine if engine else self.get_driver(MPositionRecord)
        filters = [
            MPositionRecord.portfolio_id == backtest_id,
            MPositionRecord.isdel == False,
        ]

        if date_start is not None:
            date_start = datetime_normalize(date_start)
            filters.append(MPositionRecord.timestamp >= date_start)

        if date_end is not None:
            date_end = datetime_normalize(date_end)
            filters.append(MPositionRecord.timestamp < date_end)

        r = db.session.query(MPositionRecord).filter(and_(*filters)).offset(page * size).limit(size)
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def remove_positions(self, backtest_id: str, date: str = None, engine=None) -> int:
        """
        Remove position from database.
        Args:
            backtest_id(str): In backtest mode, is backtest_id, in live mode, it is portfolio_id
            date(str): the date you want to remove positions, if empty, will remove all positionrecords
        Returns:
            Delete count
        """
        db = engine if engine else self.get_driver(MPositionRecord)
        filters = [
            MPositionRecord.portfolio_id == backtest_id,
        ]
        if date is not None:
            date = datetime_normalize(date)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + datetime.timedelta(days=1)
            filters.append(MPositionRecord.timestamp >= date_start)
            filters.append(MPositionRecord.timestamp < date_end)

        result = db.session.query(MPositionRecord).filter(and_(*filters)).delete()
        db.session.commit()
        db.session.close()

        self.clean_db()

        return result

    def set_live_status(self, engine_id: str, status: str) -> None:
        self.get_redis().hset(self._live_status_name, engine_id, status)

    def remove_live_status(self, engine_id: str) -> None:
        self.get_redis().hdel(self._live_status_name, engine_id)

    def get_live_status(self) -> dict:
        data = self.get_redis().hgetall(self._live_status_name)
        return {key.decode("utf-8"): value.decode("utf-8") for key, value in data.items()}

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
        return {key.decode("utf-8"): value.decode("utf-8") for key, value in data.items()}

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

    def remove_tick(self, code: str, date: str) -> None:
        """
        Remove ticks via code and date.
        Args:
            code(str): code
            date(str): date in string
        Returns:
            None
        """
        model = self.get_tick_model(code)
        size0 = GDATA.get_table_size(model)
        date = datetime_normalize(date)
        date = date.strftime("%Y-%m-%d")
        date_start = datetime_normalize(date)
        date_end = date_start + datetime.timedelta(days=1) + datetime.timedelta(seconds=-1)
        db = self.get_driver(model)
        db.session.query(model).filter(model.code == code).filter(model.timestamp >= date_start).filter(
            model.timestamp <= date_end
        ).delete()
        db.session.commit()
        self.clean_db()
        size1 = GDATA.get_table_size(model)
        GLOG.DEBUG(f"Remove tick about {code} on {date} DB: {size0}->{size1} Remove:{size0-size1}.")
        data_logger.DEBUG(f"Remove tick about {code} on {date} DB: {size0}->{size1} Remove:{size0-size1}.")
        if size0 - size1 == 0:
            GLOG.WARN(f"Remove {code} tick on {date} failed, check your code please.")
            data_logger.WARN(f"Remove {code} tick on {date} failed, check your code please.")
        beep(freq=900.7, repeat=2, delay=10, length=100)

    def get_latest_price(self, code: str) -> float:
        """
        Get the latest price.
        Args:
            code(str): code
        Returns:
            (latest price, latest_open)
        """
        # 1. try get live price, return
        # 2. if no live price, return the latest daybar price
        now = datetime.datetime.now()
        date_start = now + datetime.timedelta(days=-20)
        price_info = self.get_daybar_df(code=code, date_start=date_start, date_end=now)  # TODO get latest price.
        if price_info.shape[0] == 0:
            print(f"{i.code} has no data from {date_start} to {now}")
            return (0, 0)
        close_price = price_info.iloc[-1]["close"]
        open_price = price_info.iloc[-1]["open"]
        return (close_price, open_price)

    def add_transferrecord(
        self,
        portfolio_id: str,
        direction: DIRECTION_TYPES,
        market: MARKET_TYPES,
        money: float,
        timestamp: any,
        engine=None,
        *args,
        **kwargs,
    ) -> None:
        db = engine if engine else self.get_driver(MTransferRecord)
        item = MTransferRecord()
        item.set(portfolio_id, direction, market, money, timestamp)
        self.add(item)

    def get_transferrecord(
        self,
        portfolio_id: str,
        engine=None,
        *args,
        **kwargs,
    ):
        db = engine if engine else self.get_driver(MTransferRecord)
        r = db.session.query(MTransferRecord).filter(MTransferRecord.portfolio_id == portfolio_id).all()
        db.session.close()
        return r

    def get_transferrecord_in_df_via_portfolioid(
        self,
        portfolio_id: str,
        engine=None,
        *args,
        **kwargs,
    ) -> pd.DataFrame:
        db = engine if engine else self.get_driver(MTransferRecord)
        r = db.session.query(MTransferRecord).filter(MTransferRecord.portfolio_id == portfolio_id).all()
        df = pd.read_sql(r.statement, db.engine)
        db.session.close()
        return df

    def remove_transferrecord_via_portfolioid(
        self,
        portfolio_id: str,
        engine=None,
        *args,
        **kwargs,
    ) -> int:
        db = engine if engine else self.get_driver(MTransferRecord)
        pass

    def remove_transferrecord_via_id(
        self,
        portfolio_id: str,
        engine=None,
        *args,
        **kwargs,
    ) -> int:
        db = engine if engine else self.get_driver(MTransferRecord)
        pass


GDATA = GinkgoData()
