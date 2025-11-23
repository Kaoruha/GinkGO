"""
T5架构健康监控模块

提供统一的系统健康检查和监控功能
"""

import asyncio
import time
import psutil
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

from ginkgo.libs import GLOG


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    component_name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'component_name': self.component_name,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'last_check': self.last_check.isoformat(),
            'response_time_ms': self.response_time_ms
        }


@dataclass
class SystemHealth:
    """系统整体健康状态"""
    overall_status: HealthStatus
    components: List[ComponentHealth]
    system_info: Dict[str, Any] = field(default_factory=dict)
    check_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'overall_status': self.overall_status.value,
            'components': [comp.to_dict() for comp in self.components],
            'system_info': self.system_info,
            'check_timestamp': self.check_timestamp.isoformat()
        }
    
    @property
    def healthy_components(self) -> int:
        """健康组件数量"""
        return sum(1 for comp in self.components if comp.status == HealthStatus.HEALTHY)
    
    @property
    def total_components(self) -> int:
        """总组件数量"""
        return len(self.components)


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self._health_checks: Dict[str, Callable] = {}
        self._last_results: Dict[str, ComponentHealth] = {}
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[SystemHealth], None]] = []
        
    def register_health_check(self, component_name: str, 
                            check_func: Callable[[], ComponentHealth]) -> None:
        """注册健康检查函数"""
        self._health_checks[component_name] = check_func
    
    def register_async_health_check(self, component_name: str,
                                  check_func: Callable[[], ComponentHealth]) -> None:
        """注册异步健康检查函数"""
        self._health_checks[component_name] = check_func
    
    def add_health_callback(self, callback: Callable[[SystemHealth], None]) -> None:
        """添加健康状态变化回调"""
        self._callbacks.append(callback)
    
    async def check_component_health(self, component_name: str) -> ComponentHealth:
        """检查单个组件健康状态"""
        if component_name not in self._health_checks:
            return ComponentHealth(
                component_name=component_name,
                status=HealthStatus.UNKNOWN,
                message="No health check registered"
            )
        
        check_func = self._health_checks[component_name]
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time = (time.time() - start_time) * 1000
            result.response_time_ms = response_time
            result.last_check = clock_now()
            
            self._last_results[component_name] = result
            return result
            
        except Exception as e:
            GLOG.ERROR(f"健康检查失败 {component_name}: {e}")
            error_result = ComponentHealth(
                component_name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            )
            self._last_results[component_name] = error_result
            return error_result
    
    async def check_all_health(self) -> SystemHealth:
        """检查所有组件健康状态"""
        if not self._health_checks:
            return SystemHealth(
                overall_status=HealthStatus.UNKNOWN,
                components=[],
                system_info=self._get_system_info()
            )
        
        # 并发检查所有组件
        tasks = [
            self.check_component_health(component_name)
            for component_name in self._health_checks.keys()
        ]
        
        components = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        valid_components = []
        for i, result in enumerate(components):
            if isinstance(result, Exception):
                component_name = list(self._health_checks.keys())[i]
                error_component = ComponentHealth(
                    component_name=component_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)}"
                )
                valid_components.append(error_component)
            else:
                valid_components.append(result)
        
        # 计算整体状态
        overall_status = self._calculate_overall_status(valid_components)
        
        system_health = SystemHealth(
            overall_status=overall_status,
            components=valid_components,
            system_info=self._get_system_info()
        )
        
        # 通知回调
        for callback in self._callbacks:
            try:
                callback(system_health)
            except Exception as e:
                GLOG.ERROR(f"健康状态回调错误: {e}")
        
        return system_health
    
    def get_last_health_check(self) -> Optional[SystemHealth]:
        """获取最后一次健康检查结果"""
        if not self._last_results:
            return None
        
        components = list(self._last_results.values())
        overall_status = self._calculate_overall_status(components)
        
        return SystemHealth(
            overall_status=overall_status,
            components=components,
            system_info=self._get_system_info()
        )
    
    async def start_monitoring(self) -> None:
        """开始健康监控"""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        GLOG.INFO("健康监控已启动")
    
    async def stop_monitoring(self) -> None:
        """停止健康监控"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        GLOG.INFO("健康监控已停止")
    
    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                await self.check_all_health()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                GLOG.ERROR(f"健康监控循环错误: {e}")
                await asyncio.sleep(5)  # 错误后短暂等待
    
    def _calculate_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """计算整体健康状态"""
        if not components:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = sum(1 for comp in components if comp.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for comp in components if comp.status == HealthStatus.DEGRADED)
        
        total_count = len(components)
        
        # 如果超过50%的组件不健康，整体状态为不健康
        if unhealthy_count > total_count * 0.5:
            return HealthStatus.UNHEALTHY
        
        # 如果有任何不健康或超过25%组件降级，整体状态为降级
        if unhealthy_count > 0 or degraded_count > total_count * 0.25:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'python_version': f"{psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB"
            }
        except Exception as e:
            GLOG.WARN(f"获取系统信息失败: {e}")
            return {'error': str(e)}


# 预定义的健康检查函数

def check_database_health(db_connection_func: Callable) -> ComponentHealth:
    """数据库健康检查"""
    try:
        start_time = time.time()
        # 执行简单查询
        connection = db_connection_func()
        if hasattr(connection, 'execute'):
            connection.execute('SELECT 1')
        
        response_time = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            component_name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection successful",
            details={'response_time_ms': response_time}
        )
    except Exception as e:
        return ComponentHealth(
            component_name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connection failed: {str(e)}"
        )


def check_redis_health(redis_client) -> ComponentHealth:
    """Redis健康检查"""
    try:
        start_time = time.time()
        redis_client.ping()
        response_time = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            component_name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful",
            details={'response_time_ms': response_time}
        )
    except Exception as e:
        return ComponentHealth(
            component_name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}"
        )


def check_memory_health(warning_threshold: float = 80.0, 
                       critical_threshold: float = 90.0) -> ComponentHealth:
    """内存使用健康检查"""
    try:
        memory_percent = psutil.virtual_memory().percent
        
        if memory_percent >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"Critical memory usage: {memory_percent:.1f}%"
        elif memory_percent >= warning_threshold:
            status = HealthStatus.DEGRADED  
            message = f"High memory usage: {memory_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Memory usage normal: {memory_percent:.1f}%"
        
        return ComponentHealth(
            component_name="memory",
            status=status,
            message=message,
            details={
                'memory_percent': memory_percent,
                'available_mb': psutil.virtual_memory().available / 1024 / 1024
            }
        )
    except Exception as e:
        return ComponentHealth(
            component_name="memory",
            status=HealthStatus.UNHEALTHY,
            message=f"Memory check failed: {str(e)}"
        )


def check_disk_health(warning_threshold: float = 80.0,
                     critical_threshold: float = 90.0,
                     path: str = '/') -> ComponentHealth:
    """磁盘使用健康检查"""
    try:
        disk_usage = psutil.disk_usage(path)
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        if disk_percent >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"Critical disk usage: {disk_percent:.1f}%"
        elif disk_percent >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"High disk usage: {disk_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {disk_percent:.1f}%"
        
        return ComponentHealth(
            component_name="disk",
            status=status,
            message=message,
            details={
                'disk_percent': disk_percent,
                'free_gb': disk_usage.free / 1024 / 1024 / 1024,
                'total_gb': disk_usage.total / 1024 / 1024 / 1024
            }
        )
    except Exception as e:
        return ComponentHealth(
            component_name="disk",
            status=HealthStatus.UNHEALTHY,
            message=f"Disk check failed: {str(e)}"
        )


# 全局健康检查器实例
_global_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """获取全局健康检查器"""
    return _global_health_checker


def register_health_check(component_name: str, 
                         check_func: Callable[[], ComponentHealth]) -> None:
    """便捷函数：注册健康检查"""
    _global_health_checker.register_health_check(component_name, check_func)


async def check_system_health() -> SystemHealth:
    """便捷函数：检查系统健康状态"""
    return await _global_health_checker.check_all_health()
