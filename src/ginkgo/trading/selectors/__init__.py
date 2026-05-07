# Upstream: EngineAssemblyService, ComponentLoader, PortfolioBase
# Downstream: BaseSelector, FixedSelector, PopularitySelector, CNAllSelector, MomentumSelector
# Role: 选股器模块包，导出选股器基类及固定/动量/热度/全A股等选股器实现
#
# ===== 组件边界 =====
# 职责: 选出目标股票列表
# 输入: 无或市场数据
# 输出: List[str] 股票代码
# 禁止:
#   - 生成交易信号（由 Strategy 负责）
#   - 计算开仓手数（由 Sizer 负责）
#   - 风控判断（由 RiskManager 负责）






from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.selectors.popularity_selector import PopularitySelector
from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
from ginkgo.trading.selectors.momentum_selector import MomentumSelector

