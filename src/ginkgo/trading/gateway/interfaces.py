# Upstream: gateway.center, gateway.balancers, gateway.circuit_breaker, gateway.__init__
# Downstream: trading.time.clock
# Role: 事件路由系统接口与数据结构定义，包括路由中心/负载均衡器/熔断器抽象接口、路由策略枚举和路由数据类






"""
事件路由中心接口定义

提供事件路由系统的数据结构、负载均衡器纯契约与断路器状态枚举：
- 负载均衡器契约(LoadBalancer，多实现纯契约 ABC，ADR-022 原则 1)
- 路由数据结构(RouteTarget, RoutingRule, RoutingMetrics)
- 断路器状态枚举(CircuitBreakerState)
路由中心(EventRoutingCenter)与断路器(CircuitBreaker)为单实现具体类，
见 center.py / circuit_breaker.py（ADR-022 原则 2 单实现 ABC 降级）。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Set, Tuple, Pattern
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from ginkgo.trading.time.clock import now as clock_now


class RoutingStrategy(Enum):
    """路由策略"""
    ROUND_ROBIN = "round_robin"        # 轮询
    WEIGHTED = "weighted"              # 加权
    LEAST_CONNECTIONS = "least_conn"   # 最少连接
    HASH_BASED = "hash"                # 哈希路由
    PRIORITY_BASED = "priority"        # 优先级
    FAILOVER = "failover"              # 故障转移
    BROADCAST = "broadcast"            # 广播
    CONDITIONAL = "conditional"        # 条件路由


class RoutingMode(Enum):
    """路由模式"""
    SYNC = "sync"                      # 同步路由
    ASYNC = "async"                    # 异步路由
    BATCH = "batch"                    # 批量路由
    PIPELINE = "pipeline"              # 管道路由


class RouteStatus(Enum):
    """路由状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    FAILED = "failed"


class EventPriority(IntEnum):
    """事件优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class RouteTarget:
    """路由目标"""
    target_id: str
    target_type: str                   # "processor", "handler", "queue"
    target_instance: Any
    weight: int = 1
    priority: EventPriority = EventPriority.NORMAL
    max_concurrent: int = 100
    current_load: int = 0
    status: RouteStatus = RouteStatus.ACTIVE
    
    # 健康检查
    last_health_check: Optional[datetime] = None
    health_score: float = 100.0
    
    # 性能指标
    total_processed: int = 0
    total_errors: int = 0
    avg_response_time: float = 0.0
    
    # 配置
    timeout: float = 30.0
    retry_attempts: int = 3
    circuit_breaker_enabled: bool = True
    
    # 元数据
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.tags, list):
            self.tags = set(self.tags)
    
    @property
    def load_percentage(self) -> float:
        """负载百分比"""
        if self.max_concurrent == 0:
            return 0.0
        return (self.current_load / self.max_concurrent) * 100
    
    @property
    def is_overloaded(self) -> bool:
        """是否过载"""
        return self.current_load >= self.max_concurrent
    
    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.total_processed == 0:
            return 0.0
        return (self.total_errors / self.total_processed) * 100


@dataclass
class RoutingRule:
    """路由规则"""
    rule_id: str
    name: str
    description: str = ""
    
    # 匹配条件
    event_type_pattern: str = "*"      # 事件类型模式
    source_pattern: str = "*"          # 来源模式
    priority_range: Tuple[int, int] = (1, 10)
    custom_conditions: List[Callable[[Any], bool]] = field(default_factory=list)
    
    # 路由配置
    targets: List[str] = field(default_factory=list)  # 目标ID列表
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    mode: RoutingMode = RoutingMode.ASYNC
    
    # 控制参数
    enabled: bool = True
    weight: int = 1
    max_retries: int = 3
    timeout: float = 30.0
    
    # 时间控制
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    
    # 统计信息
    matched_count: int = 0
    success_count: int = 0
    error_count: int = 0
    
    # 元数据
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.tags, list):
            self.tags = set(self.tags)
        if isinstance(self.targets, str):
            self.targets = [self.targets]
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total_attempts = self.success_count + self.error_count
        if total_attempts == 0:
            return 100.0
        return (self.success_count / total_attempts) * 100
    
    @property
    def is_time_valid(self) -> bool:
        """是否在有效时间内"""
        now = clock_now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True


@dataclass  
class RoutingMetrics:
    """路由指标"""
    total_events: int = 0
    successful_routes: int = 0
    failed_routes: int = 0
    avg_routing_time: float = 0.0
    throughput_per_second: float = 0.0
    
    # 按规则统计
    rules_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # 按目标统计
    targets_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 时间窗口统计
    last_update: datetime = field(default_factory=clock_now)
    window_size: int = 300  # 5分钟窗口
    
    @property
    def success_rate(self) -> float:
        """总体成功率"""
        total_routes = self.successful_routes + self.failed_routes
        if total_routes == 0:
            return 100.0
        return (self.successful_routes / total_routes) * 100
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        return 100.0 - self.success_rate


class LoadBalancer(ABC):
    """负载均衡器接口"""
    
    @abstractmethod
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """选择路由目标"""
        pass
    
    @abstractmethod
    async def update_target_metrics(self, target_id: str, 
                                  response_time: float, success: bool) -> None:
        """更新目标指标"""
        pass


class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "closed"
    OPEN = "open"  
    HALF_OPEN = "half_open"


@dataclass
class RouteResult:
    """路由结果"""
    event_id: str
    targets: List[str]
    success: bool
    routing_time: float
    error_message: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=clock_now)
    
    @property
    def target_count(self) -> int:
        """目标数量"""
        return len(self.targets)


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    target_id: str
    is_healthy: bool
    health_score: float
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=clock_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# 路由事件类型定义
class RoutingEventType(Enum):
    """路由事件类型"""
    TARGET_REGISTERED = "target_registered"
    TARGET_UNREGISTERED = "target_unregistered" 
    TARGET_STATUS_CHANGED = "target_status_changed"
    RULE_ADDED = "rule_added"
    RULE_REMOVED = "rule_removed"
    RULE_UPDATED = "rule_updated"
    ROUTING_SUCCESS = "routing_success"
    ROUTING_FAILURE = "routing_failure"
    HEALTH_CHECK_COMPLETED = "health_check_completed"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"
    CIRCUIT_BREAKER_CLOSED = "circuit_breaker_closed"
    METRICS_UPDATED = "metrics_updated"


@dataclass
class RoutingEvent:
    """路由事件"""
    event_type: RoutingEventType
    source: str  
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: f"routing_event_{clock_now().timestamp()}")
    
    @property
    def age_seconds(self) -> float:
        """事件年龄(秒)"""
        return (clock_now() - self.timestamp).total_seconds()


# 用于测试的模拟目标类
class MockTarget:
    """模拟路由目标"""
    
    def __init__(self, target_id: str, response_time: float = 0.1, 
                 failure_rate: float = 0.0):
        self.target_id = target_id
        self.response_time = response_time
        self.failure_rate = failure_rate
        self.call_count = 0
        
    async def process(self, event: Any) -> Any:
        """处理事件"""
        self.call_count += 1
        
        # 模拟响应时间
        import asyncio
        await asyncio.sleep(self.response_time)
        
        # 模拟错误
        import random
        if random.random() < self.failure_rate:
            raise RuntimeError(f"Mock failure in {self.target_id}")
        
        return f"Processed by {self.target_id}: {getattr(event, 'event_type', 'unknown')}"
    
    def reset_stats(self):
        """重置统计"""
        self.call_count = 0
