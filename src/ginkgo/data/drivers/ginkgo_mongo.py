# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: GinkgoMongo MongoDB驱动提供MongoDB连接和文档操作支持文档存储支持交易系统功能






from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ginkgo.libs import GLOG, GinkgoLogger

data_logger = GinkgoLogger("ginkgo_data", ["ginkgo_data.log"])


class GinkgoMongo(object):
    def __init__(self, user: str, pwd: str, host: str, port: str, db: str) -> None:
        self._engine = None
        self._session = None
        self._metadata = None
        self._base = None
        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._max_try = 5

    @property
    def max_try(self) -> int:
        return self._max_try

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
        if self._engine is not None:
            self._engine.dispose()
        uri = f""
        self._engine = create_engine(uri)
        self._session = sessionmaker(self.engine)()
        self._metadata = MetaData(bind=self._engine)
        self._base = declarative_base(metadata=self.metadata)
        GLOG.DEBUG("Connect to mongo succeed.")

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exists(self, name: str) -> bool:
        GLOG.DEBUG(f"Check Mongo table {name} exists. {self.insp.has_table(name)}")
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        GLOG.DEBUG(f"Try get Mongo table {model.__tablename__} size.")
        count = self.session.query(func.count(model.uuid)).scalar()
        GLOG.DEBUG(f"Mongo table {model} size is {count}")
        return count
