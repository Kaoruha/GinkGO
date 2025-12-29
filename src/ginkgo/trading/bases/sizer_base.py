# Upstream: Portfolio(添加资金管理组件)、Strategy(策略使用Sizer计算订单大小)
# Downstream: TimeMixin/ContextMixin/EngineBindableMixin/NamedMixin/LoggableMixin(5个Mixin提供时间/上下文/引擎绑定/命名/日志能力)、Base(组件基础)、Signal/Order实体(类型注解)
# Role: SizerBase资金管理组件基类组合5个Mixin定义数据供给器和cal抽象方法计算订单大小支持交易系统功能和组件集成提供完整业务支持






"""
资金管理组件基类

组合时间、上下文和引擎绑定能力，为所有资金管理组件提供基础功能
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin

if TYPE_CHECKING:
    from ginkgo.trading.entities.signal import Signal
    from ginkgo.trading.entities.order import Order


class SizerBase(TimeMixin, ContextMixin, EngineBindableMixin, NamedMixin, LoggableMixin, Base):
    """
    资金管理组件基类

    组合时间、上下文和引擎绑定能力，为所有资金管理组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 日志管理 (log, add_logger)
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