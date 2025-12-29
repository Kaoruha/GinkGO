# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: 数据源模块导出Tushare/AKShare/TDX/Yahoo/BaoStock等数据源封装外部数据获取






from ginkgo.data.sources.ginkgo_akshare import GinkgoAkShare
from ginkgo.data.sources.ginkgo_baostock import GinkgoBaoStock
from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX
from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
from ginkgo.data.sources.ginkgo_yahoo import GinkgoYahoo

__all__ = ["GinkgoAkShare", "GinkgoBaoStock", "GinkgoTDX", "GinkgoTushare", "GinkgoYahoo"]
