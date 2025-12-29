# Upstream: All Modules
# Downstream: Standard Library
# Role: PortfolioInterface组合接口定义组合协议规范组合管理和状态支持交易系统功能支持相关功能






"""
组合统一接口定义

定义所有投资组合必须实现的统一接口，
支持单策略和多策略组合管理。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from ginkgo.core.interfaces.strategy_interface import IStrategy
from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.trading.sizers.base_sizer import BaseSizer
from ginkgo.trading.selectors.base_selector import BaseSelector
from ginkgo.trading.risk_managementss.base_risk import BaseRiskManagement


class PortfolioStatus(Enum):
    """组合状态枚举"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class RebalanceFrequency(Enum):
    """再平衡频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class IPortfolio(ABC):
    """投资组合统一接口"""
    
    def __init__(self, name: str = "UnknownPortfolio", initial_capital: float = 1000000.0):
        self.name = name
        self.initial_capital = initial_capital
        self.status = PortfolioStatus.INACTIVE
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 组合组件
        self._strategies = []
        self._analyzers = []
        self._sizers = []
        self._selectors = []
        self._risk_managementss = []
        
        # 组合配置
        self._rebalance_frequency = RebalanceFrequency.DAILY
        self._max_position_size = 0.1  # 单只股票最大仓位
        self._cash_reserve = 0.05  # 现金保留比例
        
        # 权重管理
        self._strategy_weights = {}
        self._auto_rebalance = True
        
        # 性能统计
        self._performance_metrics = {}
        self._positions = {}
        self._cash = initial_capital
        
    @property
    def strategies(self) -> List[IStrategy]:
        """策略列表"""
        return self._strategies
    
    @property
    def analyzers(self) -> List[BaseAnalyzer]:
        """分析器列表"""
        return self._analyzers
    
    @property
    def sizers(self) -> List[BaseSizer]:
        """仓位调整器列表"""
        return self._sizers
    
    @property
    def selectors(self) -> List[BaseSelector]:
        """选择器列表"""
        return self._selectors
    
    @property
    def risk_managementss(self) -> List[BaseRiskManagement]:
        """风险管理器列表"""
        return self._risk_managementss
    
    @property
    def current_cash(self) -> float:
        """当前现金"""
        return self._cash
    
    @property
    def positions(self) -> Dict[str, Dict[str, Any]]:
        """当前持仓"""
        return self._positions
    
    @property
    def total_value(self) -> float:
        """组合总价值"""
        return self._cash + sum(pos.get('market_value', 0) for pos in self._positions.values())
    
    @property
    def strategy_weights(self) -> Dict[str, float]:
        """策略权重"""
        return self._strategy_weights
    
    @abstractmethod
    def add_strategy(self, strategy: IStrategy, weight: float = 1.0) -> None:
        """
        添加策略
        
        Args:
            strategy: 策略实例
            weight: 策略权重
        """
        pass
    
    @abstractmethod
    def remove_strategy(self, strategy: Union[IStrategy, str]) -> bool:
        """
        移除策略
        
        Args:
            strategy: 策略实例或策略名称
            
        Returns:
            bool: 是否移除成功
        """
        pass
    
    def add_analyzer(self, analyzer: BaseAnalyzer) -> None:
        """添加分析器"""
        if analyzer not in self._analyzers:
            self._analyzers.append(analyzer)
            
    def add_sizer(self, sizer: BaseSizer) -> None:
        """添加仓位调整器"""
        if sizer not in self._sizers:
            self._sizers.append(sizer)
            
    def add_selector(self, selector: BaseSelector) -> None:
        """添加选择器"""
        if selector not in self._selectors:
            self._selectors.append(selector)
            
    def add_risk_managements(self, risk_mgmt: BaseRiskManagement) -> None:
        """添加风险管理器"""
        if risk_mgmt not in self._risk_managementss:
            self._risk_managementss.append(risk_mgmt)
    
    def set_strategy_weight(self, strategy_name: str, weight: float) -> None:
        """设置策略权重"""
        self._strategy_weights[strategy_name] = weight
        self._normalize_weights()
    
    def _normalize_weights(self) -> None:
        """归一化策略权重"""
        total_weight = sum(self._strategy_weights.values())
        if total_weight > 0:
            for strategy_name in self._strategy_weights:
                self._strategy_weights[strategy_name] /= total_weight
    
    def get_strategy_weight(self, strategy_name: str) -> float:
        """获取策略权重"""
        return self._strategy_weights.get(strategy_name, 0.0)
    
    def set_rebalance_frequency(self, frequency: RebalanceFrequency) -> None:
        """设置再平衡频率"""
        self._rebalance_frequency = frequency
    
    def set_position_limits(self, max_position_size: float, cash_reserve: float = None) -> None:
        """设置仓位限制"""
        self._max_position_size = max_position_size
        if cash_reserve is not None:
            self._cash_reserve = cash_reserve
    
    @abstractmethod
    def calculate_target_positions(self, signals: Dict[str, Any]) -> Dict[str, float]:
        """
        计算目标仓位
        
        Args:
            signals: 策略信号
            
        Returns:
            Dict[str, float]: 目标仓位字典 {code: weight}
        """
        pass
    
    @abstractmethod
    def rebalance(self, target_positions: Dict[str, float]) -> Dict[str, Any]:
        """
        执行再平衡
        
        Args:
            target_positions: 目标仓位
            
        Returns:
            Dict[str, Any]: 再平衡结果
        """
        pass
    
    def update_position(self, code: str, quantity: float, price: float) -> None:
        """更新持仓"""
        if code not in self._positions:
            self._positions[code] = {
                'quantity': 0,
                'avg_price': 0,
                'market_value': 0,
                'unrealized_pnl': 0
            }
        
        position = self._positions[code]
        
        # 更新持仓数量和平均价格
        old_quantity = position['quantity']
        old_avg_price = position['avg_price']
        
        new_quantity = old_quantity + quantity
        
        if new_quantity != 0:
            # 计算新的平均价格
            if quantity > 0:  # 买入
                total_cost = old_quantity * old_avg_price + quantity * price
                position['avg_price'] = total_cost / new_quantity
            # 卖出时平均价格不变
            
            position['quantity'] = new_quantity
            position['market_value'] = new_quantity * price
            position['unrealized_pnl'] = (price - position['avg_price']) * new_quantity
        else:
            # 持仓清零
            position['quantity'] = 0
            position['avg_price'] = 0
            position['market_value'] = 0
            position['unrealized_pnl'] = 0
        
        # 更新现金
        self._cash -= quantity * price
        self.updated_at = datetime.now()
    
    def get_position(self, code: str) -> Dict[str, Any]:
        """获取单只股票持仓"""
        return self._positions.get(code, {
            'quantity': 0,
            'avg_price': 0,
            'market_value': 0,
            'unrealized_pnl': 0
        })
    
    def get_position_weight(self, code: str) -> float:
        """获取持仓权重"""
        position = self.get_position(code)
        total_value = self.total_value
        if total_value > 0:
            return position.get('market_value', 0) / total_value
        return 0.0
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """计算性能指标"""
        total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in self._positions.values())
        total_return = total_pnl / self.initial_capital if self.initial_capital > 0 else 0
        
        self._performance_metrics = {
            'total_return': total_return,
            'total_pnl': total_pnl,
            'cash_ratio': self._cash / self.total_value if self.total_value > 0 else 1.0,
            'position_count': len([pos for pos in self._positions.values() if pos.get('quantity', 0) != 0])
        }
        
        return self._performance_metrics
    
    def validate_portfolio(self) -> List[str]:
        """验证组合配置"""
        errors = []
        
        if not self._strategies:
            errors.append("组合必须包含至少一个策略")
        
        if self.initial_capital <= 0:
            errors.append("初始资金必须大于0")
        
        if not (0 <= self._max_position_size <= 1):
            errors.append("最大仓位比例必须在0-1之间")
        
        if not (0 <= self._cash_reserve <= 1):
            errors.append("现金保留比例必须在0-1之间")
        
        # 检查策略权重
        total_weight = sum(self._strategy_weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            errors.append(f"策略权重总和应为1.0，当前为{total_weight:.6f}")
        
        return errors
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """获取组合概要"""
        return {
            'name': self.name,
            'status': self.status.value,
            'initial_capital': self.initial_capital,
            'current_value': self.total_value,
            'current_cash': self._cash,
            'strategy_count': len(self._strategies),
            'position_count': len([pos for pos in self._positions.values() if pos.get('quantity', 0) != 0]),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'performance_metrics': self._performance_metrics,
            'strategy_weights': self._strategy_weights.copy()
        }
    
    def activate(self) -> None:
        """激活组合"""
        errors = self.validate_portfolio()
        if errors:
            raise ValueError(f"组合验证失败: {'; '.join(errors)}")
        
        self.status = PortfolioStatus.ACTIVE
        self.updated_at = datetime.now()
    
    def suspend(self) -> None:
        """暂停组合"""
        self.status = PortfolioStatus.SUSPENDED
        self.updated_at = datetime.now()
    
    def close(self) -> None:
        """关闭组合"""
        self.status = PortfolioStatus.CLOSED
        self.updated_at = datetime.now()
    
    def reset(self) -> None:
        """重置组合状态"""
        self._positions = {}
        self._cash = self.initial_capital
        self._performance_metrics = {}
        self.status = PortfolioStatus.INACTIVE
        self.updated_at = datetime.now()
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, status={self.status.value}, strategies={len(self._strategies)})"
    
    def __repr__(self) -> str:
        return self.__str__()


class IMultiStrategyPortfolio(IPortfolio):
    """多策略组合接口"""
    
    def __init__(self, name: str = "MultiStrategyPortfolio", initial_capital: float = 1000000.0):
        super().__init__(name, initial_capital)
        self._strategy_allocations = {}  # 策略资金分配
        self._strategy_performance = {}  # 策略表现跟踪
    
    @property
    def strategy_allocations(self) -> Dict[str, float]:
        """策略资金分配"""
        return self._strategy_allocations
    
    @property
    def strategy_performance(self) -> Dict[str, Dict[str, float]]:
        """策略表现"""
        return self._strategy_performance
    
    @abstractmethod
    def allocate_capital(self, allocations: Dict[str, float]) -> None:
        """
        分配资金给各策略
        
        Args:
            allocations: 资金分配字典 {strategy_name: capital}
        """
        pass
    
    @abstractmethod
    def rebalance_strategies(self) -> None:
        """策略间再平衡"""
        pass
    
    def track_strategy_performance(self, strategy_name: str, metrics: Dict[str, float]) -> None:
        """跟踪策略表现"""
        if strategy_name not in self._strategy_performance:
            self._strategy_performance[strategy_name] = {}
        
        self._strategy_performance[strategy_name].update(metrics)
        self.updated_at = datetime.now()
    
    def get_strategy_performance(self, strategy_name: str) -> Dict[str, float]:
        """获取策略表现"""
        return self._strategy_performance.get(strategy_name, {})
    
    def get_best_performing_strategy(self) -> Optional[str]:
        """获取表现最佳的策略"""
        if not self._strategy_performance:
            return None
        
        best_strategy = None
        best_return = float('-inf')
        
        for strategy_name, metrics in self._strategy_performance.items():
            total_return = metrics.get('total_return', 0)
            if total_return > best_return:
                best_return = total_return
                best_strategy = strategy_name
        
        return best_strategy