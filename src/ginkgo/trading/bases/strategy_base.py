# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: BaseStrategy策略基类接口，提供cal计算、initialize初始化、finalize终结等核心方法，供具体策略继承实现交易逻辑






"""
策略组件基类

组合策略相关的基础能力，为所有策略组件提供基础功能
"""

from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin


class StrategyBase(TimeMixin, ContextMixin, NamedMixin, LoggableMixin, Base):
    """
    策略组件基类

    组合策略相关的基础能力，为所有策略组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 名称管理 (name)
    - 日志管理 (log, add_logger)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, name: str = "strategy", **kwargs):
        """
        初始化策略基类

        Args:
            name: 策略名称
            **kwargs: 传递给父类的参数
        """
        # 显式初始化各个Mixin，确保正确的初始化顺序
        TimeMixin.__init__(self, **kwargs)
        ContextMixin.__init__(self, **kwargs)
        NamedMixin.__init__(self, name=name, **kwargs)
        LoggableMixin.__init__(self, **kwargs)
        Base.__init__(self)

    def create_signal(
        self,
        code: str,
        direction,
        reason: str = "",
        volume: int = 0,
        weight: float = 0.0,
        strength: float = 0.5,
        confidence: float = 0.5,
        **kwargs
    ):
        """
        创建带有完整上下文的交易信号

        自动填充 portfolio_id、engine_id、run_id，策略只需关注业务参数。

        Args:
            code: 股票代码
            direction: 交易方向 (DIRECTION_TYPES)
            reason: 信号原因
            volume: 建议交易量
            weight: 信号权重
            strength: 信号强度
            confidence: 信号置信度
            **kwargs: 其他 Signal 参数 (如 business_timestamp)

        Returns:
            Signal: 带有完整上下文的信号对象
        """
        from ginkgo.trading.entities.signal import Signal

        return Signal(
            portfolio_id=self.portfolio_id,
            engine_id=self.engine_id,
            run_id=self.run_id,
            code=code,
            direction=direction,
            reason=reason,
            volume=volume,
            weight=weight,
            strength=strength,
            confidence=confidence,
            **kwargs
        )