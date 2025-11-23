"""
投资组合和风险管理事件

实现T5架构中定义的投资组合相关事件：
- EventPortfolioUpdate: 投资组合更新事件
- EventRiskBreach: 风险违规事件

这些事件用于投资组合管理和风险控制系统。
"""

import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass

from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES


@dataclass
class PortfolioSnapshot:
    """投资组合快照数据类"""
    
    # 资产信息
    total_asset: Decimal                    # 总资产
    available_cash: Decimal                 # 可用现金
    market_value: Decimal                   # 市值
    frozen_cash: Decimal                    # 冻结资金
    
    # 持仓信息
    positions: Dict[str, Dict[str, Any]]    # 持仓详情 {code: position_info}
    position_count: int                     # 持仓数量
    
    # 盈亏信息
    total_pnl: Decimal                      # 总盈亏
    realized_pnl: Decimal                   # 已实现盈亏
    unrealized_pnl: Decimal                 # 未实现盈亏
    
    # 风险指标
    risk_metrics: Dict[str, float]          # 风险指标
    
    # 时间戳
    snapshot_time: datetime.datetime
    
    @property
    def net_asset(self) -> Decimal:
        """净资产"""
        return self.total_asset
    
    @property
    def position_ratio(self) -> float:
        """仓位比例"""
        if self.total_asset == 0:
            return 0.0
        return float(self.market_value / self.total_asset)
    
    @property
    def cash_ratio(self) -> float:
        """现金比例"""
        if self.total_asset == 0:
            return 1.0
        return float(self.available_cash / self.total_asset)


class EventPortfolioUpdate(EventBase):
    """
    投资组合更新事件
    
    当投资组合发生变化时触发，包含完整的投资组合快照。
    用于实时监控投资组合状态和风险指标。
    """
    
    def __init__(self,
                 portfolio_snapshot: PortfolioSnapshot,
                 timestamp: Optional[datetime.datetime] = None,
                 update_reason: str = "Position changed",
                 changed_positions: Optional[List[str]] = None,
                 *args, **kwargs):
        super().__init__(name="PortfolioUpdate", *args, **kwargs)
        self.set_type(EVENT_TYPES.PORTFOLIOUPDATE)
        
        self._portfolio_snapshot = portfolio_snapshot
        self._update_reason = update_reason
        self._changed_positions = changed_positions or []
        
        if timestamp:
            self.set_time(timestamp)
        else:
            self.set_time(portfolio_snapshot.snapshot_time)
    
    @property
    def portfolio_snapshot(self) -> PortfolioSnapshot:
        """获取投资组合快照"""
        return self._portfolio_snapshot
    
    @property
    def update_reason(self) -> str:
        """获取更新原因"""
        return self._update_reason
    
    @property
    def changed_positions(self) -> List[str]:
        """获取发生变化的持仓代码列表"""
        return self._changed_positions
    
    @property
    def total_asset(self) -> Decimal:
        """获取总资产"""
        return self._portfolio_snapshot.total_asset
    
    @property
    def market_value(self) -> Decimal:
        """获取市值"""
        return self._portfolio_snapshot.market_value
    
    @property
    def available_cash(self) -> Decimal:
        """获取可用现金"""
        return self._portfolio_snapshot.available_cash
    
    @property
    def total_pnl(self) -> Decimal:
        """获取总盈亏"""
        return self._portfolio_snapshot.total_pnl
    
    @property
    def position_count(self) -> int:
        """获取持仓数量"""
        return self._portfolio_snapshot.position_count
    
    def get_position_info(self, code: str) -> Optional[Dict[str, Any]]:
        """获取指定股票的持仓信息"""
        return self._portfolio_snapshot.positions.get(code)
    
    def __repr__(self):
        return (f"EventPortfolioUpdate(total_asset={self.total_asset}, "
                f"positions={self.position_count}, reason='{self._update_reason}')")


@dataclass
class RiskBreachDetails:
    """风险违规详情"""
    
    risk_type: str                          # 风险类型
    risk_level: str                         # 风险级别 (WARNING, ERROR, CRITICAL)
    threshold_value: float                  # 阈值
    current_value: float                    # 当前值
    breach_magnitude: float                 # 违规幅度 (current - threshold)
    affected_positions: List[str]           # 受影响的持仓
    breach_time: datetime.datetime          # 违规时间
    
    # 相关数据
    context_data: Dict[str, Any]            # 上下文数据
    
    @property
    def breach_ratio(self) -> float:
        """违规比率"""
        if self.threshold_value == 0:
            return float('inf')
        return self.breach_magnitude / self.threshold_value
    
    @property
    def severity_score(self) -> float:
        """严重程度评分 (0-100)"""
        base_score = {
            'WARNING': 30,
            'ERROR': 60, 
            'CRITICAL': 90
        }.get(self.risk_level, 50)
        
        # 根据违规比率调整评分
        ratio_factor = min(abs(self.breach_ratio) * 10, 10)
        return min(base_score + ratio_factor, 100)


class EventRiskBreach(EventBase):
    """
    风险违规事件
    
    当投资组合触发风险控制规则时产生，包含详细的违规信息。
    """
    
    def __init__(self,
                 risk_type: str,
                 breach_details: RiskBreachDetails,
                 timestamp: Optional[datetime.datetime] = None,
                 auto_action_taken: bool = False,
                 action_description: str = "",
                 *args, **kwargs):
        super().__init__(name="RiskBreach", *args, **kwargs)
        self.set_type(EVENT_TYPES.RISKBREACH)
        
        self._risk_type = risk_type
        self._breach_details = breach_details
        self._auto_action_taken = auto_action_taken
        self._action_description = action_description
        
        if timestamp:
            self.set_time(timestamp)
        else:
            self.set_time(breach_details.breach_time)
    
    @property
    def risk_type(self) -> str:
        """获取风险类型"""
        return self._risk_type
    
    @property
    def breach_details(self) -> RiskBreachDetails:
        """获取违规详情"""
        return self._breach_details
    
    @property
    def risk_level(self) -> str:
        """获取风险级别"""
        return self._breach_details.risk_level
    
    @property
    def current_value(self) -> float:
        """获取当前值"""
        return self._breach_details.current_value
    
    @property
    def threshold_value(self) -> float:
        """获取阈值"""
        return self._breach_details.threshold_value
    
    @property
    def breach_magnitude(self) -> float:
        """获取违规幅度"""
        return self._breach_details.breach_magnitude
    
    @property
    def affected_positions(self) -> List[str]:
        """获取受影响的持仓"""
        return self._breach_details.affected_positions
    
    @property
    def auto_action_taken(self) -> bool:
        """是否已自动采取行动"""
        return self._auto_action_taken
    
    @property
    def action_description(self) -> str:
        """获取行动描述"""
        return self._action_description
    
    @property
    def severity_score(self) -> float:
        """获取严重程度评分"""
        return self._breach_details.severity_score
    
    def is_critical(self) -> bool:
        """是否为关键风险"""
        return self._breach_details.risk_level == "CRITICAL"
    
    def requires_immediate_action(self) -> bool:
        """是否需要立即行动"""
        return self.is_critical() or self.severity_score > 80
    
    def __repr__(self):
        return (f"EventRiskBreach(type={self._risk_type}, level={self.risk_level}, "
                f"current={self.current_value}, threshold={self.threshold_value})")