"""ADR-022 原则 2/6 · 死抽象删除 + core/interfaces 整层下架回归守卫

验证已删的死抽象确实消失：
- #6293 删除的引擎死接口层 + BacktestBase 空壳（原则 2）
- #6712 整层下架的 core/interfaces 包 + 同名双胞胎收敛（原则 6）

通过公共导入接口断言（模块是否存在 / 包是否导出），不耦合内部实现。
"""
import importlib
import pytest


# ──────────────────────────────────────────────────────────────────────
# #6293 · 死引擎接口层 + BacktestBase 空壳（ADR-022 原则 2，保留守卫）
# ──────────────────────────────────────────────────────────────────────

def test_engine_interface_module_removed():
    """core/interfaces/engine_interface.py（4 死引擎类 + EngineMode，0 生产消费者）应已删除。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.core.interfaces.engine_interface")


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


# ──────────────────────────────────────────────────────────────────────
# #6712 · core/interfaces 整层下架（ADR-022 原则 6 · 命名空间唯一性）
# ──────────────────────────────────────────────────────────────────────

def test_core_interfaces_package_removed():
    """core/interfaces 整层下架：包入口不可导入（死抽象真死透，0 生产引用）。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.core.interfaces")


def test_core_interfaces_strategy_module_removed():
    """core/interfaces/strategy_interface.py（BaseStrategy core 版 + BaseMLStrategy，0 生产继承）应已删除。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.core.interfaces.strategy_interface")


def test_core_interfaces_portfolio_module_removed():
    """core/interfaces/portfolio_interface.py（BasePortfolio core 版 + BaseMultiStrategyPortfolio，0 生产继承）应已删除。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.core.interfaces.portfolio_interface")


def test_core_interfaces_model_module_removed():
    """core/interfaces/model_interface.py（BaseModel 已迁 quant_ml/models/base_model.py；死子类已删）应已删除。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ginkgo.core.interfaces.model_interface")


def test_core_init_no_interfaces_attr():
    """core.__init__ 不应再残留 interfaces 容错入口（try/except + __all__ 已清）。"""
    import ginkgo.core as c
    assert not hasattr(c, "interfaces")
    assert "interfaces" not in getattr(c, "__all__", [])


# ──────────────────────────────────────────────────────────────────────
# #6712 · 活符号迁移后仍在位（防连带删除）
# ──────────────────────────────────────────────────────────────────────

def test_base_model_migrated_to_quant_ml():
    """BaseModel 应已迁至 quant_ml/models/base_model.py 且可导入（5 处生产 import 全在 quant_ml 域）。"""
    from ginkgo.quant_ml.models.base_model import BaseModel, ModelStatus
    assert BaseModel is not None
    assert ModelStatus is not None


def test_ml_strategy_base_unified_in_trading():
    """ML 策略三变体应统一为 trading/strategies/ml_strategy_base.py 的 MLStrategyBase。"""
    from ginkgo.trading.strategies.ml_strategy_base import MLStrategyBase
    assert MLStrategyBase is not None
