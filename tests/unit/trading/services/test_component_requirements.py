"""#6640: 必需组件清单 + 缺失检测辅助函数的直接单测。

覆盖创建预检/装配透传间接路径未触达的边界（int 类型输入、未知字符串忽略、
空 components、清单顺序）。
"""
import pytest

from ginkgo.enums import FILE_TYPES
from ginkgo.trading.services._assembly.requirements import (
    REQUIRED_PORTFOLIO_COMPONENT_TYPES,
    find_missing_required_components,
    find_missing_required_from_bucketed,
    format_missing_components_message,
)


class TestFindMissingRequiredComponents:
    """find_missing_required_components: 从类型集合判缺失。"""

    @pytest.mark.unit
    def test_all_present_returns_empty(self):
        """strategy+selector+sizer 齐全 → 无缺失。"""
        result = find_missing_required_components(
            {FILE_TYPES.STRATEGY, FILE_TYPES.SELECTOR, FILE_TYPES.SIZER}
        )
        assert result == []

    @pytest.mark.unit
    def test_string_member_names_accepted(self):
        """字符串成员名（PortfolioService.get_components 返回格式）→ 正确识别。"""
        result = find_missing_required_components(["STRATEGY", "SELECTOR"])
        # 仅缺 SIZER
        assert len(result) == 1
        assert result[0][0] == "Sizer"

    @pytest.mark.unit
    def test_int_values_accepted(self):
        """int value（FILE_TYPES.SIZER.value=5）→ 正确识别。"""
        result = find_missing_required_components([6, 4])  # strategy + selector
        assert ("Sizer", "sizer") in result

    @pytest.mark.unit
    def test_unknown_strings_ignored(self):
        """未知字符串（非必需类型的合法组件，如 analyzer）→ 忽略，不报错。"""
        result = find_missing_required_components(
            ["STRATEGY", "SELECTOR", "SIZER", "ANALYZER", "UNKNOWN_TYPE"]
        )
        assert result == []

    @pytest.mark.unit
    def test_order_follows_required_list(self):
        """缺失项顺序与 REQUIRED_PORTFOLIO_COMPONENT_TYPES 一致（strategy→selector→sizer）。"""
        result = find_missing_required_components([])  # 全缺
        labels = [label for label, _ in result]
        assert labels == ["Strategy", "Selector", "Sizer"]


class TestFindMissingFromBucketed:
    """find_missing_required_from_bucketed: 从分桶 dict 判缺失（装配层用）。"""

    @pytest.mark.unit
    def test_empty_dict_all_missing(self):
        assert len(find_missing_required_from_bucketed({})) == 3

    @pytest.mark.unit
    def test_none_components_all_missing(self):
        assert len(find_missing_required_from_bucketed(None)) == 3

    @pytest.mark.unit
    def test_empty_list_treated_as_missing(self):
        """空 list 视为未绑定（与 component_loader 的 len()==0 检查一致）。"""
        result = find_missing_required_from_bucketed(
            {"strategies": [{"file_id": "x"}], "selectors": [], "sizers": []}
        )
        labels = [l for l, _ in result]
        assert "Selector" in labels
        assert "Sizer" in labels
        assert "Strategy" not in labels

    @pytest.mark.unit
    def test_all_buckets_filled_no_missing(self):
        result = find_missing_required_from_bucketed(
            {"strategies": [1], "selectors": [1], "sizers": [1]}
        )
        assert result == []


class TestFormatMissingComponentsMessage:
    """format_missing_components_message: 错误信息格式。"""

    @pytest.mark.unit
    def test_empty_missing_returns_empty_string(self):
        assert format_missing_components_message("pid", []) == ""

    @pytest.mark.unit
    def test_single_component_message(self):
        msg = format_missing_components_message("abc123", [("Sizer", "sizer")])
        assert "abc123" in msg
        assert "Sizer" in msg
        assert "bind-component" in msg
        assert "--type sizer" in msg

    @pytest.mark.unit
    def test_multiple_components_joined(self):
        msg = format_missing_components_message(
            "pid", [("Strategy", "strategy"), ("Sizer", "sizer")]
        )
        assert "Strategy" in msg
        assert "Sizer" in msg
        assert "--type strategy" in msg
        assert "--type sizer" in msg


class TestRequiredListDefinition:
    """清单本身的不变量：单点维护的权威来源。"""

    @pytest.mark.unit
    def test_required_list_covers_core_three(self):
        """清单覆盖装配层 component_loader 实际要求的三个必需组件。"""
        types = {ft for ft, _, _ in REQUIRED_PORTFOLIO_COMPONENT_TYPES}
        assert FILE_TYPES.STRATEGY in types
        assert FILE_TYPES.SELECTOR in types
        assert FILE_TYPES.SIZER in types
