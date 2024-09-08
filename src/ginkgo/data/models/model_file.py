import pandas as pd
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, BLOB, Enum, Boolean
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import FILE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MFile(MMysqlBase):
    __abstract__ = False
    __tablename__ = "file"

    file_name = Column(String(40), default="ginkgo_file")
    type = Column(ChoiceType(FILE_TYPES, impl=Integer()), default=0)
    content = Column(BLOB)

    def __init__(self, *args, **kwargs) -> None:
        super(MFile, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        file_name: str,
        type: FILE_TYPES,
        content: any,
        *args,
        **kwargs,
    ) -> None:
        self.file_name = file_name
        self.type = type
        self.content = content

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
