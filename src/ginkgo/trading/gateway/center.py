# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: RoutingCenter路由中心提供路由管理和订单分发功能支持交易系统功能支持交易系统功能支持交易系统功能和组件集成提供完整业务支持






"""
事件路由中心核心实现

实现统一的事件路由分发中心，提供：
- 智能路由规则匹配
- 动态目标管理
- 性能指标收集
- 健康监控
- 缓存机制
"""

import time
import json
import hashlib
import random
import re
import asyncio
import logging
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Pattern, Tuple
from uuid import uuid4

from ginkgo.libs import GLOG
from ginkgo.trading.time.clock import now as clock_now
from .interfaces import (
    IEventRoutingCenter, ILoadBalancer, ICircuitBreaker,
    RouteTarget, RoutingRule, RoutingMetrics, RouteResult,
    HealthCheckResult, RoutingEvent, RoutingEventType,
    RoutingStrategy, RoutingMode, RouteStatus, EventPriority,
    CircuitBreakerState
)
from .balancers import LoadBalancerFactory
from .circuit_breaker import get_circuit_breaker, CircuitBreakerConfig


class EventRoutingCenter(IEventRoutingCenter):
    """事件路由中心实现"""
    
    def __init__(self,
                 center_id: str = "routing_center",
                 max_concurrent_routes: int = 1000,
                 metrics_window_size: int = 300,
                 health_check_interval: int = 30,
                 cache_ttl: int = 60,
                 logger: Optional[logging.Logger] = None):
        
        self.center_id = center_id
        self.max_concurrent_routes = max_concurrent_routes
        self.metrics_window_size = metrics_window_size
        self._metrics_window_size = metrics_window_size  # 添加下划线版本
        self.health_check_interval = health_check_interval
        self.cache_ttl = cache_ttl
        self.logger = logger or GLOG
        
        # 路由目标管理
        self._targets: Dict[str, RouteTarget] = {}
        self._targets_lock = asyncio.Lock()
        
        # 路由规则管理
        self._rules: Dict[str, RoutingRule] = {}
        self._compiled_rules: List[Tuple[RoutingRule, List[Optional[Pattern]]]] = []
        self._rules_lock = asyncio.Lock()
        
        # 路由状态
        self._active_routes: Set[str] = set()
        self._route_semaphore = asyncio.Semaphore(max_concurrent_routes)
        
        # 指标统计
        self._metrics = RoutingMetrics()
        self._route_history: deque = deque(maxlen=10000)
        self._performance_tracker = defaultdict(lambda: deque(maxlen=1000))
        self._metrics_lock = asyncio.Lock()
        
        # 缓存机制
        self._route_cache: Dict[str, List[str]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_lock = asyncio.Lock()
        
        # 负载均衡器
        self._load_balancers: Dict[RoutingStrategy, ILoadBalancer] = {}
        
        # 断路器配置
        self._circuit_breaker_config = CircuitBreakerConfig()
        self._circuit_breakers: Dict[str, ICircuitBreaker] = {}
        
        # 异步任务管理
        self._background_tasks: Set[asyncio.Task] = set()
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        
        # 线程池
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # 事件回调
        self._event_callbacks: List[callable] = []
    
    async def _initialize_load_balancers(self) -> None:
        """初始化负载均衡器"""
        try:
            for strategy in RoutingStrategy:
                self._load_balancers[strategy] = LoadBalancerFactory.create_balancer(strategy)
        except Exception as e:
            GLOG.ERROR(f"初始化负载均衡器失败: {e}")
    
    # === 生命周期管理 ===
    
    async def initialize(self) -> None:
        """初始化路由中心"""
        try:
            GLOG.INFO(f"初始化事件路由中心: {self.center_id}")
            
            # 初始化负载均衡器
            await self._initialize_load_balancers()
            
            # 启动后台任务
            await self._start_background_tasks()
            
            self._is_running = True
            GLOG.INFO(f"事件路由中心 {self.center_id} 初始化完成")
        
        except Exception as e:
            GLOG.ERROR(f"初始化路由中心失败: {e}")
            raise
    
    async def shutdown(self) -> None:
        """关闭路由中心"""
        try:
            GLOG.INFO(f"关闭事件路由中心: {self.center_id}")
            
            self._is_running = False
            self._shutdown_event.set()
            
            # 等待所有后台任务完成
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # 关闭线程池
            self._thread_pool.shutdown(wait=True)
            
            GLOG.INFO(f"事件路由中心 {self.center_id} 已关闭")
        
        except Exception as e:
            GLOG.ERROR(f"关闭路由中心失败: {e}")
    
    # === 目标管理 ===
    
    async def register_target(self, target: RouteTarget) -> bool:
        """注册路由目标"""
        try:
            if not await self._validate_target(target):
                return False
            
            async with self._targets_lock:
                self._targets[target.target_id] = target
            
            # 创建断路器(如果需要)
            if target.circuit_breaker_enabled:
                circuit_breaker = get_circuit_breaker(target.target_id, self._circuit_breaker_config)
                self._circuit_breakers[target.target_id] = circuit_breaker
            
            # 重新编译规则
            await self._recompile_rules()
            
            # 触发事件
            await self._emit_event(RoutingEventType.TARGET_REGISTERED, {
                'target_id': target.target_id,
                'target_type': target.target_type
            })
            
            GLOG.INFO(f"路由目标注册成功: {target.target_id}")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"注册路由目标失败 {target.target_id}: {e}")
            return False
    
    async def unregister_target(self, target_id: str) -> bool:
        """注销路由目标"""
        try:
            async with self._targets_lock:
                if target_id not in self._targets:
                    return False
                
                target = self._targets[target_id]
                del self._targets[target_id]
            
            # 清理断路器
            if target_id in self._circuit_breakers:
                del self._circuit_breakers[target_id]
            
            # 清理缓存
            await self._clear_target_cache(target_id)
            
            # 重新编译规则
            await self._recompile_rules()
            
            # 触发事件
            await self._emit_event(RoutingEventType.TARGET_UNREGISTERED, {
                'target_id': target_id
            })
            
            GLOG.INFO(f"路由目标注销成功: {target_id}")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"注销路由目标失败 {target_id}: {e}")
            return False
    
    async def update_target(self, target_id: str, updates: Dict[str, Any]) -> bool:
        """更新路由目标"""
        try:
            async with self._targets_lock:
                if target_id not in self._targets:
                    return False
                
                target = self._targets[target_id]
                old_status = target.status
                
                # 更新目标属性
                for key, value in updates.items():
                    if hasattr(target, key):
                        setattr(target, key, value)
            
            # 如果状态发生变化，触发事件
            if target.status != old_status:
                await self._emit_event(RoutingEventType.TARGET_STATUS_CHANGED, {
                    'target_id': target_id,
                    'old_status': old_status.value,
                    'new_status': target.status.value
                })
            
            GLOG.INFO(f"路由目标更新成功: {target_id}")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"更新路由目标失败 {target_id}: {e}")
            return False
    
    async def get_target(self, target_id: str) -> Optional[RouteTarget]:
        """获取路由目标"""
        async with self._targets_lock:
            return self._targets.get(target_id)
    
    async def list_targets(self, status_filter: Optional[RouteStatus] = None) -> List[RouteTarget]:
        """列出路由目标"""
        async with self._targets_lock:
            targets = list(self._targets.values())
            
            if status_filter:
                targets = [t for t in targets if t.status == status_filter]
            
            return targets
    
    # === 规则管理 ===
    
    async def add_routing_rule(self, rule: RoutingRule) -> bool:
        """添加路由规则"""
        try:
            if not await self._validate_rule(rule):
                return False
            
            async with self._rules_lock:
                self._rules[rule.rule_id] = rule
            
            # 重新编译规则
            await self._recompile_rules()
            
            # 触发事件
            await self._emit_event(RoutingEventType.RULE_ADDED, {
                'rule_id': rule.rule_id,
                'rule_name': rule.name
            })
            
            GLOG.INFO(f"路由规则添加成功: {rule.rule_id}")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"添加路由规则失败 {rule.rule_id}: {e}")
            return False
    
    async def remove_routing_rule(self, rule_id: str) -> bool:
        """移除路由规则"""
        try:
            async with self._rules_lock:
                if rule_id not in self._rules:
                    return False
                
                del self._rules[rule_id]
            
            # 重新编译规则
            await self._recompile_rules()
            
            # 触发事件
            await self._emit_event(RoutingEventType.RULE_REMOVED, {
                'rule_id': rule_id
            })
            
            GLOG.INFO(f"路由规则移除成功: {rule_id}")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"移除路由规则失败 {rule_id}: {e}")
            return False
    
    async def update_routing_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """更新路由规则"""
        try:
            async with self._rules_lock:
                if rule_id not in self._rules:
                    return False
                
                rule = self._rules[rule_id]
                
                # 更新规则属性
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
            
            # 重新编译规则
            await self._recompile_rules()
            
            # 触发事件
            await self._emit_event(RoutingEventType.RULE_UPDATED, {
                'rule_id': rule_id,
                'updates': updates
            })
            
            GLOG.INFO(f"路由规则更新成功: {rule_id}")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"更新路由规则失败 {rule_id}: {e}")
            return False
    
    async def get_routing_rule(self, rule_id: str) -> Optional[RoutingRule]:
        """获取路由规则"""
        async with self._rules_lock:
            return self._rules.get(rule_id)
    
    async def list_routing_rules(self, enabled_only: bool = False) -> List[RoutingRule]:
        """列出路由规则"""
        async with self._rules_lock:
            rules = list(self._rules.values())
            
            if enabled_only:
                rules = [r for r in rules if r.enabled]
            
            return rules
    
    # === 路由处理 ===
    
    async def route_event(self, event: Any) -> List[str]:
        """路由事件"""
        async with self._route_semaphore:
            return await self._do_route_event(event)

    
    # === 引擎集成接口 ===
    
    def route_event_sync(self, event: Any) -> List[str]:
        """
        同步路由事件接口 - 用于引擎集成
        
        为了与现有TimeControlledEventEngine等同步引擎兼容，
        提供同步版本的事件路由接口。
        """
        try:
            # 简化的同步路由逻辑
            event_type = str(getattr(event, 'event_type', 'unknown'))
            event_source = str(getattr(event, 'source', 'unknown'))
            
            # 记录路由请求
            GLOG.DEBUG(f"Routing event: {event_type} from {event_source}")
            
            # 基于事件类型的简单路由规则
            target_handlers = []
            
            # T5事件路由规则
            if 'Order' in event_type:
                # 订单相关事件路由到BrokerMatchMaking
                target_handlers.extend(['broker_matchmaking', 'portfolio_manager'])
                
            elif 'Price' in event_type or 'Bar' in event_type:
                # 价格相关事件路由到策略和风控
                target_handlers.extend(['strategy_manager', 'risk_manager'])
                
            elif 'Portfolio' in event_type:
                # 投资组合事件路由到分析器
                target_handlers.extend(['portfolio_analyzer', 'performance_tracker'])
                
            elif 'Risk' in event_type:
                # 风险事件路由到风控管理和通知系统
                target_handlers.extend(['risk_manager', 'notification_system'])
                
            else:
                # 默认路由到通用处理器
                target_handlers.append('default_handler')
            
            # 过滤存在的目标处理器
            available_targets = []
            for target_id in target_handlers:
                if target_id in self._targets:
                    target = self._targets[target_id]
                    if target.status == RouteStatus.ACTIVE and not target.is_overloaded:
                        available_targets.append(target_id)
            
            if available_targets:
                GLOG.DEBUG(f"Event {event_type} routed to: {available_targets}")
            else:
                GLOG.WARN(f"No available targets for event {event_type}")
                
            return available_targets
            
        except Exception as e:
            GLOG.ERROR(f"Sync event routing failed: {e}")
            return []
    
    def register_engine_handlers(self, engine_instance) -> None:
        """
        为引擎注册标准处理器目标
        
        Args:
            engine_instance: 引擎实例，将被注册为各种处理器目标
        """
        try:
            # 注册标准的处理器目标
            standard_targets = [
                ('broker_matchmaking', 'BrokerMatchMaking处理器'),
                ('portfolio_manager', '投资组合管理器'),  
                ('strategy_manager', '策略管理器'),
                ('risk_manager', '风险管理器'),
                ('portfolio_analyzer', '投资组合分析器'),
                ('performance_tracker', '绩效跟踪器'),
                ('notification_system', '通知系统'),
                ('default_handler', '默认处理器')
            ]
            
            for target_id, description in standard_targets:
                target = RouteTarget(
                    target_id=target_id,
                    target_type=f"engine_handler",
                    target_instance=engine_instance,
                    description=description,
                    max_concurrent=100,
                    weight=1.0,
                    timeout_seconds=30.0
                )
                
                # 异步注册转同步
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环正在运行，使用run_coroutine_threadsafe
                        future = asyncio.run_coroutine_threadsafe(self.register_target(target), loop)
                        success = future.result(timeout=5)
                    else:
                        # 如果没有运行事件循环，直接运行
                        success = asyncio.run(self.register_target(target))
                except RuntimeError:
                    # 没有事件循环，创建新的
                    success = asyncio.run(self.register_target(target))
                
                if success:
                    GLOG.INFO(f"Registered engine handler: {target_id}")
                else:
                    GLOG.ERROR(f"Failed to register engine handler: {target_id}")
                    
        except Exception as e:
            GLOG.ERROR(f"Failed to register engine handlers: {e}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息 - 同步接口"""
        try:
            stats = {
                'total_targets': len(self._targets),
                'active_targets': len([t for t in self._targets.values() 
                                     if t.status == RouteStatus.ACTIVE]),
                'total_rules': len(self._rules),
                'enabled_rules': len([r for r in self._rules.values() if r.enabled]),
                'active_routes': len(self._active_routes),
                'cache_size': len(self._route_cache),
            }
            
            # 添加目标详情
            stats['targets_detail'] = {}
            for target_id, target in self._targets.items():
                stats['targets_detail'][target_id] = {
                    'status': target.status.value,
                    'processed': target.total_processed,
                    'errors': target.total_errors,
                    'load': target.load_percentage
                }
            
            return stats
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get routing stats: {e}")
            return {}
    
    async def _do_route_event(self, event: Any) -> List[str]:
        """执行事件路由"""
        start_time = time.time()
        event_id = getattr(event, 'event_id', f"event_{uuid4().hex[:8]}")
        route_id = f"route_{uuid4().hex[:8]}"
        
        try:
            self._active_routes.add(route_id)
            
            # 检查缓存
            cache_key = await self._generate_cache_key(event)
            cached_targets = await self._get_cached_route(cache_key)
            if cached_targets is not None:
                return cached_targets
            
            # 匹配路由规则
            matching_rules = await self._match_routing_rules(event)
            
            if not matching_rules:
                GLOG.WARN(f"未找到匹配的路由规则: {getattr(event, 'event_type', 'unknown')}")
                return []
            
            # 选择路由目标
            selected_targets = []
            matched_rule_ids = []
            
            for rule in matching_rules:
                targets = await self._select_targets(rule, event)
                selected_targets.extend(targets)
                matched_rule_ids.append(rule.rule_id)
                
                # 更新规则统计
                rule.matched_count += 1
            
            # 去重并验证目标
            selected_targets = await self._validate_selected_targets(selected_targets)
            
            # 更新缓存
            await self._update_route_cache(cache_key, selected_targets)
            
            # 更新统计
            routing_time = time.time() - start_time
            success = len(selected_targets) > 0
            await self._update_routing_metrics(event_id, len(selected_targets), routing_time, success, matched_rule_ids)
            
            # 更新负载均衡器和断路器统计
            await self._update_target_metrics(selected_targets, routing_time, success)
            
            # 记录路由历史
            route_result = RouteResult(
                event_id=event_id,
                targets=selected_targets,
                success=success,
                routing_time=routing_time,
                matched_rules=matched_rule_ids
            )
            self._route_history.append(route_result)
            
            # 触发成功事件
            if success:
                await self._emit_event(RoutingEventType.ROUTING_SUCCESS, {
                    'event_id': event_id,
                    'targets_count': len(selected_targets),
                    'routing_time': routing_time
                })
            
            return selected_targets
        
        except Exception as e:
            routing_time = time.time() - start_time
            await self._update_routing_metrics(event_id, 0, routing_time, False, [])
            
            # 触发失败事件
            await self._emit_event(RoutingEventType.ROUTING_FAILURE, {
                'event_id': event_id,
                'error': str(e),
                'routing_time': routing_time
            })
            
            GLOG.ERROR(f"路由事件失败: {e}")
            return []
        
        finally:
            self._active_routes.discard(route_id)
    
    async def _update_target_metrics(self, targets: List[str], routing_time: float, success: bool) -> None:
        """更新目标指标"""
        for target_id in targets:
            # 更新负载均衡器指标
            for balancer in self._load_balancers.values():
                await balancer.update_target_metrics(target_id, routing_time, success)
            
            # 更新断路器状态
            if target_id in self._circuit_breakers:
                circuit_breaker = self._circuit_breakers[target_id]
                if success:
                    circuit_breaker.record_success()
                else:
                    circuit_breaker.record_failure()
            
            # 更新目标自身的指标
            if target_id in self._targets:
                target = self._targets[target_id]
                target.total_processed += 1
                if not success:
                    target.total_errors += 1
                
                # 更新平均响应时间 (使用简单移动平均)
                alpha = 0.1  # 平滑因子
                if target.avg_response_time == 0:
                    target.avg_response_time = routing_time
                else:
                    target.avg_response_time = (1 - alpha) * target.avg_response_time + alpha * routing_time
    
    async def route_events(self, events: List[Any]) -> Dict[str, List[str]]:
        """批量路由事件"""
        results = {}
        
        # 并发路由所有事件
        tasks = [self.route_event(event) for event in events]
        routes = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        for i, (event, route_result) in enumerate(zip(events, routes)):
            event_id = getattr(event, 'event_id', f"event_{i}")
            
            if isinstance(route_result, Exception):
                GLOG.ERROR(f"批量路由事件失败 {event_id}: {route_result}")
                results[event_id] = []
            else:
                results[event_id] = route_result
        
        return results
    
    # === 指标和监控 ===
    
    async def get_routing_metrics(self) -> RoutingMetrics:
        """获取路由指标"""
        async with self._metrics_lock:
            await self._calculate_metrics()
            return self._metrics
    
    async def reset_metrics(self) -> None:
        """重置指标"""
        async with self._metrics_lock:
            self._metrics = RoutingMetrics()
            self._route_history.clear()
            self._performance_tracker.clear()
            
            # 重置规则统计
            async with self._rules_lock:
                for rule in self._rules.values():
                    rule.matched_count = 0
                    rule.success_count = 0
                    rule.error_count = 0
            
            # 重置目标统计
            async with self._targets_lock:
                for target in self._targets.values():
                    target.total_processed = 0
                    target.total_errors = 0
                    target.avg_response_time = 0.0
            
            GLOG.INFO("路由指标已重置")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_data = {
            'center_id': self.center_id,
            'timestamp': clock_now().isoformat(),
            'is_running': self._is_running,
            'total_targets': len(self._targets),
            'active_targets': len([t for t in self._targets.values() if t.status == RouteStatus.ACTIVE]),
            'total_rules': len(self._rules),
            'enabled_rules': len([r for r in self._rules.values() if r.enabled]),
            'active_routes': len(self._active_routes),
            'cache_size': len(self._route_cache),
            'targets_health': {},
            'system_health': {
                'memory_usage': 0,  # TODO: 实现内存监控
                'cpu_usage': 0,     # TODO: 实现CPU监控
                'thread_pool_size': self._thread_pool._threads,
                'semaphore_available': self._route_semaphore._value
            }
        }
        
        # 检查目标健康状态
        async with self._targets_lock:
            for target_id, target in self._targets.items():
                target_health = {
                    'status': target.status.value,
                    'health_score': target.health_score,
                    'load_percentage': target.load_percentage,
                    'error_rate': target.error_rate,
                    'total_processed': target.total_processed,
                    'total_errors': target.total_errors,
                    'avg_response_time': target.avg_response_time,
                    'last_health_check': target.last_health_check.isoformat() if target.last_health_check else None
                }
                
                # 断路器状态
                if target_id in self._circuit_breakers:
                    cb = self._circuit_breakers[target_id]
                    target_health['circuit_breaker'] = {
                        'state': cb.get_state().value,
                        'is_open': cb.is_open()
                    }
                
                health_data['targets_health'][target_id] = target_health
        
        return health_data
    
    async def reload_configuration(self, config: Dict[str, Any]) -> bool:
        """重新加载配置"""
        try:
            GLOG.INFO("开始重新加载路由配置")
            
            # 重新加载目标配置
            if 'targets' in config:
                await self._reload_targets(config['targets'])
            
            # 重新加载规则配置
            if 'rules' in config:
                await self._reload_rules(config['rules'])
            
            # 重新加载系统配置
            if 'system' in config:
                await self._reload_system_config(config['system'])
            
            GLOG.INFO("路由配置重新加载成功")
            return True
        
        except Exception as e:
            GLOG.ERROR(f"重新加载路由配置失败: {e}")
            return False
    
    # === 内部辅助方法 ===
    
    async def _validate_target(self, target: RouteTarget) -> bool:
        """验证路由目标"""
        if not target.target_id:
            GLOG.ERROR("目标ID不能为空")
            return False
        
        if target.target_id in self._targets:
            GLOG.ERROR(f"目标已存在: {target.target_id}")
            return False
        
        if not target.target_instance:
            GLOG.ERROR("目标实例不能为空")
            return False
        
        if target.max_concurrent <= 0:
            GLOG.ERROR("最大并发数必须大于0")
            return False
        
        return True
    
    async def _validate_rule(self, rule: RoutingRule) -> bool:
        """验证路由规则"""
        if not rule.rule_id:
            GLOG.ERROR("规则ID不能为空")
            return False
        
        if rule.rule_id in self._rules:
            GLOG.ERROR(f"规则已存在: {rule.rule_id}")
            return False
        
        if not rule.targets:
            GLOG.ERROR("规则必须包含至少一个目标")
            return False
        
        # 检查目标是否存在
        async with self._targets_lock:
            for target_id in rule.targets:
                if target_id not in self._targets:
                    GLOG.ERROR(f"规则中的目标不存在: {target_id}")
                    return False
        
        return True
    
    async def _match_routing_rules(self, event: Any) -> List[RoutingRule]:
        """匹配路由规则"""
        matching_rules = []
        
        for rule, patterns in self._compiled_rules:
            if not rule.enabled:
                continue
            
            # 检查时间有效性
            if not rule.is_time_valid:
                continue
            
            # 检查模式匹配
            if await self._rule_matches_event(rule, patterns, event):
                matching_rules.append(rule)
        
        # 按权重排序
        matching_rules.sort(key=lambda r: r.weight, reverse=True)
        
        return matching_rules
    
    async def _rule_matches_event(self, rule: RoutingRule, patterns: List[Optional[Pattern]], event: Any) -> bool:
        """检查规则是否匹配事件"""
        # 事件类型匹配
        event_type = str(getattr(event, 'event_type', ''))
        if patterns[0] and not patterns[0].match(event_type):
            return False
        
        # 来源匹配
        event_source = str(getattr(event, 'source', ''))
        if patterns[1] and not patterns[1].match(event_source):
            return False
        
        # 优先级匹配
        event_priority = getattr(event, 'priority', EventPriority.NORMAL)
        if isinstance(event_priority, int):
            priority_value = event_priority
        else:
            priority_value = event_priority.value
            
        if not (rule.priority_range[0] <= priority_value <= rule.priority_range[1]):
            return False
        
        # 自定义条件匹配
        for condition in rule.custom_conditions:
            try:
                if not condition(event):
                    return False
            except Exception as e:
                GLOG.ERROR(f"自定义条件评估失败: {e}")
                return False
        
        return True
    
    async def _select_targets(self, rule: RoutingRule, event: Any) -> List[str]:
        """选择路由目标"""
        available_targets = []
        
        # 获取可用目标
        async with self._targets_lock:
            for target_id in rule.targets:
                if target_id not in self._targets:
                    continue
                
                target = self._targets[target_id]
                
                # 检查目标状态
                if target.status != RouteStatus.ACTIVE:
                    continue
                
                # 检查负载限制
                if target.is_overloaded:
                    continue
                
                # 检查断路器
                if target.circuit_breaker_enabled and target_id in self._circuit_breakers:
                    cb = self._circuit_breakers[target_id]
                    if cb.is_open():
                        continue
                
                available_targets.append(target_id)
        
        if not available_targets:
            return []
        
        # 使用负载均衡器选择目标
        if rule.strategy in self._load_balancers:
            load_balancer = self._load_balancers[rule.strategy]
            return await load_balancer.select_targets(available_targets, rule, event, self._targets)
        else:
            # 默认选择第一个可用目标
            return [available_targets[0]]
    
    async def _validate_selected_targets(self, targets: List[str]) -> List[str]:
        """验证选择的目标"""
        validated_targets = []
        
        async with self._targets_lock:
            for target_id in targets:
                if target_id in self._targets:
                    target = self._targets[target_id]
                    if target.status == RouteStatus.ACTIVE and not target.is_overloaded:
                        validated_targets.append(target_id)
        
        # 去重
        return list(dict.fromkeys(validated_targets))
    
    async def _recompile_rules(self) -> None:
        """重新编译路由规则"""
        async with self._rules_lock:
            self._compiled_rules.clear()
            
            for rule in self._rules.values():
                patterns = []
                
                # 编译事件类型模式
                if rule.event_type_pattern != "*":
                    pattern = self._glob_to_regex(rule.event_type_pattern)
                    try:
                        patterns.append(re.compile(pattern))
                    except re.error as e:
                        GLOG.ERROR(f"编译事件类型模式失败 {rule.event_type_pattern}: {e}")
                        patterns.append(None)
                else:
                    patterns.append(None)
                
                # 编译来源模式
                if rule.source_pattern != "*":
                    pattern = self._glob_to_regex(rule.source_pattern)
                    try:
                        patterns.append(re.compile(pattern))
                    except re.error as e:
                        GLOG.ERROR(f"编译来源模式失败 {rule.source_pattern}: {e}")
                        patterns.append(None)
                else:
                    patterns.append(None)
                
                self._compiled_rules.append((rule, patterns))
        
        GLOG.INFO(f"重新编译了 {len(self._compiled_rules)} 个路由规则")
    
    def _glob_to_regex(self, pattern: str) -> str:
        """将glob模式转换为正则表达式"""
        # 转义特殊字符
        regex = re.escape(pattern)
        # 替换转义后的通配符
        regex = regex.replace(r'\*', '.*')
        regex = regex.replace(r'\?', '.')
        return f'^{regex}$'
    
    async def _generate_cache_key(self, event: Any) -> str:
        """生成缓存键"""
        key_parts = [
            str(getattr(event, 'event_type', '')),
            str(getattr(event, 'source', '')),
            str(getattr(event, 'priority', EventPriority.NORMAL))
        ]
        
        # 添加自定义键值对
        custom_attrs = getattr(event, '__routing_attrs__', {})
        for key, value in sorted(custom_attrs.items()):
            key_parts.append(f"{key}={value}")
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _get_cached_route(self, cache_key: str) -> Optional[List[str]]:
        """获取缓存的路由结果"""
        async with self._cache_lock:
            if cache_key in self._route_cache:
                cache_time = self._cache_timestamps.get(cache_key)
                if cache_time and (clock_now() - cache_time).seconds < self.cache_ttl:
                    return self._route_cache[cache_key]
                else:
                    # 过期缓存清理
                    del self._route_cache[cache_key]
                    if cache_key in self._cache_timestamps:
                        del self._cache_timestamps[cache_key]
        
        return None
    
    async def _update_route_cache(self, cache_key: str, targets: List[str]) -> None:
        """更新路由缓存"""
        async with self._cache_lock:
            self._route_cache[cache_key] = targets
            self._cache_timestamps[cache_key] = clock_now()
    
    async def _clear_target_cache(self, target_id: str) -> None:
        """清理目标相关缓存"""
        async with self._cache_lock:
            keys_to_remove = []
            for key, targets in self._route_cache.items():
                if target_id in targets:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._route_cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
    
    async def _update_routing_metrics(self, event_id: str, target_count: int, 
                                    routing_time: float, success: bool, 
                                    matched_rules: List[str]) -> None:
        """更新路由指标"""
        async with self._metrics_lock:
            self._metrics.total_events += 1
            
            if success and target_count > 0:
                self._metrics.successful_routes += 1
            else:
                self._metrics.failed_routes += 1
            
            # 更新平均路由时间
            total_routes = self._metrics.successful_routes + self._metrics.failed_routes
            current_avg = self._metrics.avg_routing_time
            self._metrics.avg_routing_time = (current_avg * (total_routes - 1) + routing_time) / total_routes
            
            # 记录性能数据
            self._performance_tracker['routing_times'].append(routing_time)
            
            # 更新规则统计
            async with self._rules_lock:
                for rule_id in matched_rules:
                    if rule_id in self._rules:
                        rule = self._rules[rule_id]
                        if success:
                            rule.success_count += 1
                        else:
                            rule.error_count += 1
            
            self._metrics.last_update = clock_now()
    
    async def _calculate_metrics(self) -> None:
        """计算指标"""
        # 计算吞吐量
        now = clock_now()
        window_start = now - timedelta(seconds=self._metrics_window_size)
        
        recent_routes = [
            route for route in self._route_history
            if isinstance(route, RouteResult) and route.timestamp >= window_start
        ]
        
        if recent_routes:
            self._metrics.throughput_per_second = len(recent_routes) / self._metrics_window_size
        else:
            self._metrics.throughput_per_second = 0.0
        
        # 计算规则统计
        self._metrics.rules_stats.clear()
        async with self._rules_lock:
            for rule in self._rules.values():
                self._metrics.rules_stats[rule.rule_id] = {
                    'matched': rule.matched_count,
                    'success': rule.success_count,
                    'errors': rule.error_count,
                    'success_rate': rule.success_rate
                }
        
        # 计算目标统计
        self._metrics.targets_stats.clear()
        async with self._targets_lock:
            for target_id, target in self._targets.items():
                self._metrics.targets_stats[target_id] = {
                    'status': target.status.value,
                    'current_load': target.current_load,
                    'load_percentage': target.load_percentage,
                    'total_processed': target.total_processed,
                    'total_errors': target.total_errors,
                    'error_rate': target.error_rate,
                    'avg_response_time': target.avg_response_time,
                    'health_score': target.health_score
                }
    
    async def _initialize_load_balancers(self) -> None:
        """初始化负载均衡器"""
        # 负载均衡器实现将在后续添加
        # self._load_balancers = {
        #     RoutingStrategy.ROUND_ROBIN: RoundRobinBalancer(),
        #     RoutingStrategy.WEIGHTED: WeightedBalancer(),
        #     ...
        # }
        pass
    
    async def _start_background_tasks(self) -> None:
        """启动后台任务"""
        # 健康检查任务
        task = asyncio.create_task(self._health_check_task())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # 指标计算任务
        task = asyncio.create_task(self._metrics_calculation_task())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # 缓存清理任务
        task = asyncio.create_task(self._cache_cleanup_task())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def _health_check_task(self) -> None:
        """健康检查任务"""
        while self._is_running and not self._shutdown_event.is_set():
            try:
                async with self._targets_lock:
                    targets = list(self._targets.values())
                
                for target in targets:
                    await self._check_target_health(target)
                
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.health_check_interval
                )
            except asyncio.TimeoutError:
                # 正常超时，继续下一次检查
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                GLOG.ERROR(f"健康检查任务出错: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _metrics_calculation_task(self) -> None:
        """指标计算任务"""
        while self._is_running and not self._shutdown_event.is_set():
            try:
                await self._calculate_metrics()
                
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=60  # 每分钟计算一次
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                GLOG.ERROR(f"指标计算任务出错: {e}")
                await asyncio.sleep(60)
    
    async def _cache_cleanup_task(self) -> None:
        """缓存清理任务"""
        while self._is_running and not self._shutdown_event.is_set():
            try:
                now = clock_now()
                expired_keys = []
                
                async with self._cache_lock:
                    for key, timestamp in self._cache_timestamps.items():
                        if (now - timestamp).seconds > self.cache_ttl:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        if key in self._route_cache:
                            del self._route_cache[key]
                        if key in self._cache_timestamps:
                            del self._cache_timestamps[key]
                
                if expired_keys:
                    GLOG.DEBUG(f"清理了 {len(expired_keys)} 个过期缓存条目")
                
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=30  # 每30秒清理一次
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                GLOG.ERROR(f"缓存清理任务出错: {e}")
                await asyncio.sleep(30)
    
    async def _check_target_health(self, target: RouteTarget) -> None:
        """检查目标健康状态"""
        try:
            # 简化的健康检查逻辑
            health_score = 100.0
            
            # 基于错误率降低得分
            if target.total_processed > 0:
                error_rate = target.error_rate
                health_score -= error_rate
            
            # 基于响应时间降低得分
            if target.avg_response_time > 5.0:  # 超过5秒
                health_score -= 30
            
            # 基于当前负载降低得分
            if target.load_percentage > 80:
                health_score -= 20
            
            target.health_score = max(0, health_score)
            target.last_health_check = clock_now()
            
            # 更新目标状态
            old_status = target.status
            if target.health_score < 30:
                target.status = RouteStatus.FAILED
            elif target.health_score < 60:
                target.status = RouteStatus.DEGRADED
            else:
                target.status = RouteStatus.ACTIVE
            
            # 如果状态变化，触发事件
            if target.status != old_status:
                await self._emit_event(RoutingEventType.TARGET_STATUS_CHANGED, {
                    'target_id': target.target_id,
                    'old_status': old_status.value,
                    'new_status': target.status.value,
                    'health_score': target.health_score
                })
        
        except Exception as e:
            GLOG.ERROR(f"检查目标健康状态失败 {target.target_id}: {e}")
            target.status = RouteStatus.FAILED
    
    async def _emit_event(self, event_type: RoutingEventType, data: Dict[str, Any]) -> None:
        """发出路由事件"""
        try:
            event = RoutingEvent(
                event_type=event_type,
                source=self.center_id,
                data=data
            )
            
            # 调用事件回调
            for callback in self._event_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    GLOG.ERROR(f"路由事件回调失败: {e}")
        
        except Exception as e:
            GLOG.ERROR(f"发出路由事件失败: {e}")
    
    def add_event_callback(self, callback: callable) -> None:
        """添加事件回调"""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: callable) -> None:
        """移除事件回调"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    async def _reload_targets(self, targets_config: List[Dict[str, Any]]) -> None:
        """重新加载目标配置"""
        # TODO: 实现目标配置重加载逻辑
        GLOG.INFO("目标配置重加载功能待实现")
    
    async def _reload_rules(self, rules_config: List[Dict[str, Any]]) -> None:
        """重新加载规则配置"""
        # TODO: 实现规则配置重加载逻辑
        GLOG.INFO("规则配置重加载功能待实现")
    
    async def _reload_system_config(self, system_config: Dict[str, Any]) -> None:
        """重新加载系统配置"""
        # TODO: 实现系统配置重加载逻辑
        GLOG.INFO("系统配置重加载功能待实现")
