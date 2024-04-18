import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, BLOB
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import FILE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MBacktestBinding(MMysqlBase):
    __abstract__ = False
    __tablename__ = "backtest_binding"

    backtest_id = Column(String(40), default="backtest_id")
    file_id = Column(String(40), default="file_id")
    file_name = Column(String(40), default="file_name")
    type = Column(ChoiceType(FILE_TYPES, impl=Integer()), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MBacktestBinding, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self, backtest_id: str, file_id: str, file_name: str, file_type: FILE_TYPES
    ) -> None:
        self.backtest_id = str(backtest_id)
        self.file_id = str(file_id)
        self.file_name = str(file_name)
        self.type = file_type

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
