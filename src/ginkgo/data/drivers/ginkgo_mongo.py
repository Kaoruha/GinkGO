from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


class GinkgoMongo(object):
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

    def __connect(self) -> None:
        uri = f""
        self.engine = create_engine(uri)
        self.session = sessionmaker(self.engine)
        self.metadata = MetaData(bind=self.engine)
        GLOG.INFO("Connect to mongo succeed.")
        self.base = declarative_base(metadata=self.metadata)

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        count = self.session.query(func.count(model.uuid)).scalar()
        return count
