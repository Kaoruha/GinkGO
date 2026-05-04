# Upstream: Portfolio(添加资金管理组件)、Strategy(策略使用Sizer计算订单大小)
# Downstream: TimeMixin/ContextMixin/EngineBindableMixin/NamedMixin/LoggableMixin(5个Mixin提供时间/上下文/引擎绑定/命名/日志能力)、Base(组件基础)、Signal/Order实体(类型注解)
# Role: SizerBase资金管理组件基类组合5个Mixin定义数据供给器和cal抽象方法计算订单大小






"""
资金管理组件基类

组合时间、上下文和引擎绑定能力，为所有资金管理组件提供基础功能
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from ginkgo.entities.base import Base
from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import ContextMixin
from ginkgo.entities.mixins import EngineBindableMixin
from ginkgo.entities.mixins import NamedMixin

if TYPE_CHECKING:
    from ginkgo.entities import Signal
    from ginkgo.entities import Order


class SizerBase(TimeMixin, ContextMixin, EngineBindableMixin, NamedMixin, Base):
    """
    资金管理组件基类

    组合时间、上下文和引擎绑定能力，为所有资金管理组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, task_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, name: str = "sizer", engine=None, **kwargs):
        """
        初始化资金管理基类

        Args:
            name: 资金管理组件名称
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

    def create_order(self, code: str, direction, volume: int,
                     limit_price=0, order_type=None, status=None,
                     frozen_money=0, frozen_volume=0,
                     transaction_price=0, transaction_volume=0,
                     remain=0, fee=0, **kwargs):
        """
        创建带有完整上下文的订单。

        自动填充 portfolio_id、engine_id、task_id，仓位管理器只需关注业务参数。
        """
        from ginkgo.entities import Order
        from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES

        if order_type is None:
            order_type = ORDER_TYPES.MARKETORDER
        if status is None:
            status = ORDERSTATUS_TYPES.NEW

        return Order(
            portfolio_id=self.portfolio_id or "",
            engine_id=self.engine_id or "",
            task_id=self.task_id or "",
            code=code,
            direction=direction,
            order_type=order_type,
            status=status,
            volume=volume,
            limit_price=limit_price,
            frozen_money=frozen_money,
            frozen_volume=frozen_volume,
            transaction_price=transaction_price,
            transaction_volume=transaction_volume,
            remain=remain,
            fee=fee,
            **kwargs,
        )

    def cal(self, portfolio_info: Dict, signal: "Signal", *args, **kwargs) -> Optional["Order"]:
        """
        计算订单大小（抽象方法，需要子类实现）

        Args:
            portfolio_info(Dict): 投资组合信息
            signal(Signal): 交易信号
            *args: 额外参数
            **kwargs: 额外关键字参数

        Returns:
            Optional[Order]: 计算得出的订单，如果不应该交易则返回None
        """
        # 默认实现返回None，子类必须重写此方法
        return None
