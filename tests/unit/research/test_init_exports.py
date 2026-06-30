# #6121: research/__init__.py 导出完整性
# 锁定不变量：__all__ 宣传的每个名字都必须能真实导入（禁止幽灵导出）。
import importlib

import pytest


# #6121: 被移除的换手率分析导出 —— turnover_analysis.py 从未存在，导出是死引用。
REMOVED_DEAD_EXPORT = "FactorTurnoverAnalyzer"
# 回归守护：以下 analyzer 模块真实存在，导出必须保留。
EXPECTED_LIVE_EXPORTS = [
    "ICAnalyzer",
    "FactorLayering",
    "FactorOrthogonalizer",
    "FactorComparator",
    "FactorDecayAnalyzer",
    "ResearchContainer",
]


@pytest.fixture(scope="module")
def research_module():
    return importlib.import_module("ginkgo.research")


class TestResearchPublicSurface:
    """__all__ 必须诚实：宣传的每个名字都能导入。"""

    def test_all_entries_are_importable(self, research_module):
        # from ginkgo.research import * 的等价检查：遍历 __all__ 逐个 getattr。
        # 幽灵导出（指向不存在的模块）会在此暴露为 ModuleNotFoundError。
        unimportable = []
        for name in research_module.__all__:
            try:
                getattr(research_module, name)
            except Exception as exc:  # noqa: BLE001 - 任何异常都算导出不可用
                unimportable.append(f"{name}: {type(exc).__name__}: {exc}")
        assert not unimportable, "__all__ 含不可导入的幽灵导出:\n" + "\n".join(unimportable)

    def test_dead_turnover_export_removed_from_all(self, research_module):
        # 换手率分析无实现模块，从公共导出面移除，避免误导用户。
        assert REMOVED_DEAD_EXPORT not in research_module.__all__

    def test_dead_turnover_export_not_lazy_importable(self, research_module):
        # 移除后访问应得到标准 AttributeError（无此属性），而非指向幽灵模块的 ModuleNotFoundError。
        with pytest.raises(AttributeError):
            getattr(research_module, REMOVED_DEAD_EXPORT)

    @pytest.mark.parametrize("name", EXPECTED_LIVE_EXPORTS)
    def test_live_analyzer_exports_intact(self, research_module, name):
        # 回归守护：真实存在的 analyzer 导出不受影响。
        assert name in research_module.__all__
        obj = getattr(research_module, name)
        assert obj is not None
