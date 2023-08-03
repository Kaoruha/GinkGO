from sqlalchemy import create_engine, MetaData, inspect, func, DDL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from ginkgo import GLOG
from clickhouse_sqlalchemy.orm.query import Query


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

        # self.__create_database()
        self.__connect()

    def __connect(self) -> None:
        uri = f"clickhouse://{self.__user}:{self.__pwd}@{self.__host}:{self.__port}/{self.__db}"
        self.engine = create_engine(uri)
        self.session = sessionmaker(self.engine)(query_cls=Query)
        self.metadata = MetaData(bind=self.engine)
        self.base = declarative_base(metadata=self.metadata)
        GLOG.INFO("Connect to clickhouse succeed.")

    def __create_database(self) -> None:
        # ATTENTION DDL will run the sql, be care of COMMAND INJECTION
        # ATTENTION DDL will run the sql, be care of COMMAND INJECTION
        # ATTENTION DDL will run the sql, be care of COMMAND INJECTION
        uri = f"clickhouse://{self.__user}:{self.__pwd}@{self.__host}:{self.__port}/default"
        e = create_engine(uri)
        e.execute(
            DDL(
                f"CREATE DATABASE IF NOT EXISTS {self.__db} ENGINE = Memory COMMENT 'For Ginkgo Quant'"
            )
        )

    @property
    def insp(self):
        return inspect(self.engine)

    def is_table_exsists(self, name: str) -> bool:
        return self.insp.has_table(name)

    def get_table_size(self, model) -> int:
        count = self.session.query(func.count(model.uuid)).scalar()
        return count
