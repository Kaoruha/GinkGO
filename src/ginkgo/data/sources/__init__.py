# Upstream: 数据更新CLI(ginkgo data update), 数据同步服务
# Downstream: GinkgoTushare, GinkgoAkShare, GinkgoBaoStock, GinkgoTDX, GinkgoYahoo
# Role: 数据源包入口，统一导出所有外部数据源适配器(Tushare/AKShare/BaoStock/TDX/Yahoo)






from ginkgo.data.sources.ginkgo_akshare import GinkgoAkShare
from ginkgo.data.sources.ginkgo_baostock import GinkgoBaoStock
from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX
from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
from ginkgo.data.sources.ginkgo_yahoo import GinkgoYahoo

__all__ = ["GinkgoAkShare", "GinkgoBaoStock", "GinkgoTDX", "GinkgoTushare", "GinkgoYahoo"]
