# Upstream: Data Sources (TDX实时行情生成Tick)、Backtest Engines (处理高频Tick事件)
# Downstream: Base (继承提供uuid/component_type)、TICKDIRECTION_TYPES/SOURCE_TYPES (枚举)
# Role: Tick逐笔成交数据实体继承Base定义代码/价格/量/方向/时间/来源等核心属性支持交易系统功能和组件集成提供完整业务支持






import datetime
import pandas as pd
from decimal import Decimal
from functools import singledispatchmethod
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.trading.core.base import Base
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES, COMPONENT_TYPES


class Tick(Base):
    def __init__(
        self,
        code: str,
        price: Number,
        volume: int,
        direction: TICKDIRECTION_TYPES,
        timestamp: any,
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
        uuid: str = "",
        *args,
        **kwargs,
    ) -> None:
        super(Tick, self).__init__(uuid=uuid, component_type=COMPONENT_TYPES.TICK, *args, **kwargs)
        self.set(code, price, volume, direction, timestamp, source)

    @singledispatchmethod
    def set(self) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        code: str,
        price: Number,
        volume: int,
        direction: TICKDIRECTION_TYPES,
        timestamp: any,
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
    ) -> None:
        # 参数类型和值校验
        if not isinstance(code, str):
            raise ValueError("Code must be a string.")
        # 价格校验：支持int、float、Decimal、str类型，并检查非负
        try:
            price_decimal = to_decimal(price)
            if price_decimal < 0:
                raise ValueError("Price must be a non-negative number.")
        except (ValueError, TypeError):
            raise ValueError("Price must be a valid non-negative number.")
        # 成交量校验：支持int、float类型，并检查非负，自动转换为整数
        try:
            volume_int = int(volume)
            if volume_int < 0:
                raise ValueError("Volume must be a non-negative integer.")
        except (ValueError, TypeError):
            raise ValueError("Volume must be a valid non-negative integer.")
        if not isinstance(direction, TICKDIRECTION_TYPES):
            raise ValueError("Direction must be a valid TICKDIRECTION_TYPES enum.")
        if not isinstance(timestamp, (str, datetime.datetime)):
            raise ValueError("Timestamp must be a string or datetime object.")
        if not isinstance(source, SOURCE_TYPES):
            raise ValueError("Source must be a valid SOURCE_TYPES enum.")

        # 赋值
        self._code = code
        self._price = to_decimal(price)
        self._volume = int(volume)
        self._direction = direction
        self._timestamp = datetime_normalize(timestamp)
        self._source = source

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"code", "price", "volume", "direction", "timestamp"}
        # 检查 Series 是否包含所有必需字段
        if isinstance(df, pd.DataFrame):
            if not required_fields.issubset(df.columns):
                missing_fields = required_fields - set(df.columns)
                raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")
        if isinstance(df, pd.Series):
            if not required_fields.issubset(df.index):
                missing_fields = required_fields - set(df.index)
                raise ValueError(f"Missing required fields in Series: {missing_fields}")
        self._code = df["code"]
        self._price = to_decimal(df["price"])
        self._volume = df["volume"]
        self._direction = df["direction"]
        self._timestamp = datetime_normalize(df["timestamp"])

        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df["source"]))

    @property
    def code(self) -> str:
        return self._code

    @property
    def price(self) -> Decimal:
        return self._price

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def direction(self) -> TICKDIRECTION_TYPES:
        return self._direction

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    def to_model(self):
        """
        Convert Tick entity to MTick database model.

        Returns:
            MTick: Database model instance
        """
        from ginkgo.data.models.model_tick import MTick

        model = MTick()
        model.update(
            self._code,  # code作为第一个位置参数
            price=self._price,
            volume=self._volume,
            direction=self._direction,
            timestamp=self._timestamp,
            source=self._source
        )
        return model

    @classmethod
    def from_model(cls, model):
        """
        Create Tick entity from MTick database model.

        Args:
            model (MTick): Database model instance

        Returns:
            Tick: Tick entity instance

        Raises:
            TypeError: If model is not an MTick instance
        """
        from ginkgo.data.models.model_tick import MTick
        from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES

        # Validate model type
        if not isinstance(model, MTick):
            raise TypeError(f"Expected MTick instance, got {type(model).__name__}")

        # Convert direction from int back to enum
        direction = TICKDIRECTION_TYPES.from_int(model.direction) or TICKDIRECTION_TYPES.VOID

        # Convert source from int back to enum
        source = SOURCE_TYPES.from_int(model.source) or SOURCE_TYPES.OTHER

        return cls(
            code=model.code,
            price=model.price,
            volume=model.volume,
            direction=direction,
            timestamp=model.timestamp,
            source=source
        )

    def __repr__(self) -> str:
        return base_repr(self, "DB" + Tick.__name__.capitalize(), 12, 46)
