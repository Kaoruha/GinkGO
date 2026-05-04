# Upstream: PortfolioBase, Position实体
# Downstream: entities.base.Base, entities.mixins.TimeMixin, entities.mixins.ContextMixin
# Role: 持仓组件抽象基类，组合时间戳管理和上下文管理能力，为所有持仓组件提供uuid、component_type等基础功能






"""
持仓组件基类

组合时间和上下文管理能力，为所有持仓组件提供基础功能
"""

from ginkgo.entities.base import Base
from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import ContextMixin


class PositionBase(TimeMixin, ContextMixin, Base):
    """
    持仓组件基类

    组合时间和上下文管理能力，为所有持仓组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, task_id, portfolio_id)
    - 引擎上下文同步 (sync_engine_context)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, **kwargs):
        """
        初始化持仓基类

        Args:
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
