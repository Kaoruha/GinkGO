import uuid
import pandas as pd
import datetime
from types import FunctionType, MethodType
from functools import singledispatchmethod
from enum import Enum
from types import FunctionType, MethodType
from ginkgo.data import DBDRIVER as db
from ginkgo.libs.ginkgo_pretty import base_repr
from sqlalchemy import Column, String, DateTime, Boolean, func


def gen_id(self):
    return uuid.uuid4().hex


def get_datetime(self):
    return datetime.datetime.now()


class MBase(db.base):
    __abstract__ = True
    __tablename__ = "BaseModel"

    uuid = Column(String(32), primary_key=True)
    desc = Column(
        String(255),
        default="This man is lazy, there is no description.",
    )
    timestamp = Column(DateTime)
    create = Column(DateTime)
    update = Column(DateTime)
    isdel = Column(Boolean)

    def __init__(self):
        self.uuid = uuid.uuid4().hex
        self.timestamp = datetime.datetime.now()
        self.create = datetime.datetime.now()
        self.update = datetime.datetime.now()
        self.desc = "This man is so lazy. There is no description"
        self.isdel = False

    def set(self):
        raise NotImplementedError(
            "Model Class need to overload Function set to transit data."
        )

    @property
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
            else:
                item[param] = self.__getattribute__(param)

        df = pd.DataFrame.from_dict(item, orient="index")
        return df

    def delete(self):
        self.isdel = True

    def cancel_delete(self):
        self.isdel = False

    def __repr__(self):
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 80)
