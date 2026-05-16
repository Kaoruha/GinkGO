# Upstream: 数据更新CLI(ginkgo data update), 数据同步服务
# Downstream: GinkgoTushare, GinkgoAkShare, GinkgoBaoStock, GinkgoTDX, GinkgoYahoo
# Role: 数据源包入口，统一导出所有外部数据源适配器(Tushare/AKShare/BaoStock/TDX/Yahoo)

# See #2715: PEP 562 懒加载（models/ 包除外，见该目录注释）
_LAZY_IMPORTS = {
    "GinkgoAkShare": ("ginkgo.data.sources.ginkgo_akshare", "GinkgoAkShare"),
    "GinkgoBaoStock": ("ginkgo.data.sources.ginkgo_baostock", "GinkgoBaoStock"),
    "GinkgoTDX": ("ginkgo.data.sources.ginkgo_tdx", "GinkgoTDX"),
    "GinkgoTushare": ("ginkgo.data.sources.ginkgo_tushare", "GinkgoTushare"),
    "GinkgoYahoo": ("ginkgo.data.sources.ginkgo_yahoo", "GinkgoYahoo"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(_LAZY_IMPORTS.keys() | set(globals().keys()))


__all__ = ["GinkgoAkShare", "GinkgoBaoStock", "GinkgoTDX", "GinkgoTushare", "GinkgoYahoo"]
