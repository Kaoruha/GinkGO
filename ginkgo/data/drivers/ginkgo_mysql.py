from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoMysql(object):
    def __init__(self, user: str, pwd: str, host: str, port: str, db: str) -> None:
        self.engine = None
        self.session = None
        self.metadata = None
        self.base = None
        self.__user = user
        self.__pwd = pwd
        self.__host = host
        self.__port = port
        self.__db = db

        self.__connect()

    def __connect(self) -> None:
        # uri = f"mysql+pymysql://{self.__user}:{self.__pwd}@{self.__host}:{self.__port}/{self.__db}?charset=uft8"
        uri = f"mysql+pymysql://{self.__user}:{self.__pwd}@{self.__host}:{self.__port}/{self.__db}"

        self.engine = create_engine(
            uri,
            # pool_size=10,
            # pool_timeout=10,
            # max_overflow=5,
            # echo=True,
        )
        self.session = sessionmaker(self.engine)()
        self.metadata = MetaData(bind=self.engine)
        # self.base = declarative_base(metadata=self.metadata)
        self.base = declarative_base()
        GLOG.INFO("Connect to mysql succeed.")

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        # count = self.session.query(func.count(model.uuid)).scalar()
        count = self.session.query(model).count()
        return count
