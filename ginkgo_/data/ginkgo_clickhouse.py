"""
数据存储模块，负责与Clickhouse通信
"""
import pandas as pd
import tqdm
import datetime
import time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, MetaData, inspect, func
from sqlalchemy.orm import sessionmaker
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.stock.baostock_data import bao_instance as bi
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.day_bar import DayBar
from ginkgo.util.methdispatch import methdispatch


class GinkgoClickHouse(object):
    def __init__(self, host, port, username, password, database):
        self.engine = None
        self.session = None
        self.metadata = None
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database

        self.__connect()

        self.code_list_cache = None
        self.code_list_cache_last_update = None
        self.time_span_cache = {}
        # TODO Cach update

    # Connect to Docker
    def __connect(self):
        gl.logger.info("Tring to connect Clickhouse")
        uri = f"clickhouse+native://{self.username}:{self.password}@{self.host}/{self.database}"
        gl.logger.debug(f"CurrentTarget: {uri}")
        self.engine = create_engine(uri)
        self.session = sessionmaker(self.engine)()
        self.metadata = MetaData(bind=self.engine)
        gl.logger.info("Connect to clickhouse succeed.")

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        return self.insp.has_table(name)

    def insert_stockinfo(self) -> None:
        pass

    def del_stockinfo(self) -> None:
        # TODO
        pass

    # Update all stocks one by one
    def update_all_stockinfo(self) -> None:
        t0 = datetime.datetime.now()
        gl.logger.info("StockInfo Updating Start.")
        # Step1：通过Baostock获取所有指数代码
        result = bi.get_all_stock_code()
        # Step2：如果数据不为空进行持久化操作，反之报错
        if result.shape[0] == 0:
            gl.logger.error("股票指数代码获取为空，请检查代码或日期")
            return
        gl.logger.info("Updating StockInfo")
        gl.logger.info("Get Existing StockInfo.")
        old_df = self.get_stockinfo()
        rs_list = []
        pbar = tqdm.tqdm(total=result.shape[0])
        for i, r in result.iterrows():
            item = StockInfo(
                code=r["code"],
                trade_status=int(r["tradeStatus"]),
                code_name=r["code_name"],
            )
            pbar.update(1)
            pbar.set_description(f"Updating StockInfo {item.code}")
            records = old_df[old_df["code"] == item.code].sort_values(
                "create_time", ascending=False
            )
            if records.shape[0] == 0:
                rs_list.append(item)
            else:
                r0 = records.head(1)
                condition1 = r0["name"].values[0] == item.name
                condition2 = r0["trade_status"].values[0] == item.trade_status
                if condition1 & condition2:
                    continue
                else:
                    rs_list.append(item)
        self.session.add_all(rs_list)
        pbar.set_description("Dict Loaded.")
        self.session.commit()
        pbar.set_description("StockInfo Complete:)     ")
        pbar.close()
        t1 = datetime.datetime.now()
        time.sleep(0.2)
        gl.logger.info(
            f"StockInfo Update Complete. Update: {len(rs_list)}, Cost: {t1-t0}"
        )

    # Get StockInfo
    def get_stockinfo(self) -> pd.DataFrame:
        old_rs = self.session.query(StockInfo).filter()
        df = pd.read_sql(old_rs.statement, con=self.engine)
        if df.shape[0] > 0:
            df = df.drop(["uuid"], axis=1)
        return df[df["is_delete"] == False]

    # Get All Codes
    def get_codes(self) -> pd.DataFrame:
        rs = self.get_stockinfo()
        rs = rs[["code", "name"]]
        return rs

    def insert_adjustfactor(self) -> None:
        pass

    def insert_adjustfactor_async(self) -> None:
        pass

    def del_adjustfactor(self) -> None:
        pass

    def update_adjustfactor(self) -> None:
        pass

    def get_adjustfactor(self) -> None:
        pass

    def get_timespan(self, code: str) -> tuple:
        if code in self.time_span_cache.keys():
            return self.time_span_cache[code]
        df = self.get_daybar(code=code)
        start = datetime.datetime(1990, 1, 1)
        end = datetime.datetime(1990, 1, 1)
        try:
            start = df.iloc[0]["date"]
        except Exception as e:
            gl.logger.error(e)
        try:
            end = df.iloc[-1]["date"]
        except Exception as e:
            gl.logger.error(e)

        result = (start, end)
        self.time_span_cache[code] = result
        return result

    # Insert Daybar directly
    @methdispatch
    def insert_daybar(self, daybar) -> None:
        gl.logger.error(
            "Daybar insert only support <Daybar> List<Daybar> and DataFrame. Please check your code."
        )

    @insert_daybar.register(DayBar)
    def _(self, daybar):
        code = daybar.code
        date_start = self.get_timespan(code)[0]
        date_end = self.get_timespan(code)[1]
        date = daybar.date
        if date < date_start or date > date_end:
            self.session.add(daybar)
            self.session.commit()
            gl.logger.debug(f"Insert Daybar via <DayBar>{date}:{code}")
        self.time_span_cache.pop(code)

    @insert_daybar.register(list)
    def _(self, daybar):
        code = daybar[0].code
        l = []
        for i in daybar:
            if isinstance(i, DayBar):
                if i.code != code:
                    continue
                date_start = self.get_timespan(i.code)[0]
                date_end = self.get_timespan(i.code)[1]
                if i.date < date_start or i.date > date_end:
                    l.append(i)
            else:
                gl.logger.error(
                    "Daybar insert via List<Daybar>, the atom of list should be DayBar"
                )
                return
        self.session.add_all(l)
        self.session.commit()
        self.time_span_cache.pop(code)
        gl.logger.debug(f"Insert Daybar via List<DayBar>: {len(l)}")

    @insert_daybar.register(pd.DataFrame)
    def _(self, daybar):
        code = daybar.iloc[0]["code"]
        l = []
        for i, r in daybar.iterrows():
            if r["code"] != code:
                continue
            date_start = self.get_timespan(r["code"])[0]
            date_end = self.get_timespan(r["code"])[1]
            if r["date"] < date_start or r["date"] > date_end:
                item = DayBar()
                item.df_convert(r)
                l.append(item)
        self.session.add_all(l)
        self.session.commit()
        self.time_span_cache.pop(code)
        gl.logger.debug(f"Insert Daybar via DataFrame: {len(l)}")

    # Insert Daybar with date & code check
    def insert_daybar_strict(self, daybar: DayBar) -> None:
        code = daybar.code
        date = daybar.date
        rs = self.get_daybar(code=code, date_start=date, date_end=date)
        if rs.shape[0] == 0:
            self.session.add(daybar)
            self.session.commit()
            gl.logger.debug(f"Insert {date}:{code}")
        else:
            gl.logger.warn(f"{date}:{code} data exists.")

    # Get Daybars by code via BaoStock
    def get_daybars_by_bao(self, code: str) -> pd.DataFrame:
        end = datetime.datetime.now()
        end_str = datetime.datetime.strftime(end, "%Y-%m-%d")
        df = bi.get_data(code=code, data_frequency="d", end_date=end_str)
        return df

    def del_daybar(self, code: str, date: datetime.datetime) -> None:
        q = (
            self.session.query(DayBar)
            .filter(DayBar.code == code)
            .filter(DayBar.date == date)
            .order_by(DayBar.date.asc())
            .all()
        )
        for i in q:
            i.is_delete = True
            self.session.commit()

    def update_daybar(self, code: str) -> None:
        # TODO
        old_df = self.get_daybar(code=code)
        print(old_df["date"])

    def get_daybar(self, code: str, date_start=None, date_end=None) -> pd.DataFrame:
        t0 = datetime.datetime.now()
        if date_start is None:
            # Set a default to start date
            date_start = datetime.datetime(1990, 1, 1)
        elif isinstance(date_start, str):
            # If date_start is str, try convert
            # Support 2 Format
            try:
                date_start = datetime.datetime.strptime(date_start, "%Y-%m-%d")
            except Exception as e:
                date_start = datetime.datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
        elif not isinstance(date_start, datetime.datetime):
            gl.logger.error("Param Date only can be str or datetime")
            return

        if date_end is None:
            # Set a default to end date
            date_end = datetime.datetime.now()
        elif isinstance(date_end, str):
            try:
                date_end = datetime.datetime.strptime(date_end, "%Y-%m-%d")
            except Exception as e:
                date_end = datetime.datetime.strptime(date_end, "%Y-%m-%d %H:%M:%S")
        elif not isinstance(date_end, datetime.datetime):
            gl.logger.error("Param Date only can be str or datetime")
            return

        rs = (
            self.session.query(DayBar)
            .filter(DayBar.code == code)
            .filter(DayBar.date >= date_start)
            .filter(DayBar.date <= date_end)
            .order_by(DayBar.date.asc())
        )
        df = pd.read_sql(rs.statement, con=self.engine)
        ## TODO remove deuplicated
        t1 = datetime.datetime.now()
        return df[df["is_delete"] == False]

    def update_all_daybar(self) -> None:
        # 1 GetAllCode
        t0 = datetime.datetime.now()
        code_list = self.get_codes()
        # 2 Get Data by Code
        pbar = tqdm.tqdm(total=code_list.shape[0])
        for i, r in code_list.iterrows():
            code = r["code"]
            name = r["name"]
            pbar.update(1)
            pbar.set_description(f"Updating DayBar {code} {name}")
            df = self.get_daybars_by_bao(code)
            if df is None:
                continue
            float_list = [
                "open",
                "high",
                "low",
                "close",
                "preclose",
                "volume",
                "amount",
                "turn",
                "pctChg",
            ]
            int_list = [
                "adjustflag",
                "tradestatus",
                "isST",
            ]
            df[float_list] = df[float_list].fillna(value=0.0)
            df[float_list] = df[float_list].astype(float)
            df[int_list] = df[int_list].fillna(value=0)
            df[int_list] = df[int_list].astype(int)
            l = []
            for k, j in df.iterrows():
                item = DayBar()
                item.date = datetime.datetime.strptime(j["date"], "%Y-%m-%d")
                item.code = code
                item.name = name
                item.open_ = j["open"]
                item.high = j["high"]
                item.low = j["low"]
                item.close = j["close"]
                item.preclose = j["preclose"]
                item.volume = j["volume"]
                item.amount = j["amount"]
                item.adjust_flag = j["adjustflag"]
                item.turn = j["turn"]
                item.trade_status = j["tradestatus"]
                item.pct_change = j["pctChg"]
                item.is_st = j["isST"]
                l.append(item)
            self.session.add_all(l)
            self.session.commit()
        pbar.set_description("Daybar Complete:)     ")
        pbar.close()
        t1 = datetime.datetime.now()
        time.sleep(0.2)
        gl.logger.info(
            f"Daybar Update Complete. Update: {code_list.shape[0]}, Cost: {t1-t0}"
        )

    def insert_min5(self) -> None:
        pass

    def insert_min5_async(self) -> None:
        pass

    def del_min5(self) -> None:
        pass

    def update_min5(self) -> None:
        pass

    def get_min5(self) -> None:
        pass

    def get_last_trade_day(self) -> None:
        pass

    def get_last_trade_time(self) -> None:
        pass

    def set_nomin5(self) -> None:
        pass

    def has_min5(self) -> bool:
        pass

    def get_trade_day(self) -> bool:
        pass

    def get_df_norepeat(self) -> pd.DataFrame:
        pass

    def query_stock(self) -> None:
        pass


ginkgo_clickhouse = GinkgoClickHouse(
    host=HOST, port=PORT, username=USERNAME, password=PASSWORD, database=DATABASE
)
