from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.libs import GLOG, base_repr
from ginkgo.trading.core.base import Base


class BacktestBase(Base):
    """
    Enhanced Backtest Base Class with Unified 3-Tier ID Management

    提供统一的三层ID管理：
    - uuid: 组件实例唯一标识（继承自Base）
    - engine_id: 引擎装配关系标识
    - portfolio_id: 投资组合标识
    - run_id: 执行会话标识
    """

    def __init__(self, name: str = "backtest_base", uuid_str: str = "",
                 component_type: str = "", *args, **kwargs) -> None:
        # 初始化基类，支持组件类型
        super().__init__(uuid=uuid_str, component_type=component_type, *args, **kwargs)

        # 注意：ID管理已移至ContextMixin，避免MRO冲突
        # 组件应该通过继承ContextMixin来获得ID管理功能

        self._engine_put = None
        self.set_name(str(name))
        self.loggers = []
        self.add_logger(GLOG)

    

    
    # 注意：bind_engine功能已移至EngineBindableMixin，避免MRO冲突
    # 组件应该通过继承EngineBindableMixin来获得引擎绑定功能

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    def set_name(self, name: str) -> str:
        """
        Update the instance name.

        Args:
            name (str): New name for the instance.

        Returns:
            str: The updated name.
        """
        self._name = name
        return self.name


    def add_logger(self, logger) -> None:
        if logger in self.loggers:
            return
        self.loggers.append(logger)

    def reset_logger(self) -> None:
        self.loggers = []

    def log(self, level: str, msg: str, *args, **kwargs) -> None:
        level_up = level.upper()
        if level_up == "DEBUG":
            for i in self.loggers:
                i.DEBUG(msg)
        elif level_up == "INFO":
            for i in self.loggers:
                i.INFO(msg)
        elif level_up == "WARNING":
            for i in self.loggers:
                i.WARN(msg)
        elif level_up == "ERROR":
            for i in self.loggers:
                i.ERROR(msg)
        elif level_up == "CRITICAL":
            for i in self.loggers:
                i.CRITICAL(msg)
        else:
            pass


    def __repr__(self) -> str:
        # Safe repr that avoids circular references
        try:
            return f"<{self.__class__.__name__} name={getattr(self, '_name', 'Unknown')} id={id(self)}>"
        except Exception:
            return f"<{self.__class__.__name__} id={id(self)}>"
