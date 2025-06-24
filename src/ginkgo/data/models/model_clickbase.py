import pandas as pd
import uuid
import datetime

from typing import Optional
from types import FunctionType, MethodType
from sqlalchemy import Enum, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from clickhouse_sqlalchemy import engines


from ginkgo.libs import datetime_normalize
from ginkgo.libs.utils.display import base_repr
from ginkgo.enums import SOURCE_TYPES


class Base(DeclarativeBase):
    pass


class MClickBase(Base):
    __abstract__ = True
    __tablename__ = "ClickBaseModel"
    __table_args__ = (
        engines.MergeTree(order_by=("timestamp",)),
        {"extend_existing": True},
    )

    # uuid: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    uuid: Mapped[str] = mapped_column(String(32), default=lambda: str(uuid.uuid4().hex))
    meta: Mapped[Optional[str]] = mapped_column(String(255), default="{}")
    desc: Mapped[Optional[str]] = mapped_column(String(255), default="This man is lazy, there is no description.")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, primary_key=True)
    # timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)
    source: Mapped[SOURCE_TYPES] = mapped_column(Enum(SOURCE_TYPES), default=SOURCE_TYPES.OTHER)

    def update(self) -> None:
        raise NotImplementedError("Model Class need to overload Function set to transit data.")

    def to_dataframe(self, *args, **kwargs) -> pd.DataFrame:
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

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 80)
