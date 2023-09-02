import pandas as pd
import datetime
from types import FunctionType, MethodType
from functools import singledispatchmethod
from enum import Enum
from types import FunctionType, MethodType
from ginkgo.libs import gen_uuid4, datetime_normalize
from sqlalchemy.ext.declarative import declarative_base
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.enums import SOURCE_TYPES
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy_utils import ChoiceType


Base = declarative_base()


class MMysqlBase(Base):
    __abstract__ = True
    __tablename__ = "MysqlBaseModel"

    uuid = Column(String(32), primary_key=True)
    desc = Column(
        String(255),
        default="This man is lazy, there is no description.",
    )
    timestamp = Column(DateTime, default=datetime_normalize("1950-01-01"))
    create = Column(DateTime)
    update = Column(DateTime)
    isdel = Column(Boolean)
    source = Column(ChoiceType(SOURCE_TYPES, impl=Integer()), default=0)

    def __init__(self) -> None:
        self.uuid = gen_uuid4()
        self.timestamp = datetime.datetime.now()
        self.create = datetime.datetime.now()
        self.source = SOURCE_TYPES.VOID
        self.update = datetime.datetime.now()
        self.desc = "This man is so lazy. There is no description"
        self.isdel = False

    def set(self) -> None:
        raise NotImplementedError(
            "Model Class need to overload Function set to transit data."
        )

    def to_dataframe(self) -> pd.DataFrame:
        item = {}
        methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
        for param in self.__dir__():
            if param in methods:
                continue
            if param.startswith("_"):
                continue
            if isinstance(self.__getattribute__(param), MethodType):
                continue
            if isinstance(self.__getattribute__(param), FunctionType):
                continue

            if isinstance(self.__getattribute__(param), Enum):
                item[param] = self.__getattribute__(param).value
            elif isinstance(self.__getattribute__(param), str):
                item[param] = self.__getattribute__(param).strip(b"\x00".decode())
            else:
                item[param] = self.__getattribute__(param)

        df = pd.DataFrame.from_dict(item, orient="index").transpose()
        return df

    def set_source(self, source: SOURCE_TYPES) -> None:
        self.source = source

    def delete(self) -> None:
        self.isdel = True

    def cancel_delete(self) -> None:
        self.isdel = False

    def update_time(self, time: str or datetime.datetime) -> None:
        self.update = datetime.datetime.now()
        self.timestamp = datetime_normalize(time)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 80)
