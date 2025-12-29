# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 路由模块公共接口，导出Router路由器、Center路由中心、Balancer负载均衡、CircuitBreaker熔断器等订单路由组件






"""
事件路由系统

统一的事件路由和分发系统，支持：
- 智能路由规则匹配
- 多种负载均衡策略  
- 断路器故障保护
- 健康监控和指标收集
- 动态配置重载
"""

from .interfaces import (
    # 核心接口
    IEventRoutingCenter,
    ILoadBalancer,
    ICircuitBreaker,
    
    # 枚举类型
    RoutingStrategy,
    RoutingMode,
    RouteStatus,
    EventPriority,
    CircuitBreakerState,
    RoutingEventType,
    
    # 数据结构
    RouteTarget,
    RoutingRule,
    RoutingMetrics,
    RouteResult,
    HealthCheckResult,
    RoutingEvent,
    
    # 测试工具
    MockTarget,
)

from .center import EventRoutingCenter
from .balancers import (
    BaseLoadBalancer,
    RoundRobinBalancer,
    WeightedBalancer,
    LeastConnectionsBalancer,
    HashBasedBalancer,
    PriorityBasedBalancer,
    BroadcastBalancer,
    FailoverBalancer,
    ConditionalBalancer,
    LoadBalancerFactory,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerManager,
    get_circuit_breaker,
    get_circuit_breaker_manager,
)

# T6: 添加MatchMaking相关导入
from .base_matchmaking import MatchMakingBase
from .router import Router

__all__ = [
    # 核心接口
    'IEventRoutingCenter',
    'ILoadBalancer', 
    'ICircuitBreaker',
    
    # 枚举类型
    'RoutingStrategy',
    'RoutingMode',
    'RouteStatus',
    'EventPriority',
    'CircuitBreakerState',
    'RoutingEventType',
    
    # 数据结构
    'RouteTarget',
    'RoutingRule',
    'RoutingMetrics',
    'RouteResult',
    'HealthCheckResult',
    'RoutingEvent',
    
    # 实现类
    'EventRoutingCenter',
    'BaseLoadBalancer',
    'RoundRobinBalancer',
    'WeightedBalancer', 
    'LeastConnectionsBalancer',
    'HashBasedBalancer',
    'PriorityBasedBalancer',
    'BroadcastBalancer',
    'FailoverBalancer',
    'ConditionalBalancer',
    'LoadBalancerFactory',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitBreakerManager',
    'get_circuit_breaker',
    'get_circuit_breaker_manager',
    
    # T6: MatchMaking类
    'MatchMakingBase',
    'Router',
    
    # 测试工具
    'MockTarget',
]
