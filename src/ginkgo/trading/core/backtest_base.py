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
                 component_type: str = "", engine_id: str = "",
                 portfolio_id: str = "", run_id: str = "",
                 *args, **kwargs) -> None:
        # 初始化基类，支持组件类型
        super().__init__(uuid=uuid_str, component_type=component_type, *args, **kwargs)

        # 统一的三层ID管理
        self._engine_id: str = engine_id or ""
        self._portfolio_id: str = portfolio_id or ""
        self._run_id: str = run_id or ""

        self._engine_put = None
        self.set_name(str(name))
        self.loggers = []
        self.add_logger(GLOG)

    

    
    def bind_engine(self, engine: "BaseEngine") -> None:
        """
        绑定到引擎，同步引擎层面的ID信息（engine_id, run_id）

        注意：portfolio_id由投资组合层面管理，不从引擎同步

        Args:
            engine (BaseEngine): 要绑定的引擎实例

        Raises:
            ValueError: 如果引擎无效或缺少必要属性
        """
        # 验证引擎必要属性
        if not hasattr(engine, "put"):
            raise ValueError("Invalid engine: missing required attribute 'put'.")

        # 同步引擎ID
        if hasattr(engine, "engine_id") and engine.engine_id:
            self._engine_id = engine.engine_id
        elif hasattr(engine, "uuid") and engine.uuid:
            # 备用方案：使用引擎的UUID
            self._engine_id = engine.uuid
        else:
            raise ValueError("Invalid engine: missing engine_id or uuid.")

        # 同步运行ID（如果引擎已启动）
        if hasattr(engine, "run_id") and engine.run_id:
            self._run_id = engine.run_id

        # 保存引擎的事件发布函数
        self._engine_put = engine.put

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
        return base_repr(self, self._name, 12, 60)
