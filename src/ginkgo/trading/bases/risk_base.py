# Upstream: Portfolio Manager (添加Risk实例到Portfolio)、Concrete Risk Classes (PositionRatioRisk/LossLimitRisk/ProfitLimitRisk继承)
# Downstream: TimeMixin/ContextMixin/EngineBindableMixin/NamedMixin/LoggableMixin (5个Mixin提供时间/上下文/引擎绑定/命名/日志能力)、Base
# Role: RiskBase风控抽象基类组合5个Mixin提供完整能力定义双重风控机制被动拦截订单和主动生成信号






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
from ginkgo.enums import SOURCE_TYPES

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
                      business_timestamp=None, source=None,
                      **kwargs):
        """
        信号发射 seam（ADR-011, #6160）：单一入口背后藏四件事，调用方只见业务参数。

        1. 构造 Signal —— 自动填 portfolio/engine/task_id
        2. business_timestamp —— 缺省 get_time_provider().now()；provider 未绑定留 None；
           调用方传值时覆盖（不查 provider）
        3. source —— 缺省 SOURCE_TYPES.RISK；调用方可覆盖
        4. ClickHouse 日志 —— 无条件 blog.signal(strategy_id=self.uuid)
           注：strategy_id 参数名历史沿用，泛指信号生成组件 uuid（Strategy/Risk 共用）；
           来源区分由 Signal.source（STRATEGY/RISK）承担。

        Args:
            code: 股票代码
            direction: 交易方向 (DIRECTION_TYPES)
            reason: 信号原因
            volume: 建议交易量
            weight: 信号权重
            strength: 信号强度
            confidence: 信号置信度
            business_timestamp: 业务时间戳；None 时取 provider.now()，provider 未绑定留 None
            source: 信号来源；None 时缺省 RISK
            **kwargs: 其他 Signal 参数

        Returns:
            Signal: 带完整上下文、source、时间戳的信号对象
        """
        from ginkgo.entities import Signal

        # source：组件拥有的值，缺省 RISK，可覆盖（值归组件原则）
        if source is None:
            source = SOURCE_TYPES.RISK

        # business_timestamp：provider 有则取 now()，无则留 None（三层契约支撑）
        if business_timestamp is None:
            provider = self.get_time_provider()
            if provider is not None:
                business_timestamp = provider.now()

        signal = Signal(
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
            source=source,
            business_timestamp=business_timestamp,
            **kwargs,
        )

        # ClickHouse 信号日志：框架拥有的基础设施，无条件（ADR-011）
        self.blog.signal(
            symbol=code,
            direction=direction.value if hasattr(direction, 'value') else str(direction),
            signal_reason=reason,
            strategy_id=self.uuid,
            msg=reason,
        )
        return signal