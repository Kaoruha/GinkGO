import time
from sqlalchemy import create_engine, MetaData, inspect, func, DDL, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from ginkgo.libs.ginkgo_logger import GLOG, GinkgoLogger


class GinkgoMysql(object):
    def __init__(self, user: str, pwd: str, host: str, port: str, db: str) -> None:
        self._engine = None
        self._session = None
        self._metadata = None
        self._session_factory = None
        self._base = None
        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._max_try = 5
        self.SessionCLS = None

    @property
    def max_try(self) -> int:
        """
        Returns:
            Max try count for connect with db.
        """
        return self._max_try

    @property
    def engine(self):
        """
        Returns:
            DB Engine.
        """
        if self._engine is None:
            self.connect()
        return self._engine

    @property
    def session(self):
        """
        Returns:
            DB Session.
        """
        if self.SessionCLS is None:
            self.connect()
        return self.SessionCLS()

    def close_session(self):
        if self._session is not None:
            self.SessionCLS.remove()  # 清除当前线程的 Session 实例

    @property
    def metadata(self):
        """
        Returns:
            DB Metadata.
        """
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
        uri = f"mysql+pymysql://{self._user}:{self._pwd}@{self._host}:{self._port}/{self._db}"

        for i in range(self.max_try):
            try:
                self._engine = create_engine(
                    uri,
                    pool_recycle=3600,
                    pool_size=10,
                    pool_timeout=20,
                    max_overflow=10,
                    # echo=True,
                )
                self._metadata = MetaData(bind=self.engine)
                # self.base = declarative_base(metadata=self.metadata)
                self._base = declarative_base()
                self._session_factory = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine,
                )

                self.SessionCLS = scoped_session(self._session_factory)
                GLOG.DEBUG("Connect to mysql succeed.")
            except Exception as e:
                print(e)
                GLOG.DEBUG(f"Connect Mysql Failed {i+1}/{self.maxty} times.")
                time.sleep(2 * (i + 1))

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        """
        Check the exsistence of table.
        Args:
            name(str): table name
        Returns:
            Weather the table exsist.
        """
        GLOG.DEBUG(f"Check Mysql table {name} exsists. {self.insp.has_table(name)}")
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        """
        Get size of table.
        Args:
            model(Model): Data Model
        Returns:
            Count of table size.
        """
        GLOG.DEBUG(f"Get Mysql table {model.__tablename__} size.")
        query = text(f"SELECT COUNT(*) AS row_count FROM {model.__tablename__}")
        with self.session.begin():
            result = self.session.execute(query)
            row_count = result.scalar()
        return row_count
