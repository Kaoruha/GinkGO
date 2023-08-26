import time
import types
import datetime
import os
import pandas as pd
import multiprocessing
import threading
from sqlalchemy import DDL
from ginkgo.data.models import (
    MOrder,
    MBar,
    MStockInfo,
    MTradeDay,
    MAdjustfactor,
    MClickBase,
    MMysqlBase,
    MTick,
)
from ginkgo import GLOG, GCONF
from ginkgo.libs import datetime_normalize, str2bool
from ginkgo.enums import (
    MARKET_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
    TICKDIRECTION_TYPES,
)
from ginkgo.data.sources import GinkgoBaoStock, GinkgoTushare, GinkgoTDX
from ginkgo.data.drivers import GinkgoClickhouse, GinkgoMysql
from ginkgo.data import CLICKDRIVER, MYSQLDRIVER


class GinkgoData(object):
    """
    Data Modeul
    Get: from the db
    """

    def __init__(self):
        self._click_models = []
        self._mysql_models = []
        self.get_models()
        self.bs = GinkgoBaoStock()
        self.batch_size = 500
        self._is_click_cached = False
        self._is_mysql_cached = False
        self.cpu_ratio = 0.8
        self.tick_models = {}

    def get_driver(self, value):
        is_class = isinstance(value, type)
        driver = None
        if is_class:
            if issubclass(value, MClickBase):
                driver = CLICKDRIVER
            elif issubclass(value, MMysqlBase):
                driver = MYSQLDRIVER
        else:
            if isinstance(value, MClickBase):
                driver = CLICKDRIVER
            elif isinstance(value, MMysqlBase):
                driver = MYSQLDRIVER

        if driver is None:
            GLOG.ERROR(f"Model {value} should be sub of clickbase or mysqlbase.")
        return driver

    def add(self, value) -> None:
        driver = self.get_driver(value)
        driver.session.add(value)
        if driver == CLICKDRIVER:
            self._is_click_cached = True
        elif driver == MYSQLDRIVER:
            self._is_mysql_cached = True

    def commit(self) -> None:
        """
        Session Commit.
        """
        CLICKDRIVER.session.commit()
        MYSQLDRIVER.session.commit()
        # if self._is_click_cached:
        #     CLICKDRIVER.session.commit()
        #     self._is_click_cached = False

        # if self._is_mysql_cached:
        #     MYSQLDRIVER.session.commit()
        #     self._is_mysql_cached = True

    def add_all(self, values) -> None:
        """
        Add multi data into session
        """
        # TODO support different database engine.
        # Now is for clickhouse.
        click_list = []
        mysql_list = []
        for i in values:
            if isinstance(i, MClickBase):
                click_list.append(i)
            elif isinstance(i, MMysqlBase):
                mysql_list.append(i)
        if len(click_list) > 0:
            CLICKDRIVER.session.add_all(click_list)
            self._is_click_cached = True
        if len(mysql_list) > 0:
            MYSQLDRIVER.session.add_all(mysql_list)
            self._is_mysql_cached = True

    def get_tick_model(self, code: str) -> type:
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
        MClickBase.metadata.create_all(CLICKDRIVER.engine)
        # Create Tables in mysql
        MMysqlBase.metadata.create_all(MYSQLDRIVER.engine)

    def drop_all(self) -> None:
        """
        ATTENTION!!
        Just call the func in dev.
        This will drop all the tables in models.
        """
        # Drop Tables in clickhouse
        MClickBase.metadata.drop_all(CLICKDRIVER.engine)
        # Drop Tables in mysql
        MMysqlBase.metadata.drop_all(MYSQLDRIVER.engine)

    def is_table_exsist(self, model) -> bool:
        driver = self.get_driver(model)
        if driver.is_table_exsists(model.__tablename__):
            return True
        else:
            return False

    def drop_table(self, model) -> None:
        driver = self.get_driver(model)
        if driver is None:
            return
        if self.is_table_exsist(model):
            model.__table__.drop(driver.engine)
            GLOG.WARN(f"Drop Table {model.__tablename__} : {model}")
        else:
            GLOG.INFO(f"No need to drop {model.__tablename__} : {model}")

    def create_table(self, model) -> None:
        driver = self.get_driver(model)
        if driver is None:
            return
        if model.__abstract__ == True:
            GLOG.WARN(f"Pass Model:{model}")
            return
        if self.is_table_exsist(model):
            GLOG.WARN(f"Table {model.__tablename__} exist.")
        else:
            model.__table__.create(driver.engine)
            GLOG.INFO(f"Create Table {model.__tablename__} : {model}")

    def get_table_size(self, model) -> int:
        driver = self.get_driver(model)
        if driver is None:
            return 0
        return driver.get_table_size(model)

    def get_order(self, order_id: str) -> MOrder:
        r = (
            MYSQLDRIVER.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
            .first()
        )
        if r is not None:
            r.code = r.code.strip(b"\x00".decode())

        return r

    def get_order_df(self, order_id: str) -> pd.DataFrame:
        r = (
            MYSQLDRIVER.session.query(MOrder)
            .filter(MOrder.uuid == order_id)
            .filter(MOrder.isdel == False)
        )
        df = pd.read_sql(r.statement, MYSQLDRIVER.engine)

        if df.shape[0] > 1:
            GLOG.WARN(
                f"Order_id :{order_id} has {df.shape[0]} records, please check the code and clean the database."
            )

        df = df.iloc[0, :]
        df.code = df.code.strip(b"\x00".decode())
        return df

    def get_stock_info(self, code: str) -> MStockInfo:
        r = (
            CLICKDRIVER.session.query(MStockInfo)
            .filter(MStockInfo.code == code)
            .filter(MStockInfo.isdel == False)
            .first()
        )
        return r

    def get_stock_info_df(self, code: str = None) -> pd.DataFrame:
        if code == "" or code is None:
            r = CLICKDRIVER.session.query(MStockInfo).filter(MStockInfo.isdel == False)
        else:
            r = (
                CLICKDRIVER.session.query(MStockInfo)
                .filter(MStockInfo.code == code)
                .filter(MStockInfo.isdel == False)
            )
        df = pd.read_sql(r.statement, CLICKDRIVER.engine)
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
            CLICKDRIVER.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.timestamp >= date_start)
            .filter(MTradeDay.timestamp <= date_end)
            .filter(MTradeDay.isdel == False)
            .all()
        )
        return r

    def get_trade_calendar_df(
        self,
        market: MARKET_TYPES,
        date_start: any,
        date_end: any,
    ) -> pd.DataFrame:
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            CLICKDRIVER.session.query(MTradeDay)
            .filter(MTradeDay.market == market)
            .filter(MTradeDay.timestamp >= date_start)
            .filter(MTradeDay.timestamp <= date_end)
            .filter(MTradeDay.isdel == False)
        )
        df = pd.read_sql(r.statement, CLICKDRIVER.engine)
        return df

    def get_daybar(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
    ) -> list:
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            CLICKDRIVER.session.query(MBar)
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
    ) -> pd.DataFrame:
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            CLICKDRIVER.session.query(MBar)
            .filter(MBar.code == code)
            .filter(MBar.timestamp >= date_start)
            .filter(MBar.timestamp <= date_end)
            .filter(MBar.isdel == False)
        )
        df = pd.read_sql(r.statement, CLICKDRIVER.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def get_adjustfactor(
        self,
        code: str,
        date_start: any = GCONF.DEFAULTSTART,
        date_end: any = GCONF.DEFAULTEND,
        db_driver: MYSQLDRIVER = None,
    ) -> list:
        driver = db_driver if db_driver else MYSQLDRIVER
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            driver.session.query(MAdjustfactor)
            .filter(MAdjustfactor.code == code)
            .filter(MAdjustfactor.timestamp >= date_start)
            .filter(MAdjustfactor.timestamp <= date_end)
            .filter(MAdjustfactor.isdel == False)
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
        db_driver: MYSQLDRIVER = None,
    ) -> list:
        driver = db_driver if db_driver else MYSQLDRIVER
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            driver.session.query(MAdjustfactor)
            .filter(MAdjustfactor.code == code)
            .filter(MAdjustfactor.timestamp >= date_start)
            .filter(MAdjustfactor.timestamp <= date_end)
            .filter(MAdjustfactor.isdel == False)
        )
        df = pd.read_sql(r.statement, driver.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def is_tick_indb(self, code: str, date: any) -> bool:
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return
        date_start = datetime_normalize(date)
        date_end = date_start + datetime.timedelta(days=1)
        r = (
            CLICKDRIVER.session.query(model)
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

    def get_tick(self, code: str, date_start: any, date_end: any) -> MTick:
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return []
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            CLICKDRIVER.session.query(model)
            .filter(model.code == code)
            .filter(model.timestamp >= date_start)
            .filter(model.timestamp <= date_end)
            .filter(model.isdel == False)
            .all()
        )
        return r

    def get_tick_df(self, code: str, date_start: any, date_end: any) -> pd.DataFrame:
        model = self.get_tick_model(code)
        if not self.is_table_exsist(model):
            GLOG.WARN(f"Table Tick {code} not exsit. ")
            return pd.DataFrame()
        date_start = datetime_normalize(date_start)
        date_end = datetime_normalize(date_end)
        r = (
            CLICKDRIVER.session.query(model)
            .filter(model.code == code)
            .filter(model.timestamp >= date_start)
            .filter(model.timestamp <= date_end)
            .filter(model.isdel == False)
        )
        df = pd.read_sql(r.statement, CLICKDRIVER.engine)
        df = df.sort_values(by="timestamp", ascending=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def del_tick(self, code: str, date: any) -> None:
        # TODO
        pass

    def update_tick(self, code: str) -> None:
        # CreateTable
        model = self.get_tick_model(code)
        self.create_table(model)
        # Try get
        t0 = datetime.datetime.now()
        insert_count = 0
        tdx = GinkgoTDX()
        nodata_count = 0
        date = datetime.datetime.now()
        while True:
            # Break
            if nodata_count >= 50:
                break
            # Query database
            date_start = date.strftime("%Y%m%d")
            date_end = (date + datetime.timedelta(days=1)).strftime("%Y%m%d")
            GLOG.INFO(f"Trying to update {code} Tick on {date}")
            if self.is_tick_indb(code, date_start):
                GLOG.WARN(f"{code} Tick on {date} is in database. Go next")
                date = date + datetime.timedelta(days=-1)
                nodata_count = 0
                continue
            # Fetch and insert
            rs = tdx.fetch_history_transaction(code, date)
            if rs.shape[0] == 0:
                GLOG.WARN(f"{code} No data on {date} from remote.")
                nodata_count += 1
                date = date + datetime.timedelta(days=-1)
                continue

            # print(rs)
            l = []
            for i, r in rs.iterrows():
                # print(r)
                timestamp = f"{date.strftime('%Y-%m-%d')} {r.timestamp}:00"
                price = float(r.price)
                volume = int(r.volume)
                buyorsell = int(r.buyorsell)
                buyorsell = TICKDIRECTION_TYPES(buyorsell)
                item = model()
                item.set(code, price, volume, buyorsell, timestamp)
                l.append(item)
            self.add_all(l)
            self.commit()
            GLOG.INFO(f"Insert {code} Tick {len(l)}.")
            insert_count += len(l)
            nodata_count = 0
            # ReCheck
            if self.is_tick_indb(code, date_start):
                GLOG.INFO(f"{code} {date_start} Insert Recheck Successful.")
            else:
                GLOG.CRITICAL(
                    f"{code} {date_start} Insert Failed. Still no data in database."
                )
            date = date + datetime.timedelta(days=-1)
        t1 = datetime.datetime.now()
        GLOG.WARN(f"Updating Tick {code} complete. Cost: {t1-t0}")

    def update_all_cn_tick_aysnc(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        l = []
        cpu_count = multiprocessing.cpu_count()
        cpu_count = int(cpu_count * self.cpu_ratio)
        for i, r in info.iterrows():
            code = r["code"]
            l.append(code)

        p = multiprocessing.Pool(cpu_count)

        for code in l:
            res = p.apply_async(self.update_tick, args=(code,))

        p.close()
        p.join()
        t1 = datetime.datetime.now()
        GLOG.INFO(f"Update All CN Tick Done. Cost: {t1-t0}")

    # Daily Data update
    def update_stock_info(self) -> None:
        size = CLICKDRIVER.get_table_size(MStockInfo)
        GLOG.CRITICAL(f"Current Stock Info Size: {size}")
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
                GLOG.INFO(f"Update {q.code} stock info")
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
        insert_count += len(l)
        GLOG.DEBUG(f"Insert {len(l)} stock info.")
        t1 = datetime.datetime.now()
        GLOG.INFO(
            f"StockInfo Update: {update_count}, Insert: {insert_count} Cost: {t1-t0}"
        )
        size = CLICKDRIVER.get_table_size(MStockInfo)
        GLOG.CRITICAL(f"After Update Stock Info Size: {size}")

    def update_trade_calendar(self) -> None:
        """
        Update all Makets' Calendar
        """
        GLOG.INFO("Updating Trade Calendar")
        self.update_cn_trade_calendar()

    def update_cn_trade_calendar(self) -> None:
        GLOG.INFO("Updating CN Calendar.")
        size = CLICKDRIVER.get_table_size(MTradeDay)
        GLOG.CRITICAL(f"Current Trade Calendar Size: {size}")
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
            q = self.get_trade_calendar(market, date, date)
            # Check DB, if exist update
            if len(q) >= 1:
                if len(q) >= 2:
                    GLOG.CRITICAL(
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
                    self.commit()
                    GLOG.INFO(f"Update {item2.timestamp} {item2.market} TradeCalendar")

            if len(q) == 0:
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
        size = CLICKDRIVER.get_table_size(MTradeDay)
        GLOG.CRITICAL(f"After Update Trade Calendar Size: {size}")

    def update_cn_daybar(self, code: str) -> None:
        # Get the stock info of code
        t0 = datetime.datetime.now()
        info = self.get_stock_info(code)
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
        date_start = info.list_date
        date_end = info.delist_date
        today = datetime.datetime.now()
        if today < date_end:
            date_end = today

        missing_period = [
            [None, None],
        ]

        trade_calendar = self.get_trade_calendar_df(
            MARKET_TYPES.CHINA, date_start, date_end
        )
        trade_calendar = trade_calendar[trade_calendar["is_open"] == "true"]
        trade_calendar.sort_values(by="timestamp", inplace=True, ascending=True)
        trade_calendar = trade_calendar[trade_calendar["timestamp"] >= date_start]
        trade_calendar = trade_calendar[trade_calendar["timestamp"] <= date_end]

        df1 = trade_calendar["timestamp"]
        old_df = self.get_daybar_df(code)
        old_timestamp = old_df.timestamp.values if old_df.shape[0] > 0 else []
        # print(old_df["timestamp"])
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
        # for period in missing_period:
        #     print(period)
        for period in missing_period:
            if period[0] is None:
                break
            start = period[0]
            end = period[1]
            GLOG.INFO(f"Fetch {code} {info.code_name} from {start} to {end}")
            rs = tu.fetch_cn_stock_daybar(code, start, end)
            print(rs)
            # There is no data from date_start to date_end
            if rs.shape[0] == 0:
                GLOG.INFO(
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
        GLOG.INFO(
            f"Daybar {code} Update: {update_count} Insert: {insert_count} Cost: {t1-t0}"
        )

    def update_all_cn_daybar(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_cn_daybar(code)
        t1 = datetime.datetime.now()
        GLOG.INFO(f"Update ALL CN Daybar cost {t1-t0}")

    def update_all_cn_daybar_aysnc(self) -> None:
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
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
        GLOG.INFO(f"Update All CN Daybar Done. Cost: {t1-t0}")

    def update_cn_adjustfactor(self, code: str) -> None:
        t0 = datetime.datetime.now()
        tu = GinkgoTushare()
        df = tu.fetch_cn_stock_adjustfactor(code)
        insert_count = 0
        update_count = 0
        driver = GinkgoMysql(
            user=GCONF.MYSQLUSER,
            pwd=GCONF.MYSQLPWD,
            host=GCONF.MYSQLHOST,
            port=GCONF.MYSQLPORT,
            db=GCONF.MYSQLDB,
        )
        l = []
        for i, r in df.iterrows():
            code = r["ts_code"]
            date = datetime_normalize(r["trade_date"])
            factor = r["adj_factor"]
            print(f"AdjustFactor Check {date}  {code}", end="\r")
            # Check ad if exist in database
            q = self.get_adjustfactor(code, date, date, driver)
            # If exist, update
            if len(q) >= 1:
                if len(q) >= 2:
                    GLOG.CRITICAL(
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
                    print("==============")
                    print(f"code: {code}   db_code: {item.code}")
                    print(f"time: {date}   db_time: {item.timestamp}")
                    print(f"factor: {factor}   db_factor: {float(item.adjustfactor)}")
                    print("==============")
                    item.adjustfactor = factor
                    item.update = datetime.datetime.now()
                    update_count += 1
                    driver.session.commit()
                    GLOG.DEBUG(f"Update {code} {date} AdjustFactor")

            # If not exist, new insert
            if len(q) == 0:
                # Insert
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
        driver.session.add_all(l)
        driver.session.commit()
        insert_count += len(l)
        GLOG.DEBUG(f"Insert {len(l)} {code} AdjustFactor.")
        t1 = datetime.datetime.now()
        GLOG.INFO(
            f"AdjustFactor {code} Update: {update_count} Insert: {insert_count} Cost: {t1-t0}"
        )

    def update_all_cn_adjustfactor(self):
        GLOG.INFO(f"Begin to update all CN AdjustFactor")
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
        for i, r in info.iterrows():
            code = r["code"]
            self.update_cn_adjustfactor(code)
        t1 = datetime.datetime.now()
        GLOG.INFO(f"Update ALL CN AdjustFactor cost {t1-t0}")

    def update_all_cn_adjustfactor_aysnc(self):
        GLOG.INFO(f"Begin to update all cn adjust factors")
        t0 = datetime.datetime.now()
        info = self.get_stock_info_df()
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
        GLOG.INFO(f"Update ALL CN AdjustFactor cost {t1-t0}")
        size = MYSQLDRIVER.get_table_size(MAdjustfactor)
        GLOG.CRITICAL(f"After Update Adjustfactor Size: {size}")


GDATA = GinkgoData()
