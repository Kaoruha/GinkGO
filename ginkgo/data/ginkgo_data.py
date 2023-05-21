import inspect
import time
import datetime
import os
import pandas as pd
import multiprocessing
import threading
from ginkgo.data import DBDRIVER
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs import datetime_normalize
from ginkgo.data.models import MCodeOnTrade, MOrder, MBase, MBar
from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES, FREQUENCY_TYPES
from ginkgo.data import GinkgoBaoStock
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.libs.ginkgo_conf import GINKGOCONF
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
            .filter(MCodeOnTrade.timestamp >= yesterday)
            .filter(MCodeOnTrade.timestamp < tomorrow)
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

    def update_cn_codelist(self, date: str or datetime.datetime, session=None) -> None:
        # 0 Check data in database
        date = datetime_normalize(date)
        yesterday = date + datetime.timedelta(hours=-12)
        tomorrow = date + datetime.timedelta(hours=12)

        # Support Multiprocessing
        # Sqlalchemy has some problem when multi process visit.
        # Sometimes the session will be wrong. THat can not get the right result.
        # So the When running async, each process will hava a sqlalchemy instance. Or will use self.session
        my_session = self.session
        if session:
            my_session = session

        result = (
            my_session.query(MCodeOnTrade)
            .filter(MCodeOnTrade.market == MARKET_TYPES.CHINA)
            .filter(MCodeOnTrade.timestamp >= yesterday)
            .filter(MCodeOnTrade.timestamp < tomorrow)
            .first()
        )
        gl.logger.info(f"In Process {os.getpid()} {date}")

        if result:
            gl.logger.warn(f"CodeList on {date} exist. No need to update.")
            return

        # 1. Get Code List From Bao
        df: pd.DataFrame = self.bs.fetch_cn_stock_list(date)
        gl.logger.debug(f"Try get code list on {date}")
        if df.shape[0] == 0:
            gl.logger.debug(f"{date} has no codelist. Return...")
            return

        gl.logger.critical(f"Remote has Date:{date} >={yesterday} < {tomorrow}")
        # 2. Set up list(ModelCodeOntrade)
        data = []
        date = str(date.date())
        gl.logger.debug(f"Check the date again {date}")
        df["tmp"] = None
        df.loc[df["trade_status"] == "1", "tmp"] = True
        df.loc[df["trade_status"] == "0", "tmp"] = False
        df = df.drop(["trade_status"], axis=1)
        df = df.rename(columns={"tmp": "trade_status"})
        for i, r in df.iterrows():
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
        my_session.add_all(data)
        my_session.commit()
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

    def update_cn_codelist_to_latest_entire(self) -> None:
        start = "1990-12-15"
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.update_cn_codelist_period(start, today)

    def update_cn_codelist_to_latest_fast(self) -> None:
        start = self.get_cn_codelist_lastdate()
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.update_cn_codelist_period(start, today)

    def update_cn_codelist_async_worker(
        self,
        todo_queue: multiprocessing.Queue,
        done_queue: multiprocessing.Queue,
    ) -> None:
        gl.logger.info(f"Start Worker PID:{os.getpid()}")
        retry_count = 0
        retry_limit = 5

        DB = GinkgoClickhouse(
            user=GINKGOCONF.CLICKUSER,
            pwd=GINKGOCONF.CLICKPWD,
            host=GINKGOCONF.CLICKHOST,
            port=GINKGOCONF.CLICKPORT,
            db=GINKGOCONF.CLICKDB,
        )

        while True:
            try:
                date = todo_queue.get(block=False, timeout=1)
                self.update_cn_codelist(date, DB.session)
                retry_count = 0
            except Exception as e:
                retry_count += 1
                gl.logger.warn(f"WorkerUpdateCode Retry: {retry_count}")
                time.sleep(0.5)
                if retry_count >= retry_limit:
                    break
            # time.sleep(0.001)
        gl.logger.info(f"WorkerUpdateCode: {os.getpid()} Complete.")

    def update_cn_codelist_to_latest_entire_async(self) -> None:
        start = datetime_normalize("1990-12-18")
        now = datetime.datetime.now()

        cpu_count = multiprocessing.cpu_count()
        worker_count = int(cpu_count * 1)
        todo_queue = multiprocessing.Queue()
        done_queue = multiprocessing.Queue()
        pool = []
        while start <= now:
            start += datetime.timedelta(days=1)
            todo_queue.put(start)

        gl.logger.info(f"Updating Code List with {worker_count} Worker.")

        # Threading

        # for i in range(worker_count):
        #     t = threading.Thread(
        #         target=self.update_cn_codelist_async_worker,
        #         args=(
        #             todo_queue,
        #             done_queue,
        #         ),
        #         daemon=True,
        #     )
        #     t.start()
        #     pool.append(t)
        # for t in pool:
        #     t.join()

        # Multiprocessing

        for i in range(worker_count):
            p = multiprocessing.Process(
                target=self.update_cn_codelist_async_worker,
                args=(
                    todo_queue,
                    done_queue,
                ),
            )
            p.start()
            pool.append(p)

        for p in pool:
            p.join()

    # Bar

    def get_bar_lastdate(
        self, code: str, frequency: FREQUENCY_TYPES
    ) -> datetime.datetime:
        r = (
            self.session.query(MBar)
            .filter(MBar.code == code)
            .filter(MBar.frequency == frequency)
            .order_by(MBar.timestamp.desc())
            .first()
        )
        if r is None:
            return datetime_normalize("1990-12-15")
        else:
            return r.timestamp

    def get_bar(
        self,
        code: str,
        start_date: str or datetime.datetime,
        end_date: str or datetime.datetime,
        frequency: FREQUENCY_TYPES,
        adjust: int = 1,
    ) -> pd.DataFrame:
        """
        filter with code primary.
        """
        start_date = datetime_normalize(start_date)
        end_date = datetime_normalize(end_date)
        r = (
            self.session.query(MBar)
            .filter(MBar.code == code)
            .filter(MBar.timestamp >= start_date)
            .filter(MBar.timestamp <= end_date)
            .all()
        )
        if len(r) == 0:
            return
        l = []
        for i in r:
            l.append(i.to_dataframe())
        df = pd.DataFrame(l)
        # TODO Do Adjust cal
        return df

    def insert_bar(self, df: pd.DataFrame) -> None:
        """
        Insert Bar record into Database.
        Will check the date code and frequency to avoid insert the duplicate record.
        """
        rs = []
        cache = []

        for i, r in df.iterrows():
            # Set Model Bar
            item = MBar()
            item.set(r)
            item.set_source(SOURCE_TYPES.BAOSTOCK)

            # Get the latest date of bar in database
            latest = self.get_bar_lastdate(item.code, item.frequency)

            # Gen a key with new Bar code + date + frequency_type
            key = (
                item.code
                + item.timestamp.strftime("%Y-%m-%d")
                + "f"
                + str(item.frequency)
            )

            # If the model is already in cache, go next
            if key in cache:
                gl.logger.debug(
                    f"{FREQUENCY_TYPES(item.frequency)} {item.code} on {item.timestamp} already exist in insert list."
                )
                continue

            # If the new Bar is after the latest date in db, append it to tobeinsert list and cache list.
            if item.timestamp > latest:
                rs.append(item)
                cache.append(key)
            else:
                # Try get the data with the same code date and frequency
                old = self.get_bar(
                    item.code, item.timestamp, item.timestamp, item.frequency
                )
                # If there is no record in database, add the model to insert list.
                if old is None:
                    rs.append(item)
                    cache.append(key)
                else:
                    gl.logger.debug(
                        f"{FREQUENCY_TYPES(item.frequency)} {item.code} on {item.timestamp} already exist in database."
                    )
                    continue

        self.add_all(rs)
        self.commit()

    def update_bar_to_latest(
        self,
        code: str,
        frequency: FREQUENCY_TYPES,
        start_date: str or datetime.datetime,
        session=None,
        bao=None,
    ):
        start_date = datetime_normalize(start_date)
        today = datetime.datetime.now()

        if start_date > today:
            return

        end_date = start_date + datetime.timedelta(days=3000)

        if end_date > today:
            end_date = today

        end_date = end_date.strftime("%Y-%m-%d")

        gl.logger.info(f"Updating {code} FROM {start_date} to {end_date}")

        # Support Multiprocessing
        my_session = self.session
        if session:
            my_session = session

        bs = self.bs
        if bao:
            bs = bao

        gl.logger.critical(f"=============================")
        gl.logger.critical(f"============================")
        try:
            gl.logger.critical(f"==========================")
            gl.logger.debug(f"Trying to get {code} from {start_date} to {end_date}")
            if frequency == FREQUENCY_TYPES.DAY:
                df = bs.fetch_cn_stock_daybar(code, start_date, end_date)
            else:
                # TODO Deal with other type of bars
                gl.logger.critical("TODO support other type bars")
                df = bs.fetch_cn_stock_daybar(code, start_date, end_date)
            gl.logger.critical(f"=========================")
        except Exception as e:
            print(e)
            print(type(e))

        print(df.shape[0])

        gl.logger.critical(f"{start_date} -- {end_date}")
        data = []
        latest = self.get_bar_lastdate(code, frequency)
        for i, r in df.iterrows():
            if datetime_normalize(r.date) <= latest:
                continue

            old = self.get_bar(code, r.date, r.date, frequency)
            if old:
                continue

            item = MBar()
            item.set(
                r.code,
                r.open,
                r.high,
                r.low,
                r.close,
                r.volume,
                FREQUENCY_TYPES.DAY,
                r.date,
            )
            item.set_source(SOURCE_TYPES.BAOSTOCK)
            data.append(item)

        my_session.add_all(data)
        my_session.commit()
        gl.logger.critical(
            f"Insert {code} Daybar {start_date} -- {end_date}  {len(data)} rows."
        )

        if df.shape[0] >= 500:
            self.update_bar_to_latest(code, frequency, end_date, session)

    def update_bar_async_worker(
        self,
        todo_queue: multiprocessing.Queue,
        done_queue: multiprocessing.Queue,
        start_date: str or datetime.datetime,
    ):
        gl.logger.info(f"Start Worker PID:{os.getpid()}")
        retry_count = 0
        retry_limit = 4
        while True:
            try:
                code = todo_queue.get(block=False, timeout=1)
                DB = GinkgoClickhouse(
                    user=GINKGOCONF.CLICKUSER,
                    pwd=GINKGOCONF.CLICKPWD,
                    host=GINKGOCONF.CLICKHOST,
                    port=GINKGOCONF.CLICKPORT,
                    db=GINKGOCONF.CLICKDB,
                )
                BS = GinkgoBaoStock()
                gl.logger.critical(f"Worker start updating {code}")
                self.update_bar_to_latest(
                    code, FREQUENCY_TYPES.DAY, start_date, DB.session, BS
                )
                gl.logger.critical(f"Worker Finished One {code}")

                retry_count = 0

            except Exception as e:
                retry_count += 1
                gl.logger.warn(f"WorkerUpdateBar Retry: {retry_count}")
                time.sleep(0.5)
                if retry_count >= retry_limit:
                    break
        gl.logger.info(f"WorkerUpdateBar: {os.getpid()} Complete.")

    def update_bar_to_latest_entire_async(self):
        # Prepare the async moduel
        cpu_count = multiprocessing.cpu_count()
        worker_count = int(cpu_count * 1)
        worker_count = 1
        # Get Trade day
        trade_day = self.bs.fetch_cn_stock_trade_day()
        trade_day = trade_day[trade_day["is_trading_day"] == "1"]
        # trade_day = trade_day.iloc[3200:, :]
        updated_dict = {}
        # Get CodeList from start to end
        update_count = 0
        m = multiprocessing.Manager()
        todo_queue = m.Queue()
        done_queue = m.Queue()
        for i, day in trade_day.iterrows():
            pool = []
            date = day["timestamp"]
            code_list = self.get_codelist(date, MARKET_TYPES.CHINA)
            if code_list is None:
                gl.logger.warn(
                    f"{date} get no code from database, please check your table."
                )
                continue

            for i2, r2 in code_list.iterrows():
                code = r2.code
                # Skip bj
                if code.startswith("bj.", 0, 3):
                    continue

                # Check if done update this time
                if code in updated_dict.keys():
                    if datetime_normalize(date) <= updated_dict[code]:
                        gl.logger.debug(f"{date} {code} already updated.")
                        continue

                latest = self.get_bar_lastdate(code, FREQUENCY_TYPES.DAY)
                gl.logger.debug(f"{code} latest in db is {latest}")
                if latest <= datetime_normalize(date):
                    todo_queue.put(code)
                else:
                    updated_dict[code] = latest
                    gl.logger.warn(f"{code} in db {latest} is new than {date}")

            if todo_queue.qsize() == 0:
                gl.logger.debug(f"{date} no code need update.")
                continue

            update_count += todo_queue.qsize()
            gl.logger.info(f"Updating Code List with {worker_count} Worker.")
            gl.logger.warn(f"Updated {update_count} times.")

            # Multiprocessing
            for index in range(worker_count):
                p = multiprocessing.Process(
                    target=self.update_bar_async_worker,
                    args=(
                        todo_queue,
                        done_queue,
                        date,
                    ),
                )
                p.start()
                pool.append(p)

            for p in pool:
                p.join()

            # for i in range(worker_count):
            #     t = threading.Thread(
            #         target=self.update_bar_async_worker,
            #         args=(
            #             todo_queue,
            #             done_queue,
            #             date,
            #         ),
            #         daemon=True,
            #     )
            #     t.start()
            #     pool.append(t)
            # for t in pool:
            #     t.join()

            # gl.logger.critical("Next Day.")
            time.sleep(1)


GINKGODATA = GinkgoData()
