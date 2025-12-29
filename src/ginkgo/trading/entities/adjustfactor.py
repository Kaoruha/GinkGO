# Upstream: Data Services (AdjustfactorService同步复权因子)、Backtest Engines (复权K线价格)
# Downstream: Base (继承提供uuid/component_type)、FREQUENCY_TYPES (枚举)
# Role: Adjustfactor复权因子实体继承Base定义代码/时间/前复权/后复权/复权因子/UUID等核心属性






import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod
from decimal import Decimal

from ginkgo.trading.core.base import Base
from ginkgo.libs import base_repr, pretty_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import FREQUENCY_TYPES, COMPONENT_TYPES


class Adjustfactor(Base):
    """
    Adjustfactor Container. Store adjustment factor info for stock price adjustment.
    """

    def __init__(
        self,
        code: str,
        timestamp: any,
        fore_adjustfactor: Number,
        back_adjustfactor: Number,
        adjustfactor: Number,
        uuid: str = "",
        *args,
        **kwargs
    ) -> None:
        # 使用Base类初始化，传入组件类型和UUID
        super(Adjustfactor, self).__init__(uuid=uuid, component_type=COMPONENT_TYPES.ADJUSTFACTOR, *args, **kwargs)

        # 参数验证
        if not code or not isinstance(code, str):
            raise ValueError(f"code must be a non-empty string, got {code}")

        self.set(code, timestamp, fore_adjustfactor, back_adjustfactor, adjustfactor)

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        """
        1. code, timestamp, fore_adjustfactor, back_adjustfactor, adjustfactor
        2. Series
        3. DataFrame
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        code: str,
        timestamp: any,
        fore_adjustfactor: Number = 0,
        back_adjustfactor: Number = 0,
        adjustfactor: Number = 0,
        *args,
        **kwargs
    ) -> None:
        self._code = code
        self._timestamp = datetime_normalize(timestamp)
        self._fore_adjustfactor = to_decimal(fore_adjustfactor)
        self._back_adjustfactor = to_decimal(back_adjustfactor)
        self._adjustfactor = to_decimal(adjustfactor)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"code", "timestamp", "fore_adjustfactor", "back_adjustfactor", "adjustfactor"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(df.index):
            missing_fields = required_fields - set(df.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        self._code = df["code"]
        self._timestamp = datetime_normalize(df["timestamp"])
        self._fore_adjustfactor = to_decimal(df["fore_adjustfactor"])
        self._back_adjustfactor = to_decimal(df["back_adjustfactor"])
        self._adjustfactor = to_decimal(df["adjustfactor"])

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        required_fields = {"code", "timestamp", "fore_adjustfactor", "back_adjustfactor", "adjustfactor"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 假设DataFrame只有一行数据，取第一行
        row = df.iloc[0] if len(df) > 0 else df.iloc[0]

        self._code = row["code"]
        self._timestamp = datetime_normalize(row["timestamp"])
        self._fore_adjustfactor = to_decimal(row["fore_adjustfactor"])
        self._back_adjustfactor = to_decimal(row["back_adjustfactor"])
        self._adjustfactor = to_decimal(row["adjustfactor"])

    @property
    def code(self) -> str:
        """
        The Code of the Bar.
        """
        return self._code

    @property
    def timestamp(self) -> datetime.datetime:
        """
        Time
        """
        return self._timestamp

    @property
    def fore_adjustfactor(self) -> Decimal:
        return self._fore_adjustfactor

    @property
    def back_adjustfactor(self) -> Decimal:
        return self._back_adjustfactor

    @property
    def adjustfactor(self) -> Decimal:
        return self._adjustfactor

    @classmethod
    def from_model(cls, model, *args, **kwargs):
        """从数据模型创建Adjustfactor实例"""
        return cls(
            code=getattr(model, 'code', 'defaultcode'),
            timestamp=getattr(model, 'timestamp', '1990-01-01'),
            fore_adjustfactor=getattr(model, 'fore_adjustfactor', 0),
            back_adjustfactor=getattr(model, 'back_adjustfactor', 0),
            adjustfactor=getattr(model, 'adjustfactor', 0),
            uuid=getattr(model, 'uuid', ''),
            *args,
            **kwargs
        )

    def to_model(self, model_class, *args, **kwargs):
        """转换为数据模型"""
        return model_class(
            code=self.code,
            timestamp=self.timestamp,
            fore_adjustfactor=self.fore_adjustfactor,
            back_adjustfactor=self.back_adjustfactor,
            adjustfactor=self.adjustfactor,
            uuid=self.uuid,
            *args,
            **kwargs
        )

    def __repr__(self) -> str:
        return base_repr(self, Adjustfactor.__name__, 12, 60)
