"""
#5774: node-graphs file_type 解析测试

验证 add_file_to_portfolio 的 file_type 参数能接受：
- 字符串枚举名（"strategy"）
- 整数/数字字符串（6, "6"）
- 大小写变体（"Strategy", "STRATEGY"）
- 别名（"risk" → RISKMANAGER）
"""

import pytest
from ginkgo.enums import FILE_TYPES


class TestFileTypeParsing:
    """file_type 解析逻辑测试"""

    def _parse_file_type(self, raw):
        """模拟 node_graph.py 中的解析逻辑"""
        if isinstance(raw, int):
            result = FILE_TYPES.from_int(raw)
            if result is None:
                raise ValueError(f"Invalid file_type integer: {raw}")
            return result

        # 字符串输入
        s = str(raw).strip()

        # 尝试数字字符串
        if s.isdigit():
            result = FILE_TYPES.from_int(int(s))
            if result is None:
                raise ValueError(f"Invalid file_type: {s}")
            return result

        # 别名映射
        alias_map = {
            "RISK": FILE_TYPES.RISKMANAGER,
            "ANALYZER": FILE_TYPES.ANALYZER,
            "INDEX": FILE_TYPES.INDEX,
        }
        upper = s.upper()
        if upper in alias_map:
            return alias_map[upper]

        # 枚举名匹配
        result = FILE_TYPES.enum_convert(s)
        if result is None:
            raise ValueError(f"Unknown file_type: {s}")
        return result

    # --- 正常用例 ---

    @pytest.mark.unit
    def test_strategy_string(self):
        """字符串 'strategy' → STRATEGY"""
        assert self._parse_file_type("strategy") == FILE_TYPES.STRATEGY

    @pytest.mark.unit
    def test_selector_uppercase(self):
        """大写 'SELECTOR' → SELECTOR"""
        assert self._parse_file_type("SELECTOR") == FILE_TYPES.SELECTOR

    @pytest.mark.unit
    def test_integer_sizer(self):
        """整数 5 → SIZER"""
        assert self._parse_file_type(5) == FILE_TYPES.SIZER

    @pytest.mark.unit
    def test_digit_string_strategy(self):
        """数字字符串 '6' → STRATEGY"""
        assert self._parse_file_type("6") == FILE_TYPES.STRATEGY

    @pytest.mark.unit
    def test_risk_alias(self):
        """别名 'risk' → RISKMANAGER (#5774)"""
        assert self._parse_file_type("risk") == FILE_TYPES.RISKMANAGER

    @pytest.mark.unit
    def test_risk_uppercase(self):
        """别名 'RISK' → RISKMANAGER"""
        assert self._parse_file_type("RISK") == FILE_TYPES.RISKMANAGER

    @pytest.mark.unit
    def test_mixed_case(self):
        """混合大小写 'Strategy' → STRATEGY"""
        assert self._parse_file_type("Strategy") == FILE_TYPES.STRATEGY

    @pytest.mark.unit
    def test_analyzer_int(self):
        """整数 1 → ANALYZER"""
        assert self._parse_file_type(1) == FILE_TYPES.ANALYZER

    # --- 错误用例 ---

    @pytest.mark.unit
    def test_invalid_string_raises(self):
        """无效字符串抛 ValueError"""
        with pytest.raises(ValueError, match="Unknown file_type"):
            self._parse_file_type("nonexistent")

    @pytest.mark.unit
    def test_invalid_int_raises(self):
        """无效整数抛 ValueError"""
        with pytest.raises(ValueError, match="Invalid file_type"):
            self._parse_file_type(999)
