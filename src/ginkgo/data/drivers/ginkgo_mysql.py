from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoMysql(object):
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
        uri = f"mysql+pymysql://{self._user}:{self._pwd}@{self._host}:{self._port}/{self._db}"

        self._engine = create_engine(
            uri,
            # pool_size=10,
            # pool_timeout=10,
            # max_overflow=5,
            # echo=True,
        )
        self._session = sessionmaker(self.engine)()
        self._metadata = MetaData(bind=self.engine)
        # self.base = declarative_base(metadata=self.metadata)
        self._base = declarative_base()
        GLOG.DEBUG("Connect to mysql succeed.")

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        GLOG.DEBUG(f"Check Mysql table {name} exsists. {self.insp.has_table(name)}")
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        count = self.session.query(model).count()
        return count
