# Upstream: Portfolio Manager
# Downstream: Analyzers (BaseAnalyzer subclasses)
# Role: 定义 PortfolioInfo Protocol，约束传递给分析器的 portfolio_info 字典结构


from typing import Protocol, runtime_checkable, Dict, Any, Optional
from datetime import datetime


@runtime_checkable
class PortfolioInfo(Protocol):
    """协议约束 portfolio_info 字典的字段结构。

    对应 PortfolioBase.get_info() 返回的字典。
    分析器通过此协议获得类型提示和 IDE 自动补全支持。
    """

    @property
    def name(self) -> str: ...
    @property
    def now(self) -> Optional[datetime]: ...
    @property
    def uuid(self) -> str: ...
    @property
    def mode(self) -> Any: ...
    @property
    def state(self) -> Any: ...
    @property
    def cash(self) -> Any: ...
    @property
    def frozen(self) -> Any: ...
    @property
    def profit(self) -> Any: ...
    @property
    def worth(self) -> Any: ...
    @property
    def positions(self) -> Dict[str, Any]: ...
    @property
    def selector(self) -> Any: ...
    @property
    def portfolio_id(self) -> str: ...
    @property
    def engine_id(self) -> str: ...
    @property
    def task_id(self) -> str: ...
    @property
    def available_cash(self) -> float: ...
    @property
    def total_value(self) -> float: ...
    @property
    def current_time(self) -> Optional[datetime]: ...


def check_portfolio_info(info: Dict[str, Any]) -> bool:
    """运行时检查字典是否符合 PortfolioInfo 协议。"""
    required_keys = {
        'name', 'uuid', 'cash', 'frozen', 'profit', 'worth',
        'positions', 'portfolio_id', 'engine_id', 'task_id',
    }
    return required_keys.issubset(info.keys())
