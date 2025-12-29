# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 实现 ITimeProvider、ITimeAwareComponent 等类的核心功能，封装相关业务逻辑






"""
时间控制接口定义

定义统一的时间语义和时间感知组件接口，确保系统内时间一致性。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Callable
from ginkgo.enums import TIME_MODE


class ITimeProvider(ABC):
    """时间提供者接口
    
    系统中唯一的时间权威，所有时间获取必须通过此接口。
    避免组件直接使用datetime.now()造成时间不一致。
    """
    
    @abstractmethod
    def now(self) -> datetime:
        """获取当前时间"""
        pass
    
    @abstractmethod
    def get_mode(self) -> TIME_MODE:
        """获取时间模式"""
        pass
    
    @abstractmethod
    def set_current_time(self, timestamp: datetime) -> None:
        """设置当前时间（仅逻辑时间模式有效）"""
        pass
    
    @abstractmethod
    def advance_time_to(self, target_time: datetime) -> None:
        """推进时间到指定时间点（仅逻辑时间模式有效）"""
        pass
    
    @abstractmethod
    def can_access_time(self, requested_time: datetime) -> bool:
        """检查是否可以访问指定时间的数据（防未来数据泄露）"""
        pass


class ITimeAwareComponent(ABC):
    """时间感知组件接口
    
    需要时间同步的组件必须实现此接口，以便接收时间更新通知。
    """
    
    @abstractmethod
    def set_time_provider(self, time_provider: ITimeProvider) -> None:
        """设置时间提供者"""
        pass
    
    @abstractmethod
    def on_time_update(self, new_time: datetime) -> None:
        """时间更新通知回调"""
        pass
    
    @abstractmethod
    def get_current_time(self) -> datetime:
        """获取当前时间"""
        pass


