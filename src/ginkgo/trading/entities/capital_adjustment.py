# Upstream: Portfolio Manager (记录资金调整)、Backtest Engines (跟踪资金变化)
# Downstream: Base (继承提供uuid/component_type)、SOURCE_TYPES (枚举)
# Role: CapitalAdjustment资金调整实体继承Base定义投资组合/金额/时间/原因/来源/UUID等核心属性






import datetime
import pandas as pd
from decimal import Decimal
from functools import singledispatchmethod

from ginkgo.trading.core.base import Base
from ginkgo.enums import SOURCE_TYPES, COMPONENT_TYPES
from ginkgo.libs import datetime_normalize, base_repr, to_decimal


class CapitalAdjustment(Base):
    """
    资金调整业务实体类

    表示投资组合的资金调整操作，包括入金、出金、费用扣除等。
    """

    def __init__(
        self,
        portfolio_id: str,
        amount: Decimal,
        timestamp: any,
        reason: str = "",
        source: SOURCE_TYPES = SOURCE_TYPES.SIM,
        uuid: str = "",
        *args,
        **kwargs,
    ):
        # 使用Base类初始化，传入组件类型和UUID
        super(CapitalAdjustment, self).__init__(
            uuid=uuid,
            component_type=COMPONENT_TYPES.CAPITALADJUSTMENT,
            *args,
            **kwargs
        )

        # 严格类型验证
        if not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise ValueError("portfolio_id must be a non-empty string")

        if not isinstance(amount, (Decimal, int, float)):
            raise TypeError(f"amount must be Decimal, int, or float, got {type(amount)}")

        if not isinstance(reason, str):
            raise TypeError(f"reason must be string, got {type(reason)}")

        if not isinstance(source, SOURCE_TYPES):
            raise TypeError(f"source must be SOURCE_TYPES enum, got {type(source)}")

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(timestamp)
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {timestamp}")

        # 设置属性
        self._portfolio_id = portfolio_id.strip()
        self._amount = to_decimal(amount)
        self._reason = reason
        self._source = source
        self._timestamp = normalized_timestamp

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(self, portfolio_id: str, amount: Decimal, timestamp: any,
          reason: str = "", source: SOURCE_TYPES = SOURCE_TYPES.SIM, *args, **kwargs) -> None:
        # 严格类型验证
        if not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise ValueError("portfolio_id must be a non-empty string")

        if not isinstance(amount, (Decimal, int, float)):
            raise TypeError(f"amount must be Decimal, int, or float, got {type(amount)}")

        if not isinstance(reason, str):
            raise TypeError(f"reason must be string, got {type(reason)}")

        if not isinstance(source, SOURCE_TYPES):
            raise TypeError(f"source must be SOURCE_TYPES enum, got {type(source)}")

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(timestamp)
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {timestamp}")

        self._portfolio_id = portfolio_id.strip()
        self._amount = to_decimal(amount)
        self._reason = reason
        self._source = source
        self._timestamp = normalized_timestamp

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"portfolio_id", "amount", "timestamp"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(df.index):
            missing_fields = required_fields - set(df.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        # 提取并验证数据
        portfolio_id = str(df["portfolio_id"]).strip()
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty")

        amount = to_decimal(df["amount"])

        reason = str(df.get("reason", ""))
        source = df.get("source", SOURCE_TYPES.SIM)
        if not isinstance(source, SOURCE_TYPES):
            source = SOURCE_TYPES.validate_input(source)

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(df["timestamp"])
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {df['timestamp']}")

        self._portfolio_id = portfolio_id
        self._amount = amount
        self._reason = reason
        self._source = source
        self._timestamp = normalized_timestamp

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        required_fields = {"portfolio_id", "amount", "timestamp"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 假设DataFrame只有一行数据，取第一行
        row = df.iloc[0] if len(df) > 0 else df.iloc[0]

        # 提取并验证数据
        portfolio_id = str(row["portfolio_id"]).strip()
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty")

        amount = to_decimal(row["amount"])

        reason = str(row.get("reason", ""))
        source = row.get("source", SOURCE_TYPES.SIM)
        if not isinstance(source, SOURCE_TYPES):
            source = SOURCE_TYPES.validate_input(source)

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(row["timestamp"])
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {row['timestamp']}")

        self._portfolio_id = portfolio_id
        self._amount = amount
        self._reason = reason
        self._source = source
        self._timestamp = normalized_timestamp

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @classmethod
    def from_model(cls, model, *args, **kwargs):
        """从数据模型创建CapitalAdjustment实例"""
        return cls(
            portfolio_id=getattr(model, 'portfolio_id', ''),
            amount=getattr(model, 'amount', Decimal('0')),
            timestamp=getattr(model, 'timestamp', datetime.datetime.now()),
            reason=getattr(model, 'reason', ''),
            source=getattr(model, 'source', SOURCE_TYPES.SIM),
            uuid=getattr(model, 'uuid', ''),
            *args,
            **kwargs
        )

    def to_model(self, model_class, *args, **kwargs):
        """转换为数据模型"""
        return model_class(
            portfolio_id=self.portfolio_id,
            amount=self.amount,
            timestamp=self.timestamp,
            reason=self.reason,
            source=self.source,
            uuid=self.uuid,
            *args,
            **kwargs
        )

    def __repr__(self) -> str:
        return base_repr(self, CapitalAdjustment.__name__, 20, 60)