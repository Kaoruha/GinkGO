from sqlalchemy import create_engine, Column, MetaData, DDL
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from clickhouse_sqlalchemy import (
    Table,
    make_session,
    get_declarative_base,
    types,
    engines,
)

user = GINKGOCONF.CLICKDB
pwd = GINKGOCONF.CLICKPWD
host = "localhost"
port = 9000
db = GINKGOCONF.CLICKDB

uri = f"clickhouse+native://{user}:{pwd}@{host}/{db}"

engine = create_engine(uri, pool_size=100, pool_recycle=3600, pool_timeout=20)
session = make_session(engine)
metadata = MetaData(bind=engine)

Base = get_declarative_base(metadata=metadata)
