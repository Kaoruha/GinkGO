# Upstream: 数据更新任务, BarService
# Downstream: GinkgoSourceBase
# Role: Yahoo Finance数据源适配器，提供全球市场数据获取(桩实现)






from ginkgo.data.sources.source_base import GinkgoSourceBase


class GinkgoYahoo(GinkgoSourceBase):
    def connect(self, *args, **kwargs):
        raise NotImplementedError("GinkgoYahoo 尚未实现")

    def fetch_cn_stock_trade_day(self, *args, **kwargs):
        raise NotImplementedError("GinkgoYahoo 尚未实现")

    def fetch_cn_stock_list(self, date: any, *args, **kwargs):
        raise NotImplementedError("GinkgoYahoo 尚未实现")

    def fetch_cn_stock_daybar(self, *args, **kwargs):
        raise NotImplementedError("GinkgoYahoo 尚未实现")

    def fetch_cn_stock_adjustfactor(self, *args, **kwargs):
        raise NotImplementedError("GinkgoYahoo 尚未实现")

    def fetch_cn_stockinfo(self, *args, **kwargs):
        raise NotImplementedError("GinkgoYahoo 尚未实现")

