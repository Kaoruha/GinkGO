import pandas as pd
import uuid
import datetime
from functools import singledispatchmethod
from typing import Any
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, GLOG
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
from ginkgo.trading.core.base import Base


class Signal(TimeMixin, ContextMixin, NamedMixin, LoggableMixin, Base):
    """
    Signal Class.
    """

    def __init__(
        self,
        portfolio_id: str = "",
        engine_id: str = "",
        run_id: str = "",  # 新增run_id参数
        code: str = "Default Signal Code",
        direction: DIRECTION_TYPES = None,
        reason: str = "no reason",
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
        volume: int = 0,  # 建议交易量，默认0
        weight: float = 0.0,  # 信号权重或资金分配比例，默认0
        strength: float = 0.5,  # 信号强度，默认中等强度
        confidence: float = 0.5,  # 信号置信度，默认中等置信度
        uuid: str = "",  # 新增uuid参数支持，空值时自动生成
        business_timestamp: Any = None,  # 业务时间戳，用于回测时的事件时间
        *args,
        **kwargs,
    ) -> None:
        # 显式初始化各个Mixin，确保正确的初始化顺序
        name = f"Signal_{code}_{direction}"

        # TimeMixin初始化 - 传递business_timestamp参数
        TimeMixin.__init__(self, business_timestamp=business_timestamp, **kwargs)

        # ContextMixin初始化 - 不传递参数，让set方法处理
        ContextMixin.__init__(self, **kwargs)

        # NamedMixin初始化 - 传递name参数
        NamedMixin.__init__(self, name=name, **kwargs)

        # LoggableMixin初始化
        LoggableMixin.__init__(self, **kwargs)

        # Base初始化
        from ginkgo.enums import COMPONENT_TYPES
        Base.__init__(self, uuid=uuid, component_type=COMPONENT_TYPES.SIGNAL)

        # 通过set方法设置所有业务属性（包括上下文信息）
        try:
            self.set(portfolio_id, engine_id, run_id, code, direction, reason, source, volume, weight, strength, confidence)

            # 注意：business_timestamp已经在TimeMixin中处理，不需要再次设置

        except Exception as e:
            GLOG.ERROR(f"Error initializing Signal: {e}")
            raise Exception("Error initializing Signal: {e}")

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
        """
        Dispatch method for setting attributes.
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,  # 新增run_id参数
        code: str,
        direction: DIRECTION_TYPES,
        reason: str,
        source: SOURCE_TYPES,
        volume: int = 0,
        weight: float = 0.0,
        strength: float = 0.5,
        confidence: float = 0.5,
        *args,
        **kwargs,
    ):
        # 对所有核心业务字段进行类型和值验证

        # portfolio_id类型和值验证
        if not isinstance(portfolio_id, str):
            raise TypeError(f"portfolio_id must be str, got {type(portfolio_id).__name__}")
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty.")

        # engine_id类型和值验证
        if not isinstance(engine_id, str):
            raise TypeError(f"engine_id must be str, got {type(engine_id).__name__}")
        if not engine_id:
            raise ValueError("engine_id cannot be empty.")

        # run_id类型和值验证
        if not isinstance(run_id, str):
            raise TypeError(f"run_id must be str, got {type(run_id).__name__}")
        if not run_id:
            raise ValueError("run_id cannot be empty.")

        # code类型和值验证
        if not isinstance(code, str):
            raise TypeError(f"code must be str, got {type(code).__name__}")
        if not code:
            raise ValueError("code cannot be empty.")

        # direction类型验证（支持枚举或整数）
        if direction is None:
            raise ValueError("direction cannot be None.")
        if not isinstance(direction, (DIRECTION_TYPES, int)):
            raise TypeError(f"direction must be DIRECTION_TYPES or int, got {type(direction).__name__}")

        # reason类型和值验证
        if not isinstance(reason, str):
            raise TypeError(f"reason must be str, got {type(reason).__name__}")
        if not reason:
            raise ValueError("reason cannot be empty.")

        # source类型验证（支持枚举或整数）
        if source is None:
            raise ValueError("source cannot be None.")
        if not isinstance(source, (SOURCE_TYPES, int)):
            raise TypeError(f"source must be SOURCE_TYPES or int, got {type(source).__name__}")

        # strength类型和范围验证
        if not isinstance(strength, (int, float)):
            raise TypeError(f"strength must be int or float, got {type(strength).__name__}")
        if not (0.0 <= strength <= 1.0):
            raise ValueError("信号强度必须在0.0-1.0范围内")

        # confidence类型和范围验证
        if not isinstance(confidence, (int, float)):
            raise TypeError(f"confidence must be int or float, got {type(confidence).__name__}")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("置信度必须在0.0-1.0范围内")

        # volume类型验证
        if not isinstance(volume, int):
            raise TypeError(f"volume must be int, got {type(volume).__name__}")
        if volume < 0:
            raise ValueError("volume不能为负数")

        # weight类型和范围验证
        if not isinstance(weight, (int, float)):
            raise TypeError(f"weight must be int or float, got {type(weight).__name__}")
        if weight < 0:
            raise ValueError("weight不能为负数")

        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._code: str = code
        self._reason = reason
        self._volume: int = volume
        self._weight: float = float(weight)
        self._strength: float = float(strength)
        self._confidence: float = float(confidence)

        # 支持枚举类型转换
        if isinstance(direction, int):
            self._direction: DIRECTION_TYPES = DIRECTION_TYPES(direction)
        else:
            self._direction: DIRECTION_TYPES = direction

        # 支持source类型转换
        if isinstance(source, int):
            self.set_source(SOURCE_TYPES(source))
        else:
            self.set_source(source)

    @set.register
    def _(self, series: pd.Series, *args, **kwargs):
        """
        Set from pandas Series with validation
        """
        required_fields = {"portfolio_id", "engine_id", "run_id", "timestamp", "code", "direction", "reason"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(series.index):
            missing_fields = required_fields - set(series.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        # 使用严格的验证设置字段 - 按照参数位置顺序传入
        self.set(
            series['portfolio_id'],
            series['engine_id'],
            series.get('run_id', ''),
            series['timestamp'],
            series['code'],
            DIRECTION_TYPES(series['direction']),
            series['reason'],
            SOURCE_TYPES(series.get('source', SOURCE_TYPES.OTHER.value)),
            series.get('strength', 0.5),
            series.get('confidence', 0.5)
        )

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs):
        """
        Set from pandas DataFrame (uses first row)
        """
        if df.empty:
            raise ValueError("DataFrame is empty")

        required_fields = {"portfolio_id", "engine_id", "run_id", "timestamp", "code", "direction", "reason"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 使用第一行数据设置
        row = df.iloc[0]
        self.set(row)

    @property
    def code(self) -> str:
        return self._code


    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> None:
        self._portfolio_id = value

    @property
    def engine_id(self, *args, **kwargs) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def run_id(self) -> str:
        return self._run_id

    @run_id.setter
    def run_id(self, value) -> None:
        self._run_id = value

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    @property
    def volume(self) -> int:
        """建议交易量"""
        return self._volume

    @volume.setter
    def volume(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError(f"volume must be int, got {type(value).__name__}")
        if value < 0:
            raise ValueError("volume不能为负数")
        self._volume = value

    @property
    def weight(self) -> float:
        """信号权重或资金分配比例"""
        return self._weight

    @weight.setter
    def weight(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"weight must be int or float, got {type(value).__name__}")
        if value < 0:
            raise ValueError("weight不能为负数")
        self._weight = float(value)

    @property
    def strength(self) -> float:
        return self._strength

    @strength.setter
    def strength(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"strength must be int or float, got {type(value).__name__}")
        if not (0.0 <= value <= 1.0):
            raise ValueError("信号强度必须在0.0-1.0范围内")
        self._strength = float(value)

    @property
    def confidence(self) -> float:
        return self._confidence

    @confidence.setter
    def confidence(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"confidence must be int or float, got {type(value).__name__}")
        if not (0.0 <= value <= 1.0):
            raise ValueError("置信度必须在0.0-1.0范围内")
        self._confidence = float(value)


    def __repr__(self) -> str:
        return base_repr(self, Signal.__name__, 12, 60)
    
    def is_valid(self) -> bool:
        """
        验证Signal的有效性
        Returns:
            bool: True if signal is valid, False otherwise
        """
        # 检查必需字段是否存在且有效
        if not self._portfolio_id:
            return False

        if not self._engine_id:
            return False

        if not self._code:
            return False

        if self._direction is None:
            return False

        if not isinstance(self._direction, DIRECTION_TYPES):
            return False

        if self._timestamp is None:
            return False

        # 检查时间戳是否合理（不能是未来时间）
        # 在回测模式下，使用TimeRelated的当前时间；在实时模式下，使用系统时间
        try:
            current_time = self._get_current_time()

            # 处理时区兼容性问题 - 统一转换为 naive datetime 进行比较
            timestamp_to_check = self._timestamp
            current_to_check = current_time

            # 如果 timestamp 有时区，转换为 naive
            if timestamp_to_check.tzinfo is not None:
                import datetime
                timestamp_to_check = timestamp_to_check.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            # 如果 current_time 有时区，转换为 naive
            if current_to_check.tzinfo is not None:
                import datetime
                current_to_check = current_to_check.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            if timestamp_to_check > current_to_check:
                return False
        except (TypeError, AttributeError):
            # 处理其他比较问题或TimeRelated未初始化的情况
            pass

        return True
    
    def to_model(self):
        """
        转换为数据库模型
        
        Returns:
            MSignal: 数据库模型实例
        """
        from ginkgo.data.models import MSignal
        
        model = MSignal()
        model.update(
            self._portfolio_id,
            self._engine_id,
            self._run_id,
            timestamp=self._timestamp,
            code=self._code,
            direction=self._direction,
            reason=self._reason,
            source=self._source,
            volume=self._volume,
            weight=self._weight,
            strength=self._strength,
            confidence=self._confidence
        )
        model.uuid = self.uuid
        return model
    
    @classmethod
    def from_model(cls, model) -> 'Signal':
        """
        从数据库模型创建实体

        Args:
            model (MSignal): 数据库模型实例

        Returns:
            Signal: 信号实体实例

        Raises:
            TypeError: If model is not an MSignal instance
        """
        from ginkgo.data.models.model_signal import MSignal

        # Validate model type
        if not isinstance(model, MSignal):
            raise TypeError(f"Expected MSignal instance, got {type(model).__name__}")

        return cls(
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            run_id=model.run_id,
            timestamp=model.timestamp,
            code=model.code,
            direction=DIRECTION_TYPES(model.direction),
            reason=model.reason,
            source=SOURCE_TYPES(model.source),
            volume=model.volume,
            weight=model.weight,
            strength=model.strength,
            confidence=model.confidence
        )
