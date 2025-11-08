"""
选股组件基类

组合时间、上下文和名称管理能力，为所有选股组件提供基础功能
"""

from typing import Any
from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin


class SelectorBase(TimeMixin, ContextMixin, NamedMixin, LoggableMixin, Base):
    """
    选股组件基类

    组合时间、上下文和名称管理能力，为所有选股组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 名称管理 (name)
    - 日志管理 (log, add_logger)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, name: str = "selector", **kwargs):
        """
        初始化选股基类

        Args:
            name: 选股组件名称
            **kwargs: 传递给父类的参数
        """
        # 显式初始化各个Mixin，确保正确的初始化顺序
        TimeMixin.__init__(self, **kwargs)
        ContextMixin.__init__(self, **kwargs)
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

    def pick(self, time: Any = None, *args, **kwargs) -> list[str]:
        """
        选股方法（抽象方法，需要子类实现）

        Args:
            time: 时间参数
            *args: 额外参数
            **kwargs: 额外关键字参数

        Returns:
            list[str]: 选中的股票代码列表
        """
        # 默认实现返回空列表，子类应该重写此方法
        return []