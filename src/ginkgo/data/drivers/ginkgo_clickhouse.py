import time
from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoClickhouse(object):
    def __init__(self, user: str, pwd: str, host: str, port: int, db: str):
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
        if self._session is None:
            self._session = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine,
                )
            )
        return self._session

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
        """
        Returns:
            base of db connection.
        """
        if self._base is None:
            self.connect()
        return self._base

    def connect(self) -> None:
        """
        Connect with database.
        Returns:
            None
        """
        if self._engine is not None:
            self._engine.dispose()
        uri = f"clickhouse://{self._user}:{self._pwd}@{self._host}:{self._port}/{self._db}"
        for i in range(self.max_try):
            try:
                self._engine = create_engine(
                    uri,
                    pool_recycle=3600,
                    pool_size=10,
                    pool_timeout=20,
                    max_overflow=10,
                )
                self._metadata = MetaData(bind=self.engine)
                self._base = declarative_base(metadata=self.metadata)
                GLOG.DEBUG("Connect to clickhouse succeed.")
                return
            except Exception as e:
                print(e)
                GLOG.DEBUG(f"Connect Clickhouse Failed {i+1}/{self.max_try} times.")
                time.sleep(2 * (i + 1))

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
        """
        Returns:
            inspect of db engine.
        """
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        """
        Check the exsistence of table.
        Args:
            name(str): table name
        Returns:
            Weather the table exsist.
        """
        GLOG.DEBUG(
            f"Check Clickhouse table {name} exsists. {self.insp.has_table(name)}"
        )
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        """
        Get size of table.
        Args:
            model(Model): Data Model
        Returns:
            Count of table size.
        """
        GLOG.DEBUG("Try get Clickhouse table {model.__tablename__} size.")
        count = self.session.query(func.count(model.uuid)).scalar()
        GLOG.DEBUG(f"Clickhouse Table {model} size is {count}")
        return count
