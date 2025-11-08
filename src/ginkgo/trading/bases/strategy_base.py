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