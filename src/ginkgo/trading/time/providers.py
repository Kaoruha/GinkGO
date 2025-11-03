"""
时间提供者实现

包含逻辑时间提供者（回测用）和系统时间提供者（实盘用）的具体实现。
"""

import pytz
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional, Set
from .interfaces import ITimeProvider, ITimeAwareComponent
from ginkgo.enums import TIME_MODE


class LogicalTimeProvider(ITimeProvider):
    """逻辑时间提供者
    
    用于回测场景，提供可控的逻辑时间推进功能。
    确保回测过程中时间流逝的确定性和可重复性。
    """
    
    def __init__(self, initial_time: datetime, end_time: datetime = None, timezone_info: timezone = timezone.utc):
        """初始化逻辑时间提供者

        Args:
            initial_time: 初始时间（回测起始时间）
            end_time: 结束时间（回测结束时间），可选
            timezone_info: 时区信息，默认UTC
        """
        self._current_time = initial_time.replace(tzinfo=timezone_info) if initial_time.tzinfo is None else initial_time
        self._start_time = self._current_time
        self._end_time = end_time.replace(tzinfo=timezone_info) if end_time and end_time.tzinfo is None else end_time
        self._timezone = timezone_info
        self._mode = TIME_MODE.LOGICAL
        
    def now(self) -> datetime:
        """获取当前逻辑时间"""
        return self._current_time
    
    def get_mode(self) -> TIME_MODE:
        """获取时间模式"""
        return self._mode
    
    def set_current_time(self, timestamp: datetime) -> bool:
        """设置当前逻辑时间

        Args:
            timestamp: 要设置的时间戳

        Returns:
            bool: True=设置成功，False=时间倒退被拒绝
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=self._timezone)

        if timestamp < self._current_time:
            # 记录错误日志，不抛异常
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"Time regression rejected. Current: {self._current_time}, Requested: {timestamp}")
            return False

        self._current_time = timestamp
        return True
    
    def advance_time_to(self, target_time: datetime) -> None:
        """推进时间到目标时间点
        
        Args:
            target_time: 目标时间点
            
        Raises:
            ValueError: 如果目标时间早于当前时间
        """
        self.set_current_time(target_time)
    
    def can_access_time(self, requested_time: datetime) -> bool:
        """检查是否可以访问指定时间的数据

        在逻辑时间模式下，只能访问当前时间及之前的数据，防止未来数据泄露。

        Args:
            requested_time: 请求访问的时间点

        Returns:
            bool: 是否允许访问
        """
        if requested_time.tzinfo is None:
            requested_time = requested_time.replace(tzinfo=self._timezone)
        return requested_time <= self._current_time

    # ==== 配置方法：动态设置时间范围 ====
    def set_start_time(self, start_time: datetime) -> None:
        """设置回测起始时间

        Args:
            start_time: 起始时间
        """
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=self._timezone)
        self._start_time = start_time
        # 如果当前时间早于新的起始时间，重置当前时间
        if self._current_time < start_time:
            self._current_time = start_time

    def set_end_time(self, end_time: datetime) -> None:
        """设置回测结束时间

        Args:
            end_time: 结束时间
        """
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=self._timezone)
        self._end_time = end_time

    def get_time_range(self) -> tuple[datetime, Optional[datetime]]:
        """获取时间范围

        Returns:
            tuple: (起始时间, 结束时间)，结束时间可能为None
        """
        return (self._start_time, self._end_time)

    def register_time_listener(self, listener: ITimeAwareComponent):
        """注册时间监听器

        Args:
            listener: 时间感知组件
        """
        if not hasattr(self, '_listeners'):
            self._listeners = set()
        self._listeners.add(listener)

    def unregister_time_listener(self, listener: ITimeAwareComponent):
        """注销时间监听器

        Args:
            listener: 时间感知组件
        """
        if hasattr(self, '_listeners') and listener in self._listeners:
            self._listeners.remove(listener)


class SystemTimeProvider(ITimeProvider):
    """系统时间提供者
    
    用于实盘交易场景，提供基于系统时钟的实时时间。
    支持时区处理和夏令时转换。
    """
    
    def __init__(self, timezone_info: timezone = timezone.utc):
        """初始化系统时间提供者
        
        Args:
            timezone_info: 时区信息，默认UTC
        """
        self._timezone = timezone_info
        self._mode = TIME_MODE.SYSTEM
        # 监听器集合（非接口要求，供引擎订阅时间变更）
        self._listeners: Set[ITimeAwareComponent] = set()
        # 心跳控制
        self._heartbeat_active = False
        
    def now(self) -> datetime:
        """获取当前系统时间"""
        return datetime.now(self._timezone)
    
    def get_mode(self) -> TIME_MODE:
        """获取时间模式"""
        return self._mode
    
    def set_current_time(self, timestamp: datetime) -> None:
        """设置当前时间（系统时间模式下不支持）
        
        Raises:
            NotImplementedError: 系统时间模式不支持设置时间
        """
        raise NotImplementedError("Cannot set time in system time mode")
    
    def advance_time_to(self, target_time: datetime) -> None:
        """推进时间（系统时间模式下不支持）
        
        Raises:
            NotImplementedError: 系统时间模式不支持推进时间
        """
        raise NotImplementedError("Cannot advance time in system time mode")
    
    def can_access_time(self, requested_time: datetime) -> bool:
        """检查是否可以访问指定时间的数据
        
        在系统时间模式下，只能访问当前时间及之前的数据。
        
        Args:
            requested_time: 请求访问的时间点
            
        Returns:
            bool: 是否允许访问
        """
        if requested_time.tzinfo is None:
            requested_time = requested_time.replace(tzinfo=self._timezone)
        return requested_time <= self.now()

    
    def start_heartbeat(self, interval_seconds: float = 1.0):
        """简单心跳：按需可拓展为定时回调"""
        self._heartbeat_active = True

    def stop_heartbeat(self):
        self._heartbeat_active = False

    def register_time_listener(self, listener: ITimeAwareComponent):
        """注册时间监听器

        Args:
            listener: 时间感知组件
        """
        self._listeners.add(listener)

    def unregister_time_listener(self, listener: ITimeAwareComponent):
        """注销时间监听器

        Args:
            listener: 时间感知组件
        """
        if listener in self._listeners:
            self._listeners.remove(listener)


class TimeBoundaryValidator:
    """时间边界验证器

    提供严格的时间边界检查，防止未来数据泄露和时间倒退。
    使用类级缓存（按run_id隔离）支持跨实例缓存共享，优化重复验证性能。
    """

    # 类级缓存：按run_id隔离，支持跨实例共享
    _shared_cache: dict = {}
    _default_cache_size: int = 50  # 每个run默认50个槽位

    def __init__(self, time_provider: ITimeProvider, run_id: Optional[str] = None, cache_size: Optional[int] = None):
        """初始化时间边界验证器

        Args:
            time_provider: 时间提供者实例
            run_id: 回测会话ID（用于缓存隔离，支持跨实例共享）
            cache_size: 该run的缓存大小（可选，默认50个槽位）
        """
        self._time_provider = time_provider
        self._run_id = run_id
        self._cache_size = cache_size or self.__class__._default_cache_size

        # 如果指定了run_id，初始化该run的共享缓存空间
        if run_id and run_id not in self.__class__._shared_cache:
            self.__class__._shared_cache[run_id] = OrderedDict()
        
    def validate_data_access(self, data_timestamp: datetime, context: str = "data access", request_time: Optional[datetime] = None) -> None:
        """验证数据访问的时间边界
        
        Args:
            data_timestamp: 数据时间戳
            context: 访问上下文描述（用于错误信息）
            
        Raises:
            ValueError: 如果访问未来数据
        """
        # 如指定 request_time，则以 request_time 为当前时点进行校验（用于实盘/消息时间）
        if request_time is not None:
            # 若无 tz 信息，尽量与 provider 对齐
            if request_time.tzinfo is None and hasattr(self._time_provider, 'now'):
                try:
                    tz = self._time_provider.now().tzinfo
                    if tz is not None:
                        request_time = request_time.replace(tzinfo=tz)
                except Exception:
                    pass
            if data_timestamp.tzinfo is None and hasattr(self._time_provider, 'now'):
                try:
                    tz = self._time_provider.now().tzinfo
                    if tz is not None:
                        data_timestamp = data_timestamp.replace(tzinfo=tz)
                except Exception:
                    pass
            if data_timestamp > request_time:
                current_time = request_time
                raise ValueError(
                    f"Future data access violation in {context}. "
                    f"Current time: {current_time}, Requested time: {data_timestamp}"
                )

        # 否则使用 provider 的 can_access_time 逻辑
        if not self._time_provider.can_access_time(data_timestamp):
            current_time = self._time_provider.now()
            raise ValueError(
                f"Future data access violation in {context}. "
                f"Current time: {current_time}, Requested time: {data_timestamp}"
            )

    def can_access_time(self, data_timestamp: datetime, request_time: Optional[datetime] = None) -> bool:
        """轻量校验接口：返回是否允许访问

        Args:
            data_timestamp: 数据时间戳
            request_time: 请求时间（可选，指定请求所在时点）

        Returns:
            bool: 是否允许访问
        """
        try:
            self.validate_data_access(data_timestamp, context="data access", request_time=request_time)
            return True
        except Exception:
            return False

    def validate_data_access_cached(self, data_timestamp: datetime, context: str = "data_access", request_time: Optional[datetime] = None) -> bool:
        """带缓存的时间验证（类级缓存，支持跨实例共享）

        Args:
            data_timestamp: 数据时间戳
            context: 访问上下文描述
            request_time: 请求时间（可选）

        Returns:
            bool: True表示验证通过，False表示验证失败
        """
        # 如果没有run_id，直接验证（无缓存）
        if not self._run_id:
            try:
                self.validate_data_access(data_timestamp, context=context, request_time=request_time)
                return True
            except ValueError:
                return False

        # 获取该run的共享缓存
        cache = self.__class__._shared_cache.get(self._run_id)
        if cache is None:
            # run_id不存在，初始化缓存
            cache = OrderedDict()
            self.__class__._shared_cache[self._run_id] = cache

        # 构造缓存key
        cache_key = (data_timestamp, request_time)

        # 检查缓存
        if cache_key in cache:
            return cache[cache_key]

        # 缓存未命中，执行验证
        try:
            self.validate_data_access(data_timestamp, context=context, request_time=request_time)
            result = True
        except ValueError:
            result = False

        # 写入缓存（FIFO策略）
        cache[cache_key] = result
        if len(cache) > self._cache_size:
            cache.popitem(last=False)  # 删除最老的条目

        return result

    @classmethod
    def clear_cache(cls, run_id: Optional[str] = None) -> None:
        """清空缓存

        Args:
            run_id: 如果指定，只清空该run的缓存；如果为None，清空所有缓存
        """
        if run_id is None:
            cls._shared_cache.clear()
        elif run_id in cls._shared_cache:
            del cls._shared_cache[run_id]

    @classmethod
    def get_cache_stats(cls, run_id: Optional[str] = None) -> dict:
        """获取缓存统计信息

        Args:
            run_id: 如果指定，返回该run的统计；如果为None，返回所有run的统计

        Returns:
            缓存统计信息字典
        """
        if run_id is not None:
            if run_id not in cls._shared_cache:
                return {'run_id': run_id, 'size': 0, 'max_size': cls._default_cache_size, 'usage': '0.0%'}

            cache_size = len(cls._shared_cache[run_id])
            return {
                'run_id': run_id,
                'size': cache_size,
                'max_size': cls._default_cache_size,
                'usage': f"{cache_size/cls._default_cache_size*100:.1f}%"
            }
        else:
            # 返回所有run的统计
            total_runs = len(cls._shared_cache)
            total_entries = sum(len(cache) for cache in cls._shared_cache.values())
            return {
                'total_runs': total_runs,
                'total_entries': total_entries,
                'max_size_per_run': cls._default_cache_size,
                'runs': {
                    run_id: len(cache)
                    for run_id, cache in cls._shared_cache.items()
                }
            }


class DSTHandler:
    """夏令时处理器
    
    处理夏令时转换和时区相关的时间计算。
    """
    
    @staticmethod
    def normalize_timezone(timestamp: datetime, target_tz: timezone) -> datetime:
        """标准化时区
        
        Args:
            timestamp: 原始时间戳
            target_tz: 目标时区
            
        Returns:
            datetime: 转换后的时间戳
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(target_tz)
    
    @staticmethod
    def handle_dst_transition(timestamp: datetime, timezone_name: str) -> datetime:
        """处理夏令时转换
        
        Args:
            timestamp: 时间戳
            timezone_name: 时区名称（如'US/Eastern'）
            
        Returns:
            datetime: 处理DST后的时间戳
        """
        try:
            tz = pytz.timezone(timezone_name)
            if timestamp.tzinfo is None:
                # 使用pytz的localize方法处理DST
                return tz.localize(timestamp, is_dst=None)
            else:
                return timestamp.astimezone(tz)
        except Exception as e:
            raise ValueError(f"DST handling failed for timezone {timezone_name}: {e}")
