"""
断路器实现

实现断路器模式，提供故障保护机制：
- 监控目标健康状态
- 在故障率过高时开启断路器
- 支持半开状态探测恢复
- 提供多种触发策略
"""

import time
from datetime import timedelta
from typing import Dict, List, Optional, Callable
from collections import deque
from dataclasses import dataclass, field

from .interfaces import ICircuitBreaker, CircuitBreakerState
from ginkgo.trading.time.clock import now as clock_now


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 5  # 失败阈值
    failure_rate_threshold: float = 0.5  # 失败率阈值 (50%)
    recovery_timeout: int = 60  # 恢复超时时间(秒)
    half_open_max_calls: int = 3  # 半开状态最大调用次数
    sliding_window_size: int = 100  # 滑动窗口大小
    min_calls_threshold: int = 10  # 最小调用数阈值


class CircuitBreaker(ICircuitBreaker):
    """断路器实现"""
    
    def __init__(self, 
                 target_id: str,
                 config: Optional[CircuitBreakerConfig] = None,
                 custom_failure_detector: Optional[Callable[[Exception], bool]] = None):
        """
        初始化断路器
        
        Args:
            target_id: 目标ID
            config: 断路器配置
            custom_failure_detector: 自定义失败检测器
        """
        self.target_id = target_id
        self.config = config or CircuitBreakerConfig()
        self.custom_failure_detector = custom_failure_detector
        
        # 状态管理
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None
        self._state_changed_time = clock_now()
        
        # 滑动窗口统计
        self._call_results: deque = deque(maxlen=self.config.sliding_window_size)
        self._half_open_calls = 0
        
        # 事件回调
        self._state_change_callbacks: List[Callable[[CircuitBreakerState, CircuitBreakerState], None]] = []
        
    def is_open(self) -> bool:
        """检查断路器是否开启"""
        self._update_state()
        return self._state == CircuitBreakerState.OPEN
    
    def record_success(self) -> None:
        """记录成功"""
        now = clock_now()
        self._last_success_time = now
        self._call_results.append((True, now))
        
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            self._half_open_calls += 1
            
            # 半开状态下连续成功，关闭断路器
            if self._success_count >= self.config.half_open_max_calls:
                self._change_state(CircuitBreakerState.CLOSED)
        
        elif self._state == CircuitBreakerState.CLOSED:
            self._success_count += 1
    
    def record_failure(self) -> None:
        """记录失败"""
        now = clock_now()
        self._last_failure_time = now
        self._call_results.append((False, now))
        
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._failure_count += 1
            self._half_open_calls += 1
            
            # 半开状态下失败，立即开启断路器
            self._change_state(CircuitBreakerState.OPEN)
        
        elif self._state == CircuitBreakerState.CLOSED:
            self._failure_count += 1
            
            # 检查是否需要开启断路器
            if self._should_open_circuit():
                self._change_state(CircuitBreakerState.OPEN)
    
    def get_state(self) -> CircuitBreakerState:
        """获取当前状态"""
        self._update_state()
        return self._state
    
    def reset(self) -> None:
        """重置断路器"""
        old_state = self._state
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None
        self._last_success_time = None
        self._state_changed_time = clock_now()
        self._call_results.clear()
        
        if old_state != CircuitBreakerState.CLOSED:
            self._notify_state_change(old_state, CircuitBreakerState.CLOSED)
    
    def get_failure_rate(self) -> float:
        """获取失败率"""
        if not self._call_results:
            return 0.0
        
        recent_calls = self._get_recent_calls()
        if len(recent_calls) < self.config.min_calls_threshold:
            return 0.0
        
        failure_count = sum(1 for success, _ in recent_calls if not success)
        return failure_count / len(recent_calls)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        recent_calls = self._get_recent_calls()
        total_calls = len(recent_calls)
        failure_count = sum(1 for success, _ in recent_calls if not success)
        success_count = total_calls - failure_count
        
        return {
            'target_id': self.target_id,
            'state': self._state.value,
            'total_calls': total_calls,
            'success_count': success_count,
            'failure_count': failure_count,
            'failure_rate': self.get_failure_rate(),
            'last_failure_time': self._last_failure_time,
            'last_success_time': self._last_success_time,
            'state_changed_time': self._state_changed_time,
            'time_in_current_state': (clock_now() - self._state_changed_time).total_seconds(),
        }
    
    def add_state_change_callback(self, callback: Callable[[CircuitBreakerState, CircuitBreakerState], None]) -> None:
        """添加状态变化回调"""
        self._state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[CircuitBreakerState, CircuitBreakerState], None]) -> None:
        """移除状态变化回调"""
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)
    
    def _update_state(self) -> None:
        """更新状态"""
        if self._state == CircuitBreakerState.OPEN:
            # 检查是否可以转为半开状态
            if self._can_attempt_reset():
                self._change_state(CircuitBreakerState.HALF_OPEN)
    
    def _should_open_circuit(self) -> bool:
        """判断是否应该开启断路器"""
        # 检查连续失败数
        if self._failure_count >= self.config.failure_threshold:
            return True
        
        # 检查失败率
        failure_rate = self.get_failure_rate()
        recent_calls = self._get_recent_calls()
        
        if (len(recent_calls) >= self.config.min_calls_threshold and 
            failure_rate >= self.config.failure_rate_threshold):
            return True
        
        return False
    
    def _can_attempt_reset(self) -> bool:
        """判断是否可以尝试重置"""
        if not self._last_failure_time:
            return True
        
        time_since_failure = clock_now() - self._last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _get_recent_calls(self) -> List:
        """获取最近的调用记录"""
        # 返回滑动窗口内的调用记录
        return list(self._call_results)
    
    def _change_state(self, new_state: CircuitBreakerState) -> None:
        """改变状态"""
        if self._state == new_state:
            return
        
        old_state = self._state
        self._state = new_state
        self._state_changed_time = clock_now()
        
        # 重置相关计数器
        if new_state == CircuitBreakerState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
            self._failure_count = 0
        
        # 通知状态变化
        self._notify_state_change(old_state, new_state)
    
    def _notify_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState) -> None:
        """通知状态变化"""
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception:
                # 回调异常不应影响断路器功能
                pass


class CircuitBreakerManager:
    """断路器管理器"""
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._global_config = CircuitBreakerConfig()
    
    def get_circuit_breaker(self, target_id: str, 
                          config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """获取或创建断路器"""
        if target_id not in self._circuit_breakers:
            effective_config = config or self._global_config
            self._circuit_breakers[target_id] = CircuitBreaker(target_id, effective_config)
        
        return self._circuit_breakers[target_id]
    
    def remove_circuit_breaker(self, target_id: str) -> bool:
        """移除断路器"""
        if target_id in self._circuit_breakers:
            del self._circuit_breakers[target_id]
            return True
        return False
    
    def get_all_statistics(self) -> Dict[str, Dict]:
        """获取所有断路器统计"""
        return {
            target_id: breaker.get_statistics()
            for target_id, breaker in self._circuit_breakers.items()
        }
    
    def reset_all(self) -> None:
        """重置所有断路器"""
        for breaker in self._circuit_breakers.values():
            breaker.reset()
    
    def set_global_config(self, config: CircuitBreakerConfig) -> None:
        """设置全局配置"""
        self._global_config = config
    
    def get_open_circuit_breakers(self) -> List[str]:
        """获取开启状态的断路器"""
        return [
            target_id for target_id, breaker in self._circuit_breakers.items()
            if breaker.is_open()
        ]
    
    def get_statistics_summary(self) -> Dict:
        """获取统计摘要"""
        all_stats = self.get_all_statistics()
        
        if not all_stats:
            return {
                'total_circuit_breakers': 0,
                'open_count': 0,
                'closed_count': 0,
                'half_open_count': 0,
                'overall_failure_rate': 0.0
            }
        
        open_count = sum(1 for stats in all_stats.values() if stats['state'] == 'open')
        closed_count = sum(1 for stats in all_stats.values() if stats['state'] == 'closed')
        half_open_count = sum(1 for stats in all_stats.values() if stats['state'] == 'half_open')
        
        # 计算整体失败率
        total_calls = sum(stats['total_calls'] for stats in all_stats.values())
        total_failures = sum(stats['failure_count'] for stats in all_stats.values())
        overall_failure_rate = (total_failures / total_calls) if total_calls > 0 else 0.0
        
        return {
            'total_circuit_breakers': len(all_stats),
            'open_count': open_count,
            'closed_count': closed_count,
            'half_open_count': half_open_count,
            'overall_failure_rate': overall_failure_rate,
            'total_calls': total_calls,
            'total_failures': total_failures
        }


# 全局断路器管理器实例
_global_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker(target_id: str, 
                       config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """获取全局断路器实例"""
    return _global_circuit_breaker_manager.get_circuit_breaker(target_id, config)


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """获取全局断路器管理器"""
    return _global_circuit_breaker_manager
