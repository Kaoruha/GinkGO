from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, BLOB, Enum, Boolean
from sqlalchemy_utils import ChoiceType

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.enums import FILE_TYPES


class MPortfolioFileMapping(MMysqlBase):
    __abstract__ = False
    __tablename__ = "portfolio_file_mapping"

    name = Column(String(40), default="ginkgo_bind")
    portfolio_id = Column(String(40), default="ginkgo_portfolio")
    file_id = Column(String(40), default="ginkgo_file")
    type = Column(ChoiceType(FILE_TYPES, impl=Integer()), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MPortfolioFileMapping, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
        pass

    @set.register
    def _(
        self,
        name: str,
        portfolio_id: str,
        file_id: str,
        file_type: FILE_TYPES,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        self.portfolio_id = self.portfolio_id
        self.file_id = file_id
        self.type = file_type

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
