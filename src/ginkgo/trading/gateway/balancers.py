# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 实现 BaseLoadBalancer、RoundRobinBalancer、WeightedBalancer 等 10 个类的核心功能






"""
负载均衡器实现

提供多种负载均衡策略，包括：
- 轮询负载均衡
- 加权负载均衡
- 最少连接负载均衡
- 哈希负载均衡
- 优先级负载均衡
- 广播负载均衡
- 故障转移负载均衡
"""

import hashlib
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import timedelta
from ginkgo.trading.time.clock import now as clock_now
from collections import defaultdict, deque

from .interfaces import (
    ILoadBalancer, RouteTarget, RoutingRule, RoutingStrategy
)


class BaseLoadBalancer(ILoadBalancer):
    """负载均衡器基类"""
    
    def __init__(self):
        self._target_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
    
    async def update_target_metrics(self, target_id: str, 
                                  response_time: float, success: bool) -> None:
        """更新目标指标"""
        stats = self._target_stats[target_id]
        
        # 初始化统计
        if 'total_requests' not in stats:
            stats.update({
                'total_requests': 0,
                'total_failures': 0,
                'avg_response_time': 0.0,
                'last_request_time': None,
                'response_times': deque(maxlen=100),  # 保留最近100次响应时间
            })
        
        # 更新统计
        stats['total_requests'] += 1
        if not success:
            stats['total_failures'] += 1
        
        # 更新响应时间
        stats['response_times'].append(response_time)
        stats['avg_response_time'] = sum(stats['response_times']) / len(stats['response_times'])
        stats['last_request_time'] = clock_now()
    
    def _filter_healthy_targets(self, available_targets: List[str], 
                              targets_info: Dict[str, RouteTarget]) -> List[str]:
        """过滤健康的目标"""
        healthy_targets = []
        
        for target_id in available_targets:
            target = targets_info.get(target_id)
            if target and not target.is_overloaded and target.health_score > 50.0:
                healthy_targets.append(target_id)
        
        return healthy_targets if healthy_targets else available_targets


class RoundRobinBalancer(BaseLoadBalancer):
    """轮询负载均衡器"""
    
    def __init__(self):
        super().__init__()
        self._round_robin_index: Dict[str, int] = defaultdict(int)
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """轮询选择目标"""
        if not available_targets:
            return []
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(available_targets, targets_info)
        if not healthy_targets:
            return []
        
        # 轮询选择
        rule_key = rule.rule_id
        index = self._round_robin_index[rule_key] % len(healthy_targets)
        selected_target = healthy_targets[index]
        
        # 更新索引
        self._round_robin_index[rule_key] = (index + 1) % len(healthy_targets)
        
        return [selected_target]


class WeightedBalancer(BaseLoadBalancer):
    """加权负载均衡器"""
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """按权重选择目标"""
        if not available_targets:
            return []
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(available_targets, targets_info)
        if not healthy_targets:
            return []
        
        # 构建权重列表
        weighted_targets = []
        for target_id in healthy_targets:
            target = targets_info.get(target_id)
            weight = target.weight if target else 1
            
            # 根据健康分数调整权重
            if target:
                weight = int(weight * (target.health_score / 100.0))
                weight = max(1, weight)  # 保证最小权重为1
            
            weighted_targets.extend([target_id] * weight)
        
        # 随机选择
        if weighted_targets:
            selected_target = random.choice(weighted_targets)
            return [selected_target]
        
        return []


class LeastConnectionsBalancer(BaseLoadBalancer):
    """最少连接负载均衡器"""
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """选择连接数最少的目标"""
        if not available_targets:
            return []
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(available_targets, targets_info)
        if not healthy_targets:
            return []
        
        # 选择当前负载最小的目标
        min_load = float('inf')
        selected_targets = []
        
        for target_id in healthy_targets:
            target = targets_info.get(target_id)
            current_load = target.current_load if target else 0
            
            if current_load < min_load:
                min_load = current_load
                selected_targets = [target_id]
            elif current_load == min_load:
                selected_targets.append(target_id)
        
        # 如果有多个相同负载的目标，随机选择一个
        return [random.choice(selected_targets)] if selected_targets else []


class HashBasedBalancer(BaseLoadBalancer):
    """哈希负载均衡器"""
    
    def _get_hash_key(self, event: Any) -> str:
        """获取事件的哈希键"""
        # 尝试从事件中提取关键字段
        if hasattr(event, 'symbol'):
            return str(event.symbol)
        elif hasattr(event, 'source'):
            return str(event.source)
        elif hasattr(event, 'event_id'):
            return str(event.event_id)
        elif hasattr(event, 'id'):
            return str(event.id)
        else:
            # 使用事件的字符串表示
            return str(event)
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """基于哈希选择目标"""
        if not available_targets:
            return []
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(available_targets, targets_info)
        if not healthy_targets:
            return []
        
        # 对目标列表排序，确保一致性
        sorted_targets = sorted(healthy_targets)
        
        # 计算哈希
        hash_key = self._get_hash_key(event)
        hash_value = hashlib.md5(hash_key.encode()).hexdigest()
        hash_int = int(hash_value[:8], 16)
        
        # 选择目标
        index = hash_int % len(sorted_targets)
        selected_target = sorted_targets[index]
        
        return [selected_target]


class PriorityBasedBalancer(BaseLoadBalancer):
    """优先级负载均衡器"""
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """按优先级选择目标"""
        if not available_targets:
            return []
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(available_targets, targets_info)
        if not healthy_targets:
            return []
        
        # 按优先级分组
        priority_groups: Dict[int, List[str]] = defaultdict(list)
        
        for target_id in healthy_targets:
            target = targets_info.get(target_id)
            priority = target.priority.value if target else 5  # 默认正常优先级
            priority_groups[priority].append(target_id)
        
        # 选择最高优先级组
        if priority_groups:
            highest_priority = max(priority_groups.keys())
            highest_priority_targets = priority_groups[highest_priority]
            
            # 在最高优先级组中随机选择
            selected_target = random.choice(highest_priority_targets)
            return [selected_target]
        
        return []


class BroadcastBalancer(BaseLoadBalancer):
    """广播负载均衡器"""
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """选择所有可用目标进行广播"""
        if not available_targets:
            return []
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(available_targets, targets_info)
        
        # 返回所有健康目标
        return healthy_targets


class FailoverBalancer(BaseLoadBalancer):
    """故障转移负载均衡器"""
    
    def __init__(self):
        super().__init__()
        self._primary_targets: Dict[str, str] = {}  # rule_id -> primary_target_id
        self._failover_history: Dict[str, List[str]] = defaultdict(list)  # 故障转移历史
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """故障转移选择目标"""
        if not available_targets:
            return []
        
        rule_key = rule.rule_id
        
        # 获取主目标
        primary_target = self._primary_targets.get(rule_key)
        
        # 如果没有设置主目标，选择第一个可用目标作为主目标
        if not primary_target or primary_target not in available_targets:
            # 选择权重最高的目标作为主目标
            best_target = None
            best_score = -1
            
            for target_id in available_targets:
                target = targets_info.get(target_id)
                if target:
                    # 综合权重和健康分数
                    score = target.weight * (target.health_score / 100.0)
                    if score > best_score and not target.is_overloaded:
                        best_score = score
                        best_target = target_id
            
            if best_target:
                self._primary_targets[rule_key] = best_target
                primary_target = best_target
        
        # 检查主目标是否健康
        if primary_target:
            target = targets_info.get(primary_target)
            if target and not target.is_overloaded and target.health_score > 30.0:
                return [primary_target]
            else:
                # 记录故障转移
                self._failover_history[rule_key].append(primary_target)
        
        # 主目标不可用，选择备用目标
        fallback_candidates = [
            t for t in available_targets 
            if t != primary_target and t not in self._failover_history[rule_key][-5:]  # 避免最近5个故障目标
        ]
        
        if not fallback_candidates:
            # 如果没有备用候选，重置故障历史并选择除主目标外的任意目标
            self._failover_history[rule_key].clear()
            fallback_candidates = [t for t in available_targets if t != primary_target]
        
        if fallback_candidates:
            # 选择健康分数最高的备用目标
            best_fallback = max(
                fallback_candidates,
                key=lambda t: targets_info.get(t, RouteTarget(target_id=t, target_type="", target_instance=None)).health_score
            )
            return [best_fallback]
        
        # 如果所有备用都不可用，返回主目标（即使不健康）
        return [primary_target] if primary_target else []


class ConditionalBalancer(BaseLoadBalancer):
    """条件负载均衡器"""
    
    async def select_targets(self, 
                           available_targets: List[str], 
                           rule: RoutingRule, 
                           event: Any,
                           targets_info: Dict[str, RouteTarget]) -> List[str]:
        """基于自定义条件选择目标"""
        if not available_targets:
            return []
        
        # 应用自定义条件过滤
        filtered_targets = []
        for target_id in available_targets:
            target = targets_info.get(target_id)
            if target:
                # 检查所有自定义条件
                meets_all_conditions = True
                for condition in rule.custom_conditions:
                    try:
                        if not condition(event):
                            meets_all_conditions = False
                            break
                    except Exception:
                        # 条件检查异常，跳过该目标
                        meets_all_conditions = False
                        break
                
                if meets_all_conditions:
                    filtered_targets.append(target_id)
        
        # 如果没有目标满足条件，回退到所有可用目标
        if not filtered_targets:
            filtered_targets = available_targets
        
        # 过滤健康目标
        healthy_targets = self._filter_healthy_targets(filtered_targets, targets_info)
        if not healthy_targets:
            return []
        
        # 随机选择一个目标
        return [random.choice(healthy_targets)]


# 负载均衡器工厂
class LoadBalancerFactory:
    """负载均衡器工厂"""
    
    _balancers = {
        RoutingStrategy.ROUND_ROBIN: RoundRobinBalancer,
        RoutingStrategy.WEIGHTED: WeightedBalancer,
        RoutingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer,
        RoutingStrategy.HASH_BASED: HashBasedBalancer,
        RoutingStrategy.PRIORITY_BASED: PriorityBasedBalancer,
        RoutingStrategy.BROADCAST: BroadcastBalancer,
        RoutingStrategy.FAILOVER: FailoverBalancer,
        RoutingStrategy.CONDITIONAL: ConditionalBalancer,
    }
    
    @classmethod
    def create_balancer(cls, strategy: RoutingStrategy) -> ILoadBalancer:
        """创建负载均衡器"""
        balancer_class = cls._balancers.get(strategy)
        if not balancer_class:
            raise ValueError(f"Unsupported routing strategy: {strategy}")
        
        return balancer_class()
    
    @classmethod
    def get_available_strategies(cls) -> List[RoutingStrategy]:
        """获取可用的负载均衡策略"""
        return list(cls._balancers.keys())
