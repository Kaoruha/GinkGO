"""
订单组件基类

组合时间和上下文管理能力，为所有订单组件提供基础功能
"""

from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin


class OrderBase(TimeMixin, ContextMixin, Base):
    """
    订单组件基类

    组合时间和上下文管理能力，为所有订单组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 引擎上下文同步 (sync_engine_context)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, **kwargs):
        """
        初始化订单基类

        Args:
            **kwargs: 传递给父类的参数
        """
        # 显式初始化各个父类，确保正确的初始化顺序
        TimeMixin.__init__(self, **kwargs)
        ContextMixin.__init__(self, **kwargs)
        Base.__init__(self)