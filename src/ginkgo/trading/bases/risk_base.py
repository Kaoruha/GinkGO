# Upstream: Portfolio Manager (添加Risk实例到Portfolio)、Concrete Risk Classes (PositionRatioRisk/LossLimitRisk/ProfitLimitRisk继承)
# Downstream: TimeMixin/ContextMixin/EngineBindableMixin/NamedMixin/LoggableMixin (5个Mixin提供时间/上下文/引擎绑定/命名/日志能力)、Base
# Role: RiskBase风控抽象基类组合5个Mixin提供完整能力定义双重风控机制被动拦截订单和主动生成信号
# ADR-001(组件边界): Risk 仅拦截 / 调整订单（减量或拒绝），禁止增加订单量






"""
风控组件基类

组合时间、上下文和引擎绑定能力，为所有风控组件提供基础功能
"""

from typing import List, Dict, Any, TYPE_CHECKING
from ginkgo.entities.base import Base
from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import ContextMixin
from ginkgo.entities.mixins import EngineBindableMixin
from ginkgo.entities.mixins import NamedMixin

if TYPE_CHECKING:
    from ginkgo.entities import Order
    from ginkgo.entities import Signal
    from ginkgo.trading.events.base_event import EventBase


class RiskBase(TimeMixin, ContextMixin, EngineBindableMixin, NamedMixin, Base):
    """
    风控组件基类

    组合时间、上下文和引擎绑定能力，为所有风控组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, task_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 组件基础功能 (uuid, component_type, dataframe转换)

    双重风控机制：
    - cal(): 被动拦截。Portfolio 收到 Strategy 的订单后，依次通过每个
      RiskManager.cal()，风控可调整 volume、拒绝订单或放行。数据流：
      Strategy → Signal → Order → Risk.cal() → 调整后 Order
    - generate_signals(): 主动信号。每次价格事件到达时，Portfolio 调用
      每个 RiskManager.generate_signals()，风控可主动生成平仓信号（如
      止损、止盈）。数据流：EventPriceUpdate → Risk.generate_signals() → Signal

    与 Strategy 的区别：
    - Strategy.cal() 根据行情决定"买什么"，输出信号
    - Risk.cal() 根据已有订单决定"能不能买"，调整或拦截
    - Risk.generate_signals() 根据行情决定"要不要卖"，输出风控信号
    """

    def __init__(self, name: str = "risk", engine=None, **kwargs):
        """
        初始化风控基类

        Args:
            name: 风控组件名称
            engine: 可选的引擎实例，如果提供则直接绑定
            **kwargs: 传递给父类的参数
        """
        super().__init__(name=name, engine=engine, **kwargs)
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

    def create_signal(self, code: str, direction, reason: str = "",
                      volume: int = 0, weight: float = 0.0,
                      strength: float = 0.5, confidence: float = 0.5,
                      **kwargs):
        """
        创建带有完整上下文的风控信号。

        自动填充 portfolio_id、engine_id、task_id，风控组件只需关注业务参数。
        """
        from ginkgo.entities import Signal

        return Signal(
            portfolio_id=self.portfolio_id or "",
            engine_id=self.engine_id or "",
            task_id=self.task_id or "",
            code=code,
            direction=direction,
            reason=reason,
            volume=volume,
            weight=weight,
            strength=strength,
            confidence=confidence,
            **kwargs,
        )