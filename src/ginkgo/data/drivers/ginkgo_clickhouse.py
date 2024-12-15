from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session

from ginkgo.libs import GLOG, GinkgoLogger


class GinkgoClickhouse(object):
    def __init__(self, user: str, pwd: str, host: str, port: int, db: str):
        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._echo = False
        self._connect_timeout = 10
        self._read_timeout = 10
        self._uri = f"clickhouse://{self._user}:{self._pwd}@{self._host}:{self._port}/{self._db}?connect_timeout={self._connect_timeout}&read_timeout={self._read_timeout}"
        self._engine = create_engine(
            self._uri,
            echo=self._echo,
            future=True,
            pool_recycle=3600,
            pool_size=10,
            pool_timeout=20,
            max_overflow=10,
        )
        self._session_factory = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=self.engine))

    @property
    def engine(self):
        """
        Returns:
            DB Engine.
        """
        return self._engine

    @property
    def session(self):
        """
        Returns:
            DB Session.
        """
        return self._session_factory()

    def remove_session(self):
        self._session_factory.remove()
