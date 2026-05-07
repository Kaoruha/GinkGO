# Upstream: EngineAssemblyService, ComponentLoader, PortfolioBase
# Downstream: BaseSizer, FixedSizer, ATRSizer
# Role: 仓位管理模块包，导出Sizer基类及固定/ATR等仓位管理器实现
#
# ===== 组件边界 =====
# 职责: 确定开仓手数
# 输入: portfolio_info(dict), signal/order
# 输出: volume（整数手数）
# 允许:
#   - 获取行情数据计算技术指标（如 ATR），作为 sizing 算法的输入
#   - 基类提供 _data_feeder 槽位用于数据访问
# 禁止:
#   - 风控校验（由 RiskManager 负责）






from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.sizers.atr_sizer import ATRSizer

