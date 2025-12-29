# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: ResourceOptimizer资源优化器提供资源优化配置支持系统优化支持交易系统功能支持相关功能






"""
资源优化算法模块

该模块提供了多种资源分配策略，用于在资金和持仓约束下优化信号到订单的转换。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import math

from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG


class OptimizationStrategy(Enum):
    """优化策略枚举"""
    EQUAL_WEIGHT = "equal_weight"        # 等权重分配
    PRIORITY_WEIGHT = "priority_weight"   # 基于优先级加权
    KELLY_CRITERION = "kelly_criterion"   # 凯利公式
    RISK_PARITY = "risk_parity"          # 风险平价
    MOMENTUM_WEIGHT = "momentum_weight"   # 动量加权


@dataclass
class AllocationConstraints:
    """分配约束条件"""
    max_total_allocation: float = 0.8      # 最大总资金使用比例
    max_single_position: float = 0.2       # 单个股票最大仓位比例
    min_order_value: float = 1000.0        # 最小订单金额
    max_positions_count: int = 20           # 最大持仓数量
    sector_limits: Dict[str, float] = None  # 行业限制（如果有）
    
    def __post_init__(self):
        if self.sector_limits is None:
            self.sector_limits = {}


class ResourceOptimizer:
    """
    资源优化器
    
    负责将批量信号在各种约束条件下优化分配为订单。
    提供多种优化策略以适应不同的投资风格和风险偏好。
    """
    
    def __init__(self, 
                 strategy: OptimizationStrategy = OptimizationStrategy.PRIORITY_WEIGHT,
                 constraints: Optional[AllocationConstraints] = None,
                 logger=None):
        """
        初始化资源优化器
        
        Args:
            strategy: 优化策略
            constraints: 约束条件
            logger: 日志记录器
        """
        self.strategy = strategy
        self.constraints = constraints or AllocationConstraints()
        self.logger = logger or GLOG
        
        # 策略映射
        self._strategy_map = {
            OptimizationStrategy.EQUAL_WEIGHT: self._equal_weight_allocation,
            OptimizationStrategy.PRIORITY_WEIGHT: self._priority_weight_allocation,
            OptimizationStrategy.KELLY_CRITERION: self._kelly_criterion_allocation,
            OptimizationStrategy.RISK_PARITY: self._risk_parity_allocation,
            OptimizationStrategy.MOMENTUM_WEIGHT: self._momentum_weight_allocation,
        }
    
    def optimize(self, signals: List[Signal], 
                portfolio_info: Dict[str, Any]) -> List[Order]:
        """
        优化信号分配
        
        Args:
            signals: 信号列表
            portfolio_info: 组合信息
            
        Returns:
            优化后的订单列表
        """
        if not signals:
            return []
            
        try:
            # 预处理：过滤和验证信号
            valid_signals = self._filter_valid_signals(signals, portfolio_info)
            if not valid_signals:
                self.logger.WARN("No valid signals after filtering")
                return []
            
            # 获取可用资金
            available_capital = self._get_available_capital(portfolio_info)
            max_allocation = available_capital * self.constraints.max_total_allocation
            
            if max_allocation <= 0:
                self.logger.WARN("No capital available for allocation")
                return []
            
            # 执行选定的优化策略
            allocation_func = self._strategy_map.get(self.strategy)
            if not allocation_func:
                self.logger.ERROR(f"Unknown optimization strategy: {self.strategy}")
                return []
                
            allocations = allocation_func(valid_signals, max_allocation, portfolio_info)
            
            # 转换为订单
            orders = self._create_orders_from_allocations(allocations, portfolio_info)
            
            # 最终验证和调整
            validated_orders = self._validate_and_adjust_orders(orders, portfolio_info)
            
            self.logger.INFO(f"Resource optimization completed: {len(validated_orders)} orders from {len(signals)} signals")
            return validated_orders
            
        except Exception as e:
            self.logger.ERROR(f"Resource optimization failed: {e}")
            return []
    
    def _filter_valid_signals(self, signals: List[Signal], 
                            portfolio_info: Dict[str, Any]) -> List[Signal]:
        """
        过滤有效信号
        
        Args:
            signals: 原始信号列表
            portfolio_info: 组合信息
            
        Returns:
            过滤后的有效信号列表
        """
        valid_signals = []
        existing_positions = portfolio_info.get('positions', {})
        
        for signal in signals:
            try:
                # 基础验证
                if not signal.code or not signal.direction:
                    continue
                    
                # 做空信号需要检查是否有持仓
                if signal.direction == DIRECTION_TYPES.SHORT:
                    if signal.code not in existing_positions:
                        self.logger.DEBUG(f"Skip SHORT signal for {signal.code}: no existing position")
                        continue
                        
                # 检查最大持仓数量限制
                if (signal.direction == DIRECTION_TYPES.LONG and 
                    len(existing_positions) >= self.constraints.max_positions_count):
                    self.logger.DEBUG(f"Skip LONG signal for {signal.code}: max positions reached")
                    continue
                    
                valid_signals.append(signal)
                
            except Exception as e:
                self.logger.ERROR(f"Error validating signal {signal.code}: {e}")
                continue
                
        return valid_signals
    
    def _get_available_capital(self, portfolio_info: Dict[str, Any]) -> float:
        """
        获取可用资金
        
        Args:
            portfolio_info: 组合信息
            
        Returns:
            可用资金金额
        """
        return float(portfolio_info.get('available_cash', 0))
    
    def _equal_weight_allocation(self, signals: List[Signal], 
                               max_allocation: float, 
                               portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        等权重分配策略
        
        Args:
            signals: 信号列表
            max_allocation: 最大分配金额
            portfolio_info: 组合信息
            
        Returns:
            股票代码到分配金额的映射
        """
        if not signals:
            return {}
            
        allocation_per_signal = max_allocation / len(signals)
        allocations = {}
        
        for signal in signals:
            # 应用单个持仓限制
            max_single_allocation = portfolio_info.get('total_value', max_allocation) * self.constraints.max_single_position
            final_allocation = min(allocation_per_signal, max_single_allocation)
            
            if final_allocation >= self.constraints.min_order_value:
                allocations[signal.code] = final_allocation
                
        return allocations
    
    def _priority_weight_allocation(self, signals: List[Signal], 
                                  max_allocation: float, 
                                  portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        基于优先级的加权分配策略
        
        Args:
            signals: 信号列表
            max_allocation: 最大分配金额
            portfolio_info: 组合信息
            
        Returns:
            股票代码到分配金额的映射
        """
        if not signals:
            return {}
            
        # 计算权重
        weights = []
        for signal in signals:
            priority = getattr(signal, 'priority', 50)  # 默认优先级50
            confidence = getattr(signal, 'confidence', 0.5)  # 默认置信度0.5
            
            # 综合权重：优先级 * 置信度
            weight = (priority / 100.0) * confidence
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight <= 0:
            # 回退到等权重
            return self._equal_weight_allocation(signals, max_allocation, portfolio_info)
        
        allocations = {}
        portfolio_value = portfolio_info.get('total_value', max_allocation)
        
        for signal, weight in zip(signals, weights):
            allocation = max_allocation * (weight / total_weight)
            
            # 应用约束
            max_single_allocation = portfolio_value * self.constraints.max_single_position
            final_allocation = min(allocation, max_single_allocation)
            
            if final_allocation >= self.constraints.min_order_value:
                allocations[signal.code] = final_allocation
                
        return allocations
    
    def _kelly_criterion_allocation(self, signals: List[Signal], 
                                  max_allocation: float, 
                                  portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        凯利公式分配策略
        
        根据信号的胜率和盈亏比使用凯利公式计算最优仓位
        
        Args:
            signals: 信号列表
            max_allocation: 最大分配金额
            portfolio_info: 组合信息
            
        Returns:
            股票代码到分配金额的映射
        """
        allocations = {}
        
        for signal in signals:
            try:
                # 获取信号的统计信息
                win_rate = getattr(signal, 'win_rate', 0.55)  # 胜率
                avg_win = getattr(signal, 'avg_win', 0.15)    # 平均盈利率
                avg_loss = getattr(signal, 'avg_loss', 0.10)   # 平均亏损率
                
                # 凯利公式: f* = (bp - q) / b
                # 其中 b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
                if avg_loss > 0:
                    b = avg_win / avg_loss
                    p = win_rate
                    q = 1 - win_rate
                    
                    kelly_fraction = (b * p - q) / b
                    kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制在0-25%之间
                    
                    allocation = max_allocation * kelly_fraction
                    
                    # 应用约束
                    portfolio_value = portfolio_info.get('total_value', max_allocation)
                    max_single_allocation = portfolio_value * self.constraints.max_single_position
                    final_allocation = min(allocation, max_single_allocation)
                    
                    if final_allocation >= self.constraints.min_order_value:
                        allocations[signal.code] = final_allocation
                        
            except Exception as e:
                self.logger.ERROR(f"Kelly calculation failed for {signal.code}: {e}")
                continue
                
        # 如果凯利公式分配结果为空，回退到优先级权重
        if not allocations:
            return self._priority_weight_allocation(signals, max_allocation, portfolio_info)
            
        return allocations
    
    def _risk_parity_allocation(self, signals: List[Signal], 
                              max_allocation: float, 
                              portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        风险平价分配策略
        
        根据信号的风险水平进行反向分配，风险低的分配更多资金
        
        Args:
            signals: 信号列表
            max_allocation: 最大分配金额
            portfolio_info: 组合信息
            
        Returns:
            股票代码到分配金额的映射
        """
        if not signals:
            return {}
            
        # 计算风险权重（风险越低权重越高）
        risk_weights = []
        for signal in signals:
            volatility = getattr(signal, 'volatility', 0.2)  # 默认波动率20%
            risk_score = getattr(signal, 'risk_score', 50)   # 默认风险评分50
            
            # 综合风险度量（归一化到0-1）
            combined_risk = (volatility + risk_score / 100.0) / 2
            
            # 风险权重：风险越低权重越高
            risk_weight = 1 / (combined_risk + 0.01)  # 避免除零
            risk_weights.append(risk_weight)
        
        total_risk_weight = sum(risk_weights)
        
        allocations = {}
        portfolio_value = portfolio_info.get('total_value', max_allocation)
        
        for signal, risk_weight in zip(signals, risk_weights):
            allocation = max_allocation * (risk_weight / total_risk_weight)
            
            # 应用约束
            max_single_allocation = portfolio_value * self.constraints.max_single_position
            final_allocation = min(allocation, max_single_allocation)
            
            if final_allocation >= self.constraints.min_order_value:
                allocations[signal.code] = final_allocation
                
        return allocations
    
    def _momentum_weight_allocation(self, signals: List[Signal], 
                                  max_allocation: float, 
                                  portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        动量加权分配策略
        
        根据信号的动量强度进行分配
        
        Args:
            signals: 信号列表
            max_allocation: 最大分配金额
            portfolio_info: 组合信息
            
        Returns:
            股票代码到分配金额的映射
        """
        if not signals:
            return {}
            
        momentum_weights = []
        for signal in signals:
            momentum = getattr(signal, 'momentum', 0.0)  # 动量指标
            strength = getattr(signal, 'strength', 1.0)   # 信号强度
            
            # 综合动量权重
            momentum_weight = abs(momentum) * strength
            momentum_weights.append(momentum_weight)
        
        total_momentum_weight = sum(momentum_weights)
        if total_momentum_weight <= 0:
            return self._equal_weight_allocation(signals, max_allocation, portfolio_info)
        
        allocations = {}
        portfolio_value = portfolio_info.get('total_value', max_allocation)
        
        for signal, momentum_weight in zip(signals, momentum_weights):
            allocation = max_allocation * (momentum_weight / total_momentum_weight)
            
            # 应用约束
            max_single_allocation = portfolio_value * self.constraints.max_single_position
            final_allocation = min(allocation, max_single_allocation)
            
            if final_allocation >= self.constraints.min_order_value:
                allocations[signal.code] = final_allocation
                
        return allocations
    
    def _create_orders_from_allocations(self, allocations: Dict[str, float], 
                                      portfolio_info: Dict[str, Any]) -> List[Order]:
        """
        从分配金额创建订单
        
        Args:
            allocations: 股票代码到分配金额的映射
            portfolio_info: 组合信息
            
        Returns:
            订单列表
        """
        orders = []
        
        for code, allocation in allocations.items():
            try:
                # 这里需要获取当前价格，简化处理
                # 实际实现中应该从数据源获取最新价格
                estimated_price = 10.0  # 简化的估算价格
                
                # 计算交易数量（向下取整到手数）
                volume = int(allocation / estimated_price)
                volume = (volume // 100) * 100  # 向下取整到100股的倍数
                
                if volume > 0:
                    order = Order(
                        code=code,
                        direction=DIRECTION_TYPES.LONG,  # 简化处理，实际应该从信号获取
                        volume=volume,
                        limit_price=estimated_price,
                        frozen=estimated_price * volume,
                        timestamp=portfolio_info.get('current_time'),
                        portfolio_id=portfolio_info.get('portfolio_id', ''),
                        engine_id=portfolio_info.get('engine_id', '')
                    )
                    orders.append(order)
                    
            except Exception as e:
                self.logger.ERROR(f"Error creating order for {code}: {e}")
                continue
                
        return orders
    
    def _validate_and_adjust_orders(self, orders: List[Order], 
                                  portfolio_info: Dict[str, Any]) -> List[Order]:
        """
        验证和调整订单
        
        Args:
            orders: 原始订单列表
            portfolio_info: 组合信息
            
        Returns:
            验证后的订单列表
        """
        validated_orders = []
        total_frozen = 0
        
        available_capital = self._get_available_capital(portfolio_info)
        max_total_frozen = available_capital * self.constraints.max_total_allocation
        
        # 按冻结金额排序（从大到小），优先满足大订单
        sorted_orders = sorted(orders, key=lambda o: o.frozen, reverse=True)
        
        for order in sorted_orders:
            if total_frozen + order.frozen <= max_total_frozen:
                validated_orders.append(order)
                total_frozen += order.frozen
            else:
                # 尝试调整订单大小
                remaining_capital = max_total_frozen - total_frozen
                if remaining_capital >= self.constraints.min_order_value:
                    adjusted_volume = int(remaining_capital / order.limit_price)
                    adjusted_volume = (adjusted_volume // 100) * 100  # 取整到手数
                    
                    if adjusted_volume > 0:
                        order.volume = adjusted_volume
                        order.frozen = order.limit_price * adjusted_volume
                        validated_orders.append(order)
                        total_frozen += order.frozen
                        
        self.logger.INFO(f"Order validation: {len(validated_orders)}/{len(orders)} orders approved, "
                        f"total frozen: {total_frozen:.2f}")
        
        return validated_orders