"""
数据馈送接口定义

定义统一的数据馈送接口，支持回测和实盘两种模式：
- IDataFeeder: 核心数据馈送接口
- ILiveDataFeeder: 实盘数据馈送扩展接口
- IBacktestDataFeeder: 回测数据馈送扩展接口

这些接口确保回测与实盘数据馈送的一致性。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable, Generator
from datetime import datetime, date, timedelta
from enum import Enum

from ginkgo.trading.events import EventBase, EventPriceUpdate
from ginkgo.trading.time.interfaces import ITimeProvider
from ginkgo.trading.time.providers import TimeBoundaryValidator


class DataFeedStatus(Enum):
    """数据馈送状态"""
    IDLE = "IDLE"           # 空闲状态
    CONNECTING = "CONNECTING"   # 连接中
    CONNECTED = "CONNECTED"     # 已连接
    STREAMING = "STREAMING"     # 数据流中
    DISCONNECTED = "DISCONNECTED"  # 已断开
    ERROR = "ERROR"         # 错误状态


class IDataFeeder(ABC):
    """
    数据馈送核心接口
    
    定义所有数据馈送器必须实现的基本功能，包括：
    - 时间控制集成
    - 事件发布机制
    - 交易日历支持
    """
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化数据馈送器
        
        Args:
            config: 配置参数
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        启动数据馈送
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        停止数据馈送
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    def get_status(self) -> DataFeedStatus:
        """
        获取当前状态
        
        Returns:
            DataFeedStatus: 当前状态
        """
        pass
    
    @abstractmethod
    def set_event_publisher(self, publisher: Callable[[EventBase], None]) -> None:
        """
        设置事件发布器
        
        Args:
            publisher: 事件发布函数
        """
        pass
    
    @abstractmethod
    def set_time_provider(self, time_provider: ITimeProvider) -> None:
        """
        设置时间提供者

        Args:
            time_provider: 时间提供者接口
        """
        pass

    @abstractmethod
    def validate_time_access(self, request_time: datetime, data_time: datetime) -> bool:
        """
        验证时间访问权限（防止未来数据泄露）
        
        Args:
            request_time: 请求时间
            data_time: 数据时间
            
        Returns:
            bool: 是否允许访问
        """
        pass


class IBacktestDataFeeder(IDataFeeder):
    """
    回测数据馈送接口
    
    扩展核心接口，添加回测特有的功能：
    - 时间推进控制
    - 历史数据查询
    - 模拟数据生成
    """
    
    def advance_time(self, target_time: datetime, *args, **kwargs) -> bool:
        """
        推进到指定时间，主动推送事件到引擎

        Args:
            target_time: 目标时间

        Returns:
            bool: 是否成功推进时间
        """
        pass
    
    @abstractmethod
    def get_historical_data(self, 
                          symbols: List[str], 
                          start_time: datetime, 
                          end_time: datetime,
                          data_type: str = "bar") -> Dict[str, List[Any]]:
        """
        获取历史数据
        
        Args:
            symbols: 股票代码列表
            start_time: 开始时间
            end_time: 结束时间
            data_type: 数据类型（bar/tick）
            
        Returns:
            Dict[str, List[Any]]: 历史数据
        """
        pass

    @abstractmethod
    def get_data_range(self) -> tuple[datetime, datetime]:
        """
        获取数据时间范围
        
        Returns:
            tuple[datetime, datetime]: (开始时间, 结束时间)
        """
        pass


class ILiveDataFeeder(IDataFeeder):
    """
    实盘数据馈送接口
    
    扩展核心接口，添加实盘特有的功能：
    - 实时数据订阅
    - 连接管理
    - 断线重连
    - 限流控制
    """
    
    @abstractmethod
    def subscribe_symbols(self, symbols: List[str], data_types: List[str] = None) -> bool:
        """
        订阅股票数据
        
        Args:
            symbols: 股票代码列表
            data_types: 数据类型列表（tick/bar/order_book等）
            
        Returns:
            bool: 订阅是否成功
        """
        pass
    
    @abstractmethod
    def unsubscribe_symbols(self, symbols: List[str], data_types: List[str] = None) -> bool:
        """
        取消订阅股票数据
        
        Args:
            symbols: 股票代码列表  
            data_types: 数据类型列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        pass
    
    @abstractmethod
    def start_subscription(self) -> bool:
        """
        开始订阅数据流
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop_subscription(self) -> bool:
        """
        停止订阅数据流
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息
        
        Returns:
            Dict[str, Any]: 连接状态信息
        """
        pass
    
    @abstractmethod
    def reconnect(self, max_attempts: int = 3, delay_seconds: float = 1.0) -> bool:
        """
        重新连接
        
        Args:
            max_attempts: 最大重试次数
            delay_seconds: 重试延迟秒数
            
        Returns:
            bool: 重连是否成功
        """
        pass
    
    @abstractmethod
    def set_rate_limiter(self, requests_per_second: float) -> None:
        """
        设置请求限流
        
        Args:
            requests_per_second: 每秒请求数限制
        """
        pass
    
    @abstractmethod
    def get_subscribed_symbols(self) -> List[str]:
        """
        获取已订阅的股票列表
        
        Returns:
            List[str]: 已订阅的股票代码
        """
        pass
