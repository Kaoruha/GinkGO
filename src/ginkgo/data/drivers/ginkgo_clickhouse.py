from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoClickhouse(object):
    def __init__(self, user: str, pwd: str, host: str, port: int, db: str):
        self._engine = None
        self._session = None
        self._metadata = None
        self._base = None
        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db

    @property
    def engine(self):
        if self._engine is None:
            self.connect()
        return self._engine

    @property
    def session(self):
        if self._session is None:
            self.connect()
        return self._session

    @property
    def metadata(self):
        if self._metadata is None:
            self.connect()
        return self._metadata

    @property
    def base(self):
        if self._base is None:
            self.connect()
        return self._base

    def connect(self) -> None:
        uri = f"clickhouse://{self._user}:{self._pwd}@{self._host}:{self._port}/{self._db}"
        self._engine = create_engine(uri)
        self._session = sessionmaker(self.engine)()
        self._metadata = MetaData(bind=self.engine)
        self._base = declarative_base(metadata=self.metadata)
        GLOG.DEBUG("Connect to clickhouse succeed.")

    def __create_database(self) -> None:
        # ATTENTION DDL will run the sql, be care of COMMAND INJECTION
        uri = f"clickhouse://{self._user}:{self._pwd}@{self._host}:{self._port}/default"
        e = create_engine(uri)
        e.execute(
            DDL(
                f"CREATE DATABASE IF NOT EXISTS {self._db} ENGINE = Memory COMMENT 'For Ginkgo Quant'"
            )
        )
        GLOG.DEBUG(f"Create database {self._db} succeed.")

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        GLOG.DEBUG(
            f"Check Clickhouse table {name} exsists. {self.insp.has_table(name)}"
        )
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        GLOG.DEBUG("Try get Clickhouse table {model.__tablename__} size.")
        count = self.session.query(func.count(model.uuid)).scalar()
        GLOG.DEBUG(f"Clickhouse Table {model} size is {count}")
        return count
