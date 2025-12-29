# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: BaseRouter路由器抽象基类接口，定义订单路由和匹配的核心方法，供子类继承实现具体路由逻辑和订单分发功能






"""
BaseRouter基础类

通过Mixin组装，提供Router的基础功能。
组装TimeMixin、ContextMixin、LoggableMixin、OrderManagementMixin等基础功能。
"""

from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
from ginkgo.trading.mixins.order_management_mixin import OrderManagementMixin
from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin


class BaseRouter(TimeMixin, ContextMixin, LoggableMixin, OrderManagementMixin, EngineBindableMixin):
    """
    Router基础类

    通过Mixin组装提供Router的基础功能：
    - TimeMixin: 时间管理和业务时间戳处理
    - ContextMixin: 引擎上下文管理
    - LoggableMixin: 统一日志记录
    - OrderManagementMixin: 内存订单管理

    子类继承后只需要专注于具体的路由逻辑。
    """

    def __init__(self, name: str = "BaseRouter"):
        """
        初始化Router基础功能

        Args:
            name: Router名称
        """
        # 按照Mixin依赖顺序初始化
        TimeMixin.__init__(self)
        ContextMixin.__init__(self)
        LoggableMixin.__init__(self)
        OrderManagementMixin.__init__(self)

        # 设置名称
        self._router_name = name

        # 记录初始化完成
        self.log("INFO", f"{self._router_name} initialized")

    @property
    def name(self) -> str:
        """
        获取Router名称

        Returns:
            str: Router名称
        """
        return self._router_name

    def get_router_info(self) -> dict:
        """
        获取Router信息摘要

        Returns:
            dict: Router信息
        """
        return {
            'name': self._router_name,
            'pending_orders': self.get_pending_order_count(),
            'processing_orders': self.get_tracked_order_count(),
            'execution_history': self.get_execution_history_count(),
            'has_engine_binding': hasattr(self, 'bound_engine') and self.bound_engine is not None,
        }