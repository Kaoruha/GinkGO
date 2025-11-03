import pandas as pd
import uuid
import datetime
from functools import singledispatchmethod
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, GLOG
from ginkgo.trading.core.base import Base
from ginkgo.trading.entities.time_related import TimeRelated


class Signal(Base, TimeRelated):
    """
    Signal Class.
    """

    def __init__(
        self,
        portfolio_id: str = "",
        engine_id: str = "",
        run_id: str = "",  # 新增run_id参数
        timestamp: any = None,
        code: str = "Default Signal Code",
        direction: DIRECTION_TYPES = None,
        reason: str = "no reason",
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
        strength: float = 0.5,  # 信号强度，默认中等强度
        confidence: float = 0.5,  # 信号置信度，默认中等置信度
        uuid: str = "",  # 新增uuid参数支持，空值时自动生成
        *args,
        **kwargs,
    ) -> None:
        # 初始化多重继承的父类
        from ginkgo.enums import COMPONENT_TYPES
        Base.__init__(self, uuid=uuid, component_type=COMPONENT_TYPES.SIGNAL, *args, **kwargs)
        TimeRelated.__init__(self, timestamp=timestamp, *args, **kwargs)

        try:
            self.set(portfolio_id, engine_id, run_id, timestamp, code, direction, reason, source, strength, confidence)
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
        timestamp: any,
        code: str,
        direction: DIRECTION_TYPES,
        reason: str,
        source: SOURCE_TYPES,
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

        # timestamp验证和设置（委托给TimeRelated）
        if timestamp is None:
            raise ValueError("timestamp cannot be None.")
        self.timestamp = timestamp  # 使用TimeRelated的timestamp属性

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
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._code: str = code
        self._reason = reason
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

            # 处理时区兼容性问题
            if self._timestamp.tzinfo is not None and current_time.tzinfo is None:
                # Signal timestamp有时区，current_time没有时区 - 将current_time转换为本地时区的aware datetime
                import datetime
                local_tz = datetime.datetime.now().astimezone().tzinfo
                current_time = current_time.replace(tzinfo=local_tz)
            elif self._timestamp.tzinfo is None and current_time.tzinfo is not None:
                # Signal timestamp没有时区，current_time有时区 - 移除current_time的时区
                current_time = current_time.replace(tzinfo=None)

            if self._timestamp > current_time:
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
            strength=model.strength,
            confidence=model.confidence
        )
