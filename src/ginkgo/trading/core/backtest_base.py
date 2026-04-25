from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.libs import GLOG, base_repr
from ginkgo.entities.base import Base


class BacktestBase(Base):
    """
    Enhanced Backtest Base Class with Unified 3-Tier ID Management

    提供统一的三层ID管理：
    - uuid: 组件实例唯一标识（继承自Base）
    - engine_id: 引擎装配关系标识
    - portfolio_id: 投资组合标识
    - task_id: 执行会话标识

    注意：ID管理已移至ContextMixin，避免MRO冲突。
    注意：name管理已移至NamedMixin，避免MRO冲突。
    注意：引擎绑定已移至EngineBindableMixin，避免MRO冲突。
    组件应通过继承对应Mixin获得这些能力。
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        try:
            return f"<{self.__class__.__name__} name={getattr(self, '_name', 'Unknown')} id={id(self)}>"
        except Exception:
            return f"<{self.__class__.__name__} id={id(self)}>"
