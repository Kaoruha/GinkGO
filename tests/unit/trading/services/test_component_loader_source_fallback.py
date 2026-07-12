# Issue #5880 缺陷4a: component_loader source_import_map 类型映射错位
# Upstream: ginkgo.trading.services._assembly.component_loader.SOURCE_FALLBACK_IMPORT_MAP
# Downstream: _instantiate_component_from_file 的源码回退分支
# Role: 动态加载失败时，按组件类型从正确的源码包回退导入。
#       原 bug: key 7(=ENGINE) 映射到 risk_managements，而 RISKMANAGER=3 缺失，
#       导致 risk 组件 fallback 错导入 engine 包路径、risk 类型无回退。

from ginkgo.trading.services._assembly.component_loader import (
    SOURCE_FALLBACK_IMPORT_MAP,
)
from ginkgo.enums import FILE_TYPES


class TestSourceFallbackImportMap:
    """缺陷4a: 源码回退类型映射正确性"""

    def test_riskmanager_fallback_maps_to_risk_management_package(self):
        """RISKMANAGER(=3) 源码回退应从 ginkgo.trading.risk_management 导入（单数）"""
        assert FILE_TYPES.RISKMANAGER.value in SOURCE_FALLBACK_IMPORT_MAP
        assert SOURCE_FALLBACK_IMPORT_MAP[FILE_TYPES.RISKMANAGER.value] == (
            "ginkgo.trading.risk_management",
            "risk_management",
        )

    def test_risk_fallback_module_path_importable(self):
        """risk 回退 module_path 必须指向真实可 import 的模块（防复数路径 bug 复发，#6476）"""
        import importlib
        module_path, _ = SOURCE_FALLBACK_IMPORT_MAP[FILE_TYPES.RISKMANAGER.value]
        importlib.import_module(module_path)

    def test_engine_not_misassigned_to_risk_managements(self):
        """ENGINE(=7) 不应映射到 risk_managements（原 bug: key 7 错指 risk）"""
        # engine 是内置回测/实盘引擎，非用户上传 .py 组件，不应有源码回退条目
        assert FILE_TYPES.ENGINE.value not in SOURCE_FALLBACK_IMPORT_MAP

    def test_strategy_selector_sizer_analyzer_mappings_intact(self):
        """其余类型映射保持不变（回归保护）"""
        assert SOURCE_FALLBACK_IMPORT_MAP[FILE_TYPES.STRATEGY.value] == (
            "ginkgo.trading.strategies",
            "strategies",
        )
        assert SOURCE_FALLBACK_IMPORT_MAP[FILE_TYPES.SELECTOR.value] == (
            "ginkgo.trading.selectors",
            "selectors",
        )
        assert SOURCE_FALLBACK_IMPORT_MAP[FILE_TYPES.SIZER.value] == (
            "ginkgo.trading.sizers",
            "sizers",
        )
        assert SOURCE_FALLBACK_IMPORT_MAP[FILE_TYPES.ANALYZER.value] == (
            "ginkgo.trading.analysis.analyzers",
            "analyzers",
        )
