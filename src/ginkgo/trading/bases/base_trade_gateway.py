# Upstream: gateway.trade_gateway
# Downstream: entities.mixins.TimeMixin, entities.mixins.ContextMixin, trading.mixins.order_management_mixin, entities.mixins.EngineBindableMixin, libs.GLOG
# Role: 交易网关抽象基类，通过Mixin组装时间管理、上下文管理、内存订单管理等基础功能，子类专注路由逻辑






"""
BaseTradeGateway基础类

通过Mixin组装，提供TradeGateway的基础功能。
组装TimeMixin、ContextMixin、LoggableMixin、OrderManagementMixin等基础功能。
"""

from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import ContextMixin
from ginkgo.trading.mixins.order_management_mixin import OrderManagementMixin
from ginkgo.entities.mixins import EngineBindableMixin
from ginkgo.libs import GLOG


class BaseTradeGateway(TimeMixin, ContextMixin, OrderManagementMixin, EngineBindableMixin):
    """
    TradeGateway基础类

    通过Mixin组装提供TradeGateway的基础功能：
    - TimeMixin: 时间管理和业务时间戳处理
    - ContextMixin: 引擎上下文管理
    - OrderManagementMixin: 内存订单管理

    子类继承后只需要专注于具体的路由逻辑。
    """

    def __init__(self, name: str = "BaseTradeGateway"):
        """
        初始化TradeGateway基础功能

        Args:
            name: TradeGateway名称
        """
        super().__init__()

        # 设置名称
        self._gateway_name = name

        # 记录初始化完成
        GLOG.INFO(f"{self._gateway_name} initialized")

    @property
    def name(self) -> str:
        """
        获取TradeGateway名称

        Returns:
            str: TradeGateway名称
        """
        return self._gateway_name

    def get_gateway_info(self) -> dict:
        """
        获取TradeGateway信息摘要

        Returns:
            dict: TradeGateway信息
        """
        return {
            'name': self._gateway_name,
            'pending_orders': self.get_pending_order_count(),
            'processing_orders': self.get_tracked_order_count(),
            'execution_history': self.get_execution_history_count(),
            'has_engine_binding': hasattr(self, 'bound_engine') and self.bound_engine is not None,
        }