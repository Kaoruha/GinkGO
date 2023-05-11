import inspect
import datetime
import importlib
import pandas as pd
from ginkgo.data import DBDRIVER
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.models import MCodeOnTrade, MOrder, MBase
from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES
from ginkgo.data import GinkgoBaoStock
from ginkgo.libs.ginkgo_normalize import datetime_normalize


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
            gl.logger.warn(f"Drop Table {model.__tablename__} : {model}")

    def create_table(self, model: MBase) -> None:
        if model.__abstract__ == True:
            gl.logger.debug(f"Pass Model:{model}")
            return
        if DBDRIVER.is_table_exsists(model.__tablename__):
            gl.logger.debug(f"Table {model.__tablename__} exist.")
        else:
            model.__table__.create()
            gl.logger.info(f"Create Table {model.__tablename__} : {model}")

    def get_table_size(self, model: MBase) -> int:
        return DBDRIVER.get_table_size(model)

    def get_order(self, order_id: str) -> MOrder:
        r = self.session.query(MOrder).filter(MOrder.uuid == order_id).first()
        r.code = r.code.strip(b"\x00".decode())
        return r

    # CodeListOnTrade
    def get_cn_codelist_lastdate(self) -> datetime.datetime:
        r = (
            self.session.query(MCodeOnTrade)
            .filter(MCodeOnTrade.market == MARKET_TYPES.CHINA)
            .order_by(MCodeOnTrade.timestamp.desc())
            .first()
        )
        if r is None:
            return datetime_normalize("1990-12-15")
        else:
            return r.timestamp

    def get_codelist(
        self, date: str or datetime.datetime, market: MARKET_TYPES
    ) -> pd.DataFrame:
        date = datetime_normalize(date)
        yesterday = date + datetime.timedelta(hours=-12)
        tomorrow = date + datetime.timedelta(hours=12)
        r = (
            self.session.query(MCodeOnTrade)
            .filter(MCodeOnTrade.market == market)
            .filter(MCodeOnTrade.timestamp > yesterday)
            .filter(MCodeOnTrade.timestamp <= tomorrow)
            .all()
        )
        if len(r) == 0:
            return
        l = []
        for i in r:
            l.append(i.to_dataframe())
        df = pd.DataFrame(l)
        return df

    def insert_codelist(self, df: pd.DataFrame) -> None:
        rs = []
        for i, r in df.iterrows():
            item = MCodeOnTrade()
            item.set(r)
            rs.append(item)
        self.add_all(rs)
        self.commit()

    def update_cn_codelist(self, date: str or datetime.datetime) -> None:
        date = datetime_normalize(date)
        # 0 Check data in database
        rs = self.get_codelist(date, MARKET_TYPES.CHINA)
        if rs is not None:
            gl.logger.debug(f"CodeList on {date} exist. No need to update.")
            return

        # 1. Get Code List From Bao
        rs: pd.DataFrame = self.bs.fetch_cn_stock_list(date)
        if rs.shape[0] == 0:
            return

        # 2. Set up list(ModelCodeOntrade)
        data = []
        date = str(date.date())
        rs["tmp"] = None
        rs.loc[rs["trade_status"] == "1", "tmp"] = True
        rs.loc[rs["trade_status"] == "0", "tmp"] = False
        rs = rs.drop(["trade_status"], axis=1)
        rs = rs.rename(columns={"tmp": "trade_status"})
        for i, r in rs.iterrows():
            m = MCodeOnTrade()
            m.set_source(SOURCE_TYPES.BAOSTOCK)
            m.set(
                r["code"],
                r["code_name"],
                r["trade_status"],
                MARKET_TYPES.CHINA,
                date,
            )
            data.append(m)

        # 3. insert_code_list()
        self.add_all(data)
        self.commit()
        gl.logger.info(f"Insert {date} CodeList {len(data)} rows.")

    def update_cn_codelist_period(
        self, start: str or datetime.datetime, end: str or datetime.datetime
    ) -> None:
        start = datetime_normalize(start)
        end = datetime_normalize(end)
        current = start
        while current <= end:
            self.update_cn_codelist(current)
            current = current + datetime.timedelta(days=1)

    def update_cn_codelist_to_latest_entire(self):
        start = "1990-12-15"
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.update_cn_code_list_period(start, today)

    def update_cn_codelist_to_latest_fast(self):
        start = self.get_cn_codelist_lastdate()
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.update_cn_code_list_period(start, today)

    # Daybar

    def get_cn_daybar_lastdate(self):
        pass

    def get_daybar(self, code, code_name, date):
        pass

    def insert_daybar(self, df: pd.DataFrame):
        pass

    def update_cn_daybar(self, code, code_name, date):
        pass

    def update_cn_daybar_to_latest_entire(self):
        pass

    def update_cn_daybar_to_latest_fast(self):
        pass

    def update_cn_daybar_to_latest_entire_async(self):
        pass

    def update_cn_daybar_to_latest_fast_async(self):
        pass

    # Min5

    def get_cn_min5_lastdate(self):
        pass

    def get_min5(self, code, code_name, date):
        pass

    def insert_min5(self, df: pd.DataFrame):
        pass

    def update_cn_min5(self, code, code_name, date):
        pass

    def update_cn_min5_to_latest_entire_async(self):
        pass

    def update_cn_min5_to_latest_fast_async(self):
        pass

    # Adjustfactor

    def get_cn_adjustfactor_lastdate(self):
        pass

    def get_adjustfactor(self, code, code_name, date):
        pass

    def insert_adjustfactor(self, df: pd.DataFrame):
        pass

    def update_cn_adjustfactor(self, code, code_name, date):
        pass

    def update_cn_adjustfactor_to_latest_entire(self):
        pass

    def update_cn_adjustfactor_to_latest_fast(self):
        pass


GINKGODATA = GinkgoData()
