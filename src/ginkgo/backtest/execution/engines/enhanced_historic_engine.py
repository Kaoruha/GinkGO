"""
增强版历史回测引擎 - 优化性能和内存使用
"""

import datetime
import sys
from time import sleep
from queue import Queue, Empty, PriorityQueue
from threading import Thread, Event
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import psutil
import gc

from ginkgo.backtest.execution.engines.historic_engine import HistoricEngine
from ginkgo.backtest.execution.events.base_event import EventBase
from ginkgo.libs import GLOG, time_logger, GCONF
from ginkgo.enums import EVENT_TYPES


@dataclass
class PerformanceMetrics:
    """性能指标"""
    events_processed: int = 0
    avg_processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    queue_size: int = 0
    cpu_usage_percent: float = 0.0


class EventCache:
    """事件缓存管理器"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.usage_count = {}
        self.access_order = []
    
    def get(self, key: str) -> Optional[EventBase]:
        """获取缓存的事件"""
        if key in self.cache:
            self.usage_count[key] += 1
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, event: EventBase):
        """缓存事件"""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[key] = event
        self.usage_count[key] = 1
        self.access_order.append(key)
    
    def _evict_lru(self):
        """移除最近最少使用的事件"""
        if self.access_order:
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]
            del self.usage_count[lru_key]
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.usage_count.clear()
        self.access_order.clear()


class EventBatch:
    """事件批处理器"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.current_batch = []
        
    def add_event(self, event: EventBase) -> bool:
        """添加事件到批次，返回是否批次已满"""
        self.current_batch.append(event)
        return len(self.current_batch) >= self.batch_size
    
    def get_batch(self) -> List[EventBase]:
        """获取当前批次并清空"""
        batch = self.current_batch.copy()
        self.current_batch.clear()
        return batch
    
    def has_events(self) -> bool:
        """检查是否有待处理事件"""
        return len(self.current_batch) > 0


class EnhancedHistoricEngine(HistoricEngine):
    """增强版历史回测引擎"""
    
    def __init__(
        self, 
        name: str = "EnhancedHistoricEngine",
        interval: int = 1,
        enable_caching: bool = True,
        enable_batching: bool = True,
        batch_size: int = 100,
        cache_size: int = 10000,
        memory_limit_mb: int = 1000,
        *args, 
        **kwargs
    ):
        super().__init__(name, interval, *args, **kwargs)
        
        # 性能优化配置
        self.enable_caching = enable_caching
        self.enable_batching = enable_batching
        self.memory_limit_mb = memory_limit_mb
        
        # 缓存和批处理
        self.event_cache = EventCache(cache_size) if enable_caching else None
        self.event_batch = EventBatch(batch_size) if enable_batching else None
        
        # 性能监控
        self.performance_metrics = PerformanceMetrics()
        self.last_gc_time = datetime.datetime.now()
        self.gc_interval = datetime.timedelta(minutes=5)  # 5分钟GC一次
        
        # 优化的事件队列 - 使用优先队列
        self._priority_queue = PriorityQueue()
        self._use_priority_queue = True
        
        # 时间钩子优化
        self._time_hooks = []
        self._time_hook_cache = {}
        
    def set_config(self, config):
        """设置配置参数"""
        if hasattr(config, 'start_date'):
            self.start_date = config.start_date
        if hasattr(config, 'end_date'):
            self.end_date = config.end_date
        if hasattr(config, 'sleep_interval'):
            self._sleep_interval = config.sleep_interval
        if hasattr(config, 'enable_tick_data'):
            self._enable_tick_data = config.enable_tick_data
    
    def put_event(self, event: EventBase, priority: int = 5):
        """将事件放入队列，支持优先级"""
        if self._use_priority_queue:
            # 优先级队列：数字越小优先级越高
            self._priority_queue.put((priority, datetime.datetime.now(), event))
        else:
            self._queue.put(event)
    
    def get_event(self, timeout: float = 0.05) -> Optional[EventBase]:
        """从队列获取事件"""
        try:
            if self._use_priority_queue:
                priority, timestamp, event = self._priority_queue.get(block=True, timeout=timeout)
                return event
            else:
                return self._queue.get(block=True, timeout=timeout)
        except Empty:
            return None
    
    @time_logger
    def main_loop(self, flag: Event) -> None:
        """增强版主循环"""
        if not isinstance(flag, Event):
            self.log("ERROR", f"{self.name} main_loop: flag must be an instance of threading.Event.")
            return
        
        consecutive_empty_count = 0
        last_metrics_update = datetime.datetime.now()
        metrics_update_interval = datetime.timedelta(seconds=30)
        
        self.log("INFO", f"Starting enhanced main loop for {self.name}")
        
        while self._active:
            if flag.is_set():
                break
            
            try:
                # 批处理模式
                if self.enable_batching:
                    events_processed = self._process_event_batch()
                else:
                    # 单事件处理模式
                    event = self.get_event()
                    if event:
                        self._process_enhanced(event)
                        events_processed = 1
                    else:
                        events_processed = 0
                
                if events_processed > 0:
                    consecutive_empty_count = 0
                    self.performance_metrics.events_processed += events_processed
                else:
                    consecutive_empty_count += 1
                    self.next_phase()
                
            except Exception as e:
                self.log("ERROR", f"Error in main loop: {e}")
                consecutive_empty_count += 1
            
            # 动态休眠策略
            sleep_time = self._calculate_adaptive_sleep(consecutive_empty_count)
            sleep(sleep_time)
            
            # 定期更新性能指标
            now = datetime.datetime.now()
            if now - last_metrics_update > metrics_update_interval:
                self._update_performance_metrics()
                last_metrics_update = now
            
            # 内存管理
            self._manage_memory()
        
        self.log("INFO", f"Enhanced main loop ended for {self.name}")
    
    def _process_event_batch(self) -> int:
        """批处理事件"""
        batch_processed = 0
        start_time = datetime.datetime.now()
        
        # 收集一批事件
        while not self.event_batch.has_events() or batch_processed < self.event_batch.batch_size:
            event = self.get_event(timeout=0.01)  # 短超时
            if event is None:
                break
            
            if self.event_batch.add_event(event):
                # 批次已满，开始处理
                break
        
        # 处理批次中的事件
        if self.event_batch.has_events():
            batch = self.event_batch.get_batch()
            
            # 按事件类型分组处理以提高效率
            grouped_events = self._group_events_by_type(batch)
            
            for event_type, events in grouped_events.items():
                batch_processed += self._process_event_group(event_type, events)
        
        # 更新平均处理时间
        if batch_processed > 0:
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            self._update_avg_processing_time(processing_time, batch_processed)
        
        return batch_processed
    
    def _group_events_by_type(self, events: List[EventBase]) -> Dict[EVENT_TYPES, List[EventBase]]:
        """按事件类型分组"""
        grouped = {}
        for event in events:
            event_type = event.event_type
            if event_type not in grouped:
                grouped[event_type] = []
            grouped[event_type].append(event)
        return grouped
    
    def _process_event_group(self, event_type: EVENT_TYPES, events: List[EventBase]) -> int:
        """批量处理同类型事件"""
        processed_count = 0
        
        try:
            # 对于某些事件类型，可以进行批量优化
            if event_type == EVENT_TYPES.PRICEUPDATE:
                processed_count = self._batch_process_price_updates(events)
            elif event_type == EVENT_TYPES.SIGNAL:
                processed_count = self._batch_process_signals(events)
            else:
                # 默认逐个处理
                for event in events:
                    self._process_enhanced(event)
                    processed_count += 1
                    
        except Exception as e:
            self.log("ERROR", f"Error processing event group {event_type}: {e}")
        
        return processed_count
    
    def _batch_process_price_updates(self, events: List[EventBase]) -> int:
        """批量处理价格更新事件"""
        # 按股票代码分组
        price_groups = {}
        for event in events:
            code = getattr(event, 'code', None)
            if code:
                if code not in price_groups:
                    price_groups[code] = []
                price_groups[code].append(event)
        
        processed = 0
        for code, price_events in price_groups.items():
            # 只处理最新的价格事件，忽略过时的
            latest_event = max(price_events, key=lambda e: getattr(e, 'timestamp', datetime.datetime.min))
            self._process_enhanced(latest_event)
            processed += 1
        
        return processed
    
    def _batch_process_signals(self, events: List[EventBase]) -> int:
        """批量处理信号事件"""
        processed = 0
        for event in events:
            # 检查信号是否仍然有效
            if self._is_signal_valid(event):
                self._process_enhanced(event)
                processed += 1
        return processed
    
    def _is_signal_valid(self, signal_event: EventBase) -> bool:
        """检查信号是否仍然有效"""
        # 检查信号时间是否过时
        if hasattr(signal_event, 'timestamp'):
            time_diff = self.now - signal_event.timestamp
            if time_diff > datetime.timedelta(minutes=5):  # 5分钟后信号失效
                return False
        return True
    
    def _process_enhanced(self, event: EventBase):
        """增强版事件处理"""
        # 使用缓存检查是否已处理过相似事件
        if self.enable_caching:
            cache_key = self._generate_cache_key(event)
            cached_result = self.event_cache.get(cache_key)
            if cached_result:
                # 使用缓存结果，避免重复计算
                return
        
        # 正常处理事件
        start_time = datetime.datetime.now()
        super()._process(event)
        
        # 缓存处理结果
        if self.enable_caching:
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            if processing_time > 0.001:  # 只缓存耗时操作
                self.event_cache.put(cache_key, event)
    
    def _generate_cache_key(self, event: EventBase) -> str:
        """生成事件缓存键"""
        key_parts = [
            str(event.event_type),
            getattr(event, 'code', ''),
            str(getattr(event, 'timestamp', '')),
        ]
        return '_'.join(key_parts)
    
    def _calculate_adaptive_sleep(self, consecutive_empty_count: int) -> float:
        """计算自适应休眠时间"""
        if consecutive_empty_count > 50:
            return 1.0  # 长期空闲，休眠1秒
        elif consecutive_empty_count > 20:
            return 0.5  # 休眠500ms
        elif consecutive_empty_count > 10:
            return 0.1  # 休眠100ms
        elif consecutive_empty_count > 5:
            return 0.02  # 休眠20ms
        else:
            return 0.002  # 活跃期，保持2ms
    
    def _update_avg_processing_time(self, processing_time: float, events_count: int):
        """更新平均处理时间"""
        if self.performance_metrics.events_processed > 0:
            total_time = (
                self.performance_metrics.avg_processing_time * 
                (self.performance_metrics.events_processed - events_count) +
                processing_time
            )
            self.performance_metrics.avg_processing_time = total_time / self.performance_metrics.events_processed
        else:
            self.performance_metrics.avg_processing_time = processing_time / events_count
    
    def _update_performance_metrics(self):
        """更新性能指标"""
        try:
            # 内存使用
            process = psutil.Process()
            self.performance_metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
            # CPU使用率
            self.performance_metrics.cpu_usage_percent = process.cpu_percent()
            
            # 队列大小
            if self._use_priority_queue:
                self.performance_metrics.queue_size = self._priority_queue.qsize()
            else:
                self.performance_metrics.queue_size = self._queue.qsize()
            
            # 记录性能指标
            if self.performance_metrics.events_processed % 1000 == 0:
                self.log("DEBUG", f"Performance: "
                        f"Events={self.performance_metrics.events_processed}, "
                        f"AvgTime={self.performance_metrics.avg_processing_time:.4f}s, "
                        f"Memory={self.performance_metrics.memory_usage_mb:.1f}MB, "
                        f"CPU={self.performance_metrics.cpu_usage_percent:.1f}%")
                        
        except Exception as e:
            self.log("ERROR", f"Error updating performance metrics: {e}")
    
    def _manage_memory(self):
        """内存管理"""
        current_memory = self.performance_metrics.memory_usage_mb
        
        # 内存使用超过限制时的处理
        if current_memory > self.memory_limit_mb:
            self.log("WARN", f"Memory usage {current_memory:.1f}MB exceeds limit {self.memory_limit_mb}MB")
            
            # 清理缓存
            if self.event_cache:
                self.event_cache.clear()
                self.log("INFO", "Event cache cleared to free memory")
            
            # 强制垃圾回收
            gc.collect()
        
        # 定期垃圾回收
        now = datetime.datetime.now()
        if now - self.last_gc_time > self.gc_interval:
            collected = gc.collect()
            self.last_gc_time = now
            if collected > 0:
                self.log("DEBUG", f"Garbage collection freed {collected} objects")
    
    def add_time_hook(self, hook_func, cache_result: bool = False):
        """添加时间钩子，支持结果缓存"""
        self._time_hooks.append(hook_func)
        if cache_result:
            self._time_hook_cache[hook_func.__name__] = {}
    
    def execute_time_hooks(self, current_time: datetime.datetime):
        """执行时间钩子，支持缓存优化"""
        for hook in self._time_hooks:
            try:
                hook_name = hook.__name__
                
                # 检查是否需要缓存
                if hook_name in self._time_hook_cache:
                    # 生成缓存键
                    cache_key = current_time.strftime("%Y%m%d")
                    
                    if cache_key not in self._time_hook_cache[hook_name]:
                        # 执行钩子并缓存结果
                        result = hook(current_time)
                        self._time_hook_cache[hook_name][cache_key] = result
                    # 使用缓存结果（如果钩子有返回值处理逻辑）
                else:
                    # 直接执行钩子
                    hook(current_time)
                    
            except Exception as e:
                self.log("ERROR", f"Error executing time hook {hook.__name__}: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'events_processed': self.performance_metrics.events_processed,
            'avg_processing_time_ms': self.performance_metrics.avg_processing_time * 1000,
            'memory_usage_mb': self.performance_metrics.memory_usage_mb,
            'cpu_usage_percent': self.performance_metrics.cpu_usage_percent,
            'queue_size': self.performance_metrics.queue_size,
            'cache_enabled': self.enable_caching,
            'batching_enabled': self.enable_batching,
            'cache_size': len(self.event_cache.cache) if self.event_cache else 0,
        }
    
    def optimize_for_large_dataset(self):
        """为大数据集优化配置"""
        self.enable_batching = True
        self.enable_caching = True
        self.event_batch.batch_size = 200  # 增大批次大小
        self.memory_limit_mb = 2000  # 增大内存限制
        self.gc_interval = datetime.timedelta(minutes=2)  # 更频繁的GC
        self.log("INFO", "Engine optimized for large dataset processing")
    
    def optimize_for_realtime(self):
        """为实时处理优化配置"""
        self.enable_batching = False  # 禁用批处理以减少延迟
        self.enable_caching = False  # 禁用缓存以确保实时性
        self._use_priority_queue = True  # 使用优先队列
        self.log("INFO", "Engine optimized for real-time processing")