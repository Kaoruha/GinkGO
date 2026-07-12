"""回归守卫:组件创建死层删除(#6476,ADR-022 原则 3+6)。

#6476 经 grep + 运行时实测确认以下为死层/潜伏死代码并已删除。本测试锁定该删除——
防止 careless revert / merge 静默重新引入这些无人调用的抽象,再次堆积成死代码。

被删项(详见 issue #6476):
- AnalyzerRegistry(ginkgo.trading.analysis.analyzers.registry,195L):潜伏死代码。
  import 即崩(`ANALYZER_CATEGORY_TYPES` 全仓零定义,非路径漂移);backtest.py
  `list_analyzers` 端点的 import 被 `except Exception` 静默吞,端点运行时永远走
  `_FALLBACK_ANALYZERS`。删后端点直接返回内置目录,行为不变。
- ComponentFactoryService(ginkgo.trading.services.component_factory_service,213L):
  零实例化、零方法调用,仅 services/__init__.py 的 import/export 壳。
- core.factories(3 文件):零外部类引用,仅 core/__init__.py try/except 残壳。
- core.adapters(5 文件):零外部类引用,仅 core/__init__.py try/except 残壳。

ADR-022 原则 3:ComponentLoader.perform_component_binding 是组件创建的单一接缝。
ADR-022 原则 6:core/ 层级下架(factories/adapters 残留抽象)。

正向守卫:ComponentLoader(单一活跃接缝)+ analyzers 包内置分析器必须仍在——
锁住防过度删除。
"""
import importlib.util

import pytest


# ---------- AnalyzerRegistry 潜伏死代码已删 ----------

@pytest.mark.unit
def test_analyzer_registry_module_removed():
    """AnalyzerRegistry 潜伏死代码已删:find_spec 应返回 None。

    删除前 import 即崩(ANALYZER_CATEGORY_TYPES 全仓零定义),backtest.py 的引用
    被 except 吞,端点永远走回退列表。删后无行为变化。
    """
    assert importlib.util.find_spec(
        "ginkgo.trading.analysis.analyzers.registry"
    ) is None


@pytest.mark.unit
def test_analyzers_package_intact_after_registry_removal():
    """正向守卫:删 registry 后 analyzers 包仍正常导出内置分析器(防过度删除)。"""
    from ginkgo.trading.analysis.analyzers import (
        BaseAnalyzer,
        SharpeRatio,
        MaxDrawdown,
    )

    assert BaseAnalyzer is not None
    assert SharpeRatio is not None
    assert MaxDrawdown is not None


# ---------- list_analyzers 端点不再引用已删 registry ----------

@pytest.mark.unit
def test_list_analyzers_no_longer_imports_registry():
    """backtest.py 清理死 try 块后,不再 import/实例化 AnalyzerRegistry。

    删 registry 前端点的 import 被 except 吞(运行时永远走回退);清理后回退列表
    提为唯一实现,不应再残留真实 import 或实例化(注释里解释历史是允许的)。
    """
    from pathlib import Path

    backtest_api = Path(__file__).resolve().parents[2] / "api" / "api" / "backtest.py"
    source = backtest_api.read_text(encoding="utf-8")
    # 禁止真实 import 语句 + 实例化(注释提及历史名字不在此列)
    assert "from ginkgo.trading.analysis.analyzers.registry" not in source, (
        "backtest.py 仍 import 已删的 registry 模块 —— 应清理死 try 块"
    )
    assert "AnalyzerRegistry()" not in source, (
        "backtest.py 仍实例化已删的 AnalyzerRegistry —— 应清理死 try 块"
    )


# ---------- ComponentFactoryService 死层已删 ----------

@pytest.mark.unit
def test_component_factory_service_module_removed():
    """ComponentFactoryService(213L)已删:业务代码零实例化零调用。

    唯一使用方是 test_component_factory_service_smoke.py(纯 MagicMock 合成
    可调用性测试,无真实业务断言),随 CFS 一并删除。
    """
    assert importlib.util.find_spec(
        "ginkgo.trading.services.component_factory_service"
    ) is None


@pytest.mark.unit
def test_component_factory_service_smoke_removed():
    """测死代码的合成 smoke 随 CFS 一并删除(测的对象已不存在)。"""
    from pathlib import Path

    smoke = (
        Path(__file__).resolve().parents[2]
        / "tests" / "unit" / "services" / "smoke"
        / "test_component_factory_service_smoke.py"
    )
    assert not smoke.exists()


@pytest.mark.unit
def test_services_package_intact_after_factory_removal():
    """正向守卫:删 CFS 后 services 包仍导出活跃服务(防过度删除)。"""
    from ginkgo.trading.services import (
        EngineAssemblyService,
        PortfolioManagementService,
    )

    assert EngineAssemblyService is not None
    assert PortfolioManagementService is not None
