import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, BLOB
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import PARAMETER_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MFileParameter(MMysqlBase):
    __abstract__ = False
    __tablename__ = "file_parameter"

    file_id = Column(String(40), default="file_id")
    para_name = Column(String(40), default="para_name")
    order = Column(Integer, default=0)
    type = Column(ChoiceType(PARAMETER_TYPES, impl=Integer()), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MBacktestBinding, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self, file_id: str, para_name: str, para_type: PARAMETER_TYPES, order: int
    ) -> None:
        self.file_id = str(file_id)
        self.para_name = str(para_name)
        self.type = para_type
        self.order = int(order)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
