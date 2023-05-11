from sqlalchemy import create_engine, MetaData, inspect, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_conf import GINKGOCONF


class GinkgoClickhouse(object):
    def __init__(self, user: str, pwd: str, host: str, port: int, db: str):
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

    def __connect(self):
        uri = f"clickhouse://{self.__user}:{self.__pwd}@{self.__host}:{self.__port}/{self.__db}"
        self.engine = create_engine(uri)
        self.session = sessionmaker(self.engine)()
        self.metadata = MetaData(bind=self.engine)
        gl.logger.info("Connect to clickhouse succeed.")
        self.base = declarative_base(metadata=self.metadata)

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        count = self.session.query(func.count(model.uuid)).scalar()
        return count
