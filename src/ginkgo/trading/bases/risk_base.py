# Upstream: Portfolio Manager (添加Risk实例到Portfolio)、Concrete Risk Classes (PositionRatioRisk/LossLimitRisk/ProfitLimitRisk继承)
# Downstream: TimeMixin/ContextMixin/EngineBindableMixin/NamedMixin/LoggableMixin (5个Mixin提供时间/上下文/引擎绑定/命名/日志能力)、Base
# Role: RiskBase风控抽象基类组合5个Mixin提供完整能力定义双重风控机制被动拦截订单和主动生成信号






"""
风控组件基类

组合时间、上下文和引擎绑定能力，为所有风控组件提供基础功能
"""

from typing import List, Dict, Any, TYPE_CHECKING
from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin

if TYPE_CHECKING:
    from ginkgo.trading.entities.order import Order
    from ginkgo.trading.entities.signal import Signal
    from ginkgo.trading.events.base_event import EventBase


class RiskBase(TimeMixin, ContextMixin, EngineBindableMixin, NamedMixin, LoggableMixin, Base):
    """
    风控组件基类

    组合时间、上下文和引擎绑定能力，为所有风控组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 日志管理 (log, add_logger)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, name: str = "risk", engine=None, **kwargs):
        """
        初始化风控基类

        Args:
            name: 风控组件名称
            engine: 可选的引擎实例，如果提供则直接绑定
            **kwargs: 传递给父类的参数
        """
        # 显式初始化各个Mixin，确保正确的初始化顺序
        TimeMixin.__init__(self, **kwargs)
        ContextMixin.__init__(self, **kwargs)
        EngineBindableMixin.__init__(self, engine=engine, **kwargs)
        NamedMixin.__init__(self, name=name, **kwargs)
        LoggableMixin.__init__(self, **kwargs)
        Base.__init__(self)
        self._data_feeder = None

    def bind_data_feeder(self, feeder: Any, *args, **kwargs) -> None:
        """
        绑定数据供给器

        Args:
            feeder: 数据供给器实例
        """
        self._data_feeder = feeder

    def cal(self, portfolio_info: Dict, order: "Order") -> "Order":
        """
        风控订单处理
        接收投资组合信息和订单，返回处理后的订单

        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单

        Returns:
            Order: 处理后的订单，默认直接返回原订单
        """
        # 默认实现直接返回原订单，子类可以重写实现具体风控逻辑
        return order

    def generate_signals(self, portfolio_info: Dict, event: "EventBase") -> List["Signal"]:
        """
        风控信号生成
        接收到Event后主动生成风控信号来控制仓位

        Args:
            portfolio_info(Dict): 投资组合信息
            event(EventBase): 收到的事件

        Returns:
            List[Signal]: 风控信号列表，默认返回空列表
        """
        # 默认实现不生成信号，子类可以重写实现主动风控逻辑
        return []