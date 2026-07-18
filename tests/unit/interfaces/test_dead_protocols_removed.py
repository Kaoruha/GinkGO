"""ADR-022 原则 1 · 死 Protocol 删除回归守卫

验证 #6713 删除的四项死 Protocol 接口确实消失，且保留的 PortfolioInfo 不受影响。
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
    ],
)
def test_dead_protocol_module_removed(module):
    """四个死 Protocol 模块（0 真实现/继承，仅 docstring 示例引用）应已删除。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_protocols_pkg_only_exports_portfolio_info():
    """protocols 包入口收窄后应仅导出 PortfolioInfo，I* Protocol 符号不再泄漏。"""
    import ginkgo.trading.interfaces.protocols as proto
    assert "PortfolioInfo" in proto.__all__
    for name in ("IEngine", "IPortfolio", "IRiskManagement", "IStrategy"):
        assert not hasattr(proto, name), f"{name} 应已从 protocols 包移除（ADR-022 原则 1）"
        assert name not in proto.__all__


def test_interfaces_pkg_only_exports_portfolio_info():
    """trading.interfaces 包入口收窄后应仅导出 PortfolioInfo。"""
    import ginkgo.trading.interfaces as iface
    assert iface.__all__ == ["PortfolioInfo"]


def test_portfolio_info_protocol_intact():
    """保留的运行时可检查协议 PortfolioInfo 应仍可导入——删的是死接口，非活协议。"""
    from ginkgo.trading.interfaces.protocols.portfolio_info import PortfolioInfo
    assert PortfolioInfo is not None
