"""
引擎状态查询接口定义

定义用于查询引擎状态、事件统计、时间信息和组件同步的标准化数据类。
这些接口支持公共API查询，避免依赖私有实现细节。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Union

from ginkgo.enums import EXECUTION_MODE, TIME_MODE, ENGINESTATUS_TYPES


@dataclass
class EngineStatus:
    """引擎基础状态信息"""
    is_running: bool                    # 引擎是否在运行
    current_time: Optional[datetime]    # 当前时间
    execution_mode: Optional[EXECUTION_MODE] = None  # 执行模式
    processed_events: int = 0           # 已处理事件数
    queue_size: int = 0                  # 事件队列大小
    status: ENGINESTATUS_TYPES = ENGINESTATUS_TYPES.IDLE  # 引擎状态枚举


@dataclass
class EventStats:
    """事件处理统计信息"""
    processed_events: int               # 已处理事件数
    registered_handlers: int           # 已注册处理器数
    queue_size: int                     # 事件队列大小
    processing_rate: float = 0.0        # 处理速率（事件/秒）


@dataclass
class QueueInfo:
    """事件队列信息"""
    queue_size: int                      # 队列大小
    max_size: int                        # 队列最大容量
    is_full: bool = False                # 队列是否已满
    is_empty: bool = True               # 队列是否为空


@dataclass
class TimeInfo:
    """时间相关信息"""
    current_time: Optional[datetime]       # 当前时间（逻辑或实时）
    time_mode: TIME_MODE                  # 时间模式
    time_provider_type: str               # 时间提供者类型
    is_logical_time: bool                 # 是否为逻辑时间
    logical_start_time: Optional[datetime] = None  # 逻辑时间开始时间
    time_advancement_count: int = 0       # 时间推进次数


@dataclass
class ComponentSyncInfo:
    """组件同步状态信息"""
    component_id: str                    # 组件ID
    component_type: str                  # 组件类型
    is_synced: bool                      # 是否已同步
    last_sync_time: Optional[datetime]   # 最后同步时间
    sync_count: int = 0                  # 同步次数
    sync_error_count: int = 0            # 同步错误次数
    is_registered: bool = True           # 是否已注册