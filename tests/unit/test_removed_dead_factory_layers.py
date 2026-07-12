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


# ---------- core.factories / core.adapters 死层已删(ADR-022 原则 6)----------

@pytest.mark.unit
def test_core_factories_module_removed():
    """core.factories(3 文件)已删:零外部类引用,仅 core/__init__.py try/except 残壳。"""
    assert importlib.util.find_spec("ginkgo.core.factories") is None


@pytest.mark.unit
def test_core_adapters_module_removed():
    """core.adapters(5 文件)已删:零外部类引用,仅 core/__init__.py try/except 残壳。"""
    assert importlib.util.find_spec("ginkgo.core.adapters") is None


@pytest.mark.unit
def test_core_factories_tests_removed():
    """core.factories 死层的测试随源码一并删除(测的对象已不存在)。

    与 test_component_factory_service_smoke_removed 对称:删源码时同步删测它的
    测试,防 import 已删模块致 pytest 收集崩。守目录不存在比 find_spec 更强——
    find_spec 守源码模块,目录存在性守测试文件残留(PEP420 命名空间包陷阱)。
    """
    from pathlib import Path

    tests_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "unit" / "core" / "factories"
    )
    assert not tests_dir.exists(), (
        "tests/unit/core/factories/ 应随 core.factories 源码一并删除"
    )


@pytest.mark.unit
def test_core_adapters_tests_removed():
    """core.adapters 死层的测试随源码一并删除(测的对象已不存在)。

    与 test_core_factories_tests_removed 同理;core.adapters 删源码后漏删测试
    曾致 pytest tests/unit/core/ 收集崩 4 个 ModuleNotFoundError(PR #6710 review)。
    """
    from pathlib import Path

    tests_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "unit" / "core" / "adapters"
    )
    assert not tests_dir.exists(), (
        "tests/unit/core/adapters/ 应随 core.adapters 源码一并删除"
    )


@pytest.mark.unit
def test_core_package_intact_after_factories_adapters_removal():
    """正向守卫:删 factories/adapters 后 core 包仍导出活跃服务。

    interfaces 保留(#6707 范围,本 PR 不动);factories/adapters 不再是 core 属性。
    """
    import ginkgo.core as core

    assert callable(core.get_config)
    assert callable(core.get_logger)
    # interfaces 保留给 #6707
    assert hasattr(core, "interfaces")
    # factories/adapters 已下架
    assert not hasattr(core, "factories")
    assert not hasattr(core, "adapters")


# ---------- ComponentLoader = 组件创建单一接缝(ADR-022 原则 3)----------

@pytest.mark.unit
def test_component_loader_is_single_component_creation_seam():
    """ComponentLoader.perform_component_binding 是组件创建的单一对外入口。

    ADR-022 原则 3:全仓唯一执行「DB 源码 → exec_module → 组件实例」的路径。
    删除 4 层死工厂(ComponentFactoryService/core.factories/core.adapters/
    AnalyzerRegistry)后,ComponentLoader 是唯一幸存的组件创建抽象。
    本测试锁住该正向事实——单例接缝存在且可调,防过度删除伤及真路径。
    """
    from ginkgo.trading.services._assembly.component_loader import ComponentLoader

    assert callable(ComponentLoader.perform_component_binding), (
        "ComponentLoader.perform_component_binding 必须存在且可调 —— "
        "它是组件创建的单一接缝(ADR-022 原则 3)"
    )


@pytest.mark.unit
def test_component_loader_documents_single_seam_contract():
    """文档契约:ComponentLoader 模块/类 docstring 必须记录 ADR-022 原则 3。

    #6476 的交付之一是「将 ComponentLoader 记录为单一接缝」。docstring 是该
    架构决策的载体;锁住它防未来 refactor 静默剥离架构边界说明,再次堆积工厂层。
    """
    import ginkgo.trading.services._assembly.component_loader as mod

    # 模块 docstring 记录单一接缝契约
    assert mod.__doc__ is not None, "ComponentLoader 模块必须有 docstring"
    doc = mod.__doc__
    assert "ADR-022" in doc, "模块 docstring 须引用 ADR-022(单一接缝契约)"
    assert "单一接缝" in doc or "唯一接缝" in doc, (
        "模块 docstring 须显式声明 ComponentLoader 为组件创建的单一/唯一接缝"
    )
