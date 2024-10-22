import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from ginkgo.libs.ginkgo_logger import GLOG, GinkgoLogger


class GinkgoMysql(object):
    def __init__(self, user: str, pwd: str, host: str, port: str, db: str, *args, **kwargs) -> None:
        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._echo = False
        self._connect_timeout = 2
        self._read_timeout = 4
        self._uri = f"mysql+pymysql://{self._user}:{self._pwd}@{self._host}:{self._port}/{self._db}?connect_timeout={self._connect_timeout}&read_timeout={self._read_timeout}"
        self._engine = create_engine(self._uri, echo=self._echo, future=True)
        self._session_factory = scoped_session(sessionmaker(bind=self.engine))

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

    def remove_session(self) -> None:
        self._session_factory.remove()
