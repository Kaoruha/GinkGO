"""ADR-022 原则 1 · 死 Protocol 删除回归守卫

验证 #6713 删除的四项死 Protocol 接口确实消失；#6864 进一步删除最后一个存活的
PortfolioInfo（零消费方，analyzer 收 plain Dict，存活仅由本测试强制）。
通过公共导入接口断言（模块是否存在 / 包是否导出），不耦合内部实现。
"""
import importlib
import pytest


@pytest.mark.parametrize(
    "module",
    [
        "ginkgo.trading.interfaces.protocols.engine",
        "ginkgo.trading.interfaces.protocols.portfolio",
        "ginkgo.trading.interfaces.protocols.risk_management",
        "ginkgo.trading.interfaces.protocols.strategy",
        "ginkgo.trading.interfaces.protocols.portfolio_info",
    ],
)
def test_dead_protocol_module_removed(module):
    """五项死 Protocol 模块应已删除（零消费方；portfolio_info 曾由测试强制存活，#6864 订正）。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_protocols_pkg_exports_nothing():
    """protocols 包入口收窄后不再导出任何 Protocol 符号（含 PortfolioInfo）。"""
    import ginkgo.trading.interfaces.protocols as proto
    assert proto.__all__ == []
    for name in ("IEngine", "IPortfolio", "IRiskManagement", "IStrategy", "PortfolioInfo"):
        assert not hasattr(proto, name), f"{name} 应已从 protocols 包移除（ADR-022 原则 1）"


def test_interfaces_pkg_exports_nothing():
    """trading.interfaces 包入口收窄后不再导出任何 Protocol 符号。"""
    import ginkgo.trading.interfaces as iface
    assert iface.__all__ == []
