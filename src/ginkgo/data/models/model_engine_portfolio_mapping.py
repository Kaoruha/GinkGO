import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import base_repr


class MEnginePortfolioMapping(MMysqlBase):
    __abstract__ = False
    __tablename__ = "engine_portfolio_mapping"

    engine_id: Mapped[str] = mapped_column(String(32), default="")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    engine_name: Mapped[str] = mapped_column(String(32), default="")
    portfolio_name: Mapped[str] = mapped_column(String(32), default="")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        engine_id: str,
        portfolio_id: Optional[str] = None,
        engine_name: Optional[str] = None,
        portfolio_name: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.engine_id = engine_id
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_name is not None:
            self.engine_name = engine_name
        if portfolio_name is not None:
            self.portfolio_name = portfolio_name
        if source is not None:
            self.set_source(source)
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.engine_id = df["engine_id"]
        self.portfolio_id = df["portfolio_id"]
        self.engine_name = df["engine_name"]
        self.portfolio_name = df["portfolio_name"]
        if "source" in df.keys():
            self.set_source(df["source"])
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MEnginePortfolioMapping实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理source字段的枚举转换
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            # 从kwargs中移除source，避免重复赋值
            del kwargs['source']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
