# Upstream: EngineAssemblyService, ComponentLoader, PortfolioBase
# Downstream: NoRiskManagement, BaseRiskManagement
# Role: 风险管理模块包，导出风控基类及无风控等风控管理器实现
#
# ===== 组件边界 =====
# 职责: 风控拦截（被动）和主动风控信号生成
# 双重机制:
#   - cal(order): 被动拦截，调整 order.volume 或标记 ORDERBLOCKED
#   - generate_signals(portfolio_info, event): 主动生成止损/平仓信号
# 输入: portfolio_info(dict), order 或 event
# 输出: 调整后的 order 或 List[Signal]
# 约束:
#   - 只能减少或拒绝订单量，不能增加
#   - 止损止盈逻辑属于 RiskManager 职责，不属于 Strategy






from ginkgo.trading.risk_management.no_risk import NoRiskManagement
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement

