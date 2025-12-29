# Upstream: Backtest Engines (判断交易日)、Data Services (同步交易日历)
# Downstream: Base (继承提供uuid/component_type)、MARKET_TYPES (枚举CHINA/NASDAQ)
# Role: TradeDay交易日历实体继承Base定义核心属性提供枚举验证和转换方法支持交易系统功能和组件集成提供完整业务支持






import datetime
import pandas as pd
from functools import singledispatchmethod

from ginkgo.trading.core.base import Base
from ginkgo.enums import MARKET_TYPES, COMPONENT_TYPES
from ginkgo.libs import datetime_normalize, base_repr


class TradeDay(Base):
    def __init__(
        self,
        market: MARKET_TYPES,
        is_open: bool,
        timestamp: any,
        uuid: str = "",
        *args,
        **kwargs,
    ):
        # 使用Base类初始化，传入组件类型和UUID
        super(TradeDay, self).__init__(uuid=uuid, component_type=COMPONENT_TYPES.TRADEDAY, *args, **kwargs)

        # 严格类型验证 - 确保参数类型正确
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")
        if not isinstance(is_open, bool):
            raise TypeError(f"is_open must be bool, got {type(is_open)}")

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(timestamp)
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {timestamp}")

        # 设置属性
        self._market = market
        self._is_open = is_open
        self._timestamp = normalized_timestamp

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(self, market: MARKET_TYPES, is_open: bool, timestamp: any, *args, **kwargs) -> None:
        # 严格类型验证
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")
        if not isinstance(is_open, bool):
            raise TypeError(f"is_open must be bool, got {type(is_open)}")

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(timestamp)
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {timestamp}")

        self._market = market
        self._is_open = is_open
        self._timestamp = normalized_timestamp

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"market", "is_open", "timestamp"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(df.index):
            missing_fields = required_fields - set(df.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        # 严格类型验证
        market = df["market"]
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")

        is_open = df["is_open"]
        # 将pandas/numpy bool转换为Python bool
        if hasattr(is_open, 'item'):
            is_open = bool(is_open.item())
        elif not isinstance(is_open, bool):
            is_open = bool(is_open)

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(df["timestamp"])
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {df['timestamp']}")

        self._market = market
        self._is_open = is_open
        self._timestamp = normalized_timestamp

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        required_fields = {"market", "is_open", "timestamp"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 假设DataFrame只有一行数据，取第一行
        row = df.iloc[0] if len(df) > 0 else df.iloc[0]

        # 严格类型验证
        market = row["market"]
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")

        is_open = row["is_open"]
        # 将pandas/numpy bool转换为Python bool
        if hasattr(is_open, 'item'):
            is_open = bool(is_open.item())
        elif not isinstance(is_open, bool):
            is_open = bool(is_open)

        # 时间戳格式验证和标准化
        normalized_timestamp = datetime_normalize(row["timestamp"])
        if normalized_timestamp is None:
            raise ValueError(f"Invalid timestamp format: {row['timestamp']}")

        self._market = market
        self._is_open = is_open
        self._timestamp = normalized_timestamp

    @property
    def market(self) -> MARKET_TYPES:
        return self._market

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @classmethod
    def from_model(cls, model, *args, **kwargs):
        """从数据模型创建TradeDay实例"""
        # 处理market字段 - 支持整数和枚举类型
        market_value = getattr(model, 'market', MARKET_TYPES.OTHER)
        if isinstance(market_value, int):
            # 如果是整数，转换为枚举对象
            market = MARKET_TYPES(market_value)
        elif isinstance(market_value, MARKET_TYPES):
            # 如果已经是枚举对象，直接使用
            market = market_value
        else:
            # 其他情况，使用默认值
            market = MARKET_TYPES.OTHER

        return cls(
            market=market,
            is_open=getattr(model, 'is_open', True),
            timestamp=getattr(model, 'timestamp', '1990-01-01'),
            uuid=getattr(model, 'uuid', ''),
            *args,
            **kwargs
        )

    def to_model(self, model_class, *args, **kwargs):
        """转换为数据模型"""
        return model_class(
            market=self.market,
            is_open=self.is_open,
            timestamp=self.timestamp,
            uuid=self.uuid,
            *args,
            **kwargs
        )

    def __repr__(self) -> str:
        return base_repr(self, TradeDay.__name__, 20, 60)
