"""ADR-022 原则 2 · 死抽象删除回归守卫

验证 #6293 删除的两项死抽象确实消失，且活符号不受影响。
通过公共导入接口断言（模块是否存在 / 包是否导出），不耦合内部实现。
"""
import importlib
import pytest


def test_engine_interface_module_removed():
    """core/interfaces/engine_interface.py（4 死引擎类 + EngineMode，0 生产消费者）应已删除。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.core.interfaces.engine_interface")


def test_core_interfaces_no_longer_exports_base_engine():
    """core.interfaces 包入口不应再导出已删的 BaseEngine（ADR-022 原则 2）。"""
    import ginkgo.core.interfaces as ci
    assert not hasattr(ci, "BaseEngine")
    assert "BaseEngine" not in ci.__all__


def test_backtest_base_module_removed():
    """trading/core/backtest_base.py 的 BacktestBase 空壳应已删除（0 真继承者，职责全移 Mixin）。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.trading.core.backtest_base")


def test_backtest_base_not_exported():
    """trading 包入口不应再导出已删的 BacktestBase。"""
    import ginkgo.trading as t
    import ginkgo.trading.core as tc
    assert not hasattr(t, "BacktestBase")
    assert not hasattr(tc, "BacktestBase")


def test_live_engine_base_intact():
    """真实引擎基类（trading/engines/base_engine.py）应仍可导入——删的是死接口层，非活引擎基类。"""
    from ginkgo.trading.engines.base_engine import BaseEngine
    assert BaseEngine is not None


def test_core_interfaces_live_exports_intact():
    """core.interfaces 的 3 个活接口（BaseStrategy/BaseModel/BasePortfolio）应仍可导入，未被连带删除。"""
    import ginkgo.core.interfaces as ci
    for name in ("BaseStrategy", "BaseModel", "BasePortfolio"):
        assert hasattr(ci, name), f"{name} 应仍导出（ADR-022 仅删死抽象，活接口保留）"
