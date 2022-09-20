"""
数据存储模块，负责与Clickhouse通信
"""
import pandas as pd
import tqdm
import datetime
import time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.stock.baostock_data import bao_instance as bi
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD
from ginkgo.data.models.stock_info import StockInfo
from ginkgo.data.models.day_bar import DayBar


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

    def get_stockinfo(self) -> pd.DataFrame:
        old_rs = self.session.query(StockInfo).filter()
        df = pd.read_sql(old_rs.statement, con=self.engine)
        if df.shape[0] > 0:
            df = df.drop(["uuid"], axis=1)
        # df.drop_duplicates(
        #     subset=["code", "name", "trade_status", "has_min5"], inplace=True
        # )
        return df[df["is_delete"] == False]

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

    def insert_daybars(self, daybars: list) -> None:
        count = 0
        for i in daybars:
            old = self.get_daybar(code=i.code, date_start=i.date, date_end=i.date)
            if old.count() == 0:
                self.session.add(i)
                count += 1
            else:
                self.update_daybar(i)
        self.session.commit()

    def get_daybars_by_bao(self, code: str) -> pd.DataFrame:
        end = datetime.datetime.now()
        end_str = datetime.datetime.strftime(end, "%Y-%m-%d")
        df = bi.get_data(code=code, data_frequency="d", end_date=end_str)
        return df

    def del_daybar(self, code: str, date: datetime.datetime) -> None:
        pass

    def update_daybar(self, daybar: DayBar) -> None:
        pass

    def get_daybar(self, code: str, date_start: str, date_end: str) -> None:
        date_start = datetime.datetime.strptime(date_start, "%Y-%m-%d")
        date_end = datetime.datetime.strptime(date_end, "%Y-%m-%d")
        rs = (
            self.session.query(DayBar)
            .filter(DayBar.code == code)
            .filter(DayBar.date >= date_start)
            .filter(DayBar.date <= date_end)
        )
        return rs

    def update_all_daybar(self) -> None:
        # 1 GetAllCode
        t0 = datetime.datetime.now()
        code_list = self.get_codes()
        print(code_list)
        # 2 Get Data by Code
        pbar = tqdm.tqdm(total=code_list.shape[0])
        for i, r in code_list.iterrows():
            code = r["code"]
            name = r["name"]
            pbar.update(1)
            pbar.set_description(f"Updating DayBar {code} {name}")
            df = self.get_daybars_by_bao(code)
            print("==" * 20)
            print(df)
            print(df is None)
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
