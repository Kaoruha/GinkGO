"""
#5774: node-graphs file_type 解析测试

验证 _resolve_file_type 能正确解析：
- 字符串枚举名（"strategy"）
- 整数/数字字符串（6, "6"）
- 大小写变体（"Strategy", "STRATEGY"）
- 别名（"risk" → RISKMANAGER）

直接导入 api/api/_file_type.py（无模块级副作用）进行测试。
"""

import sys
from pathlib import Path

import pytest
from ginkgo.enums import FILE_TYPES

# _file_type.py 无 FastAPI/core 依赖，安全加入 sys.path
_api_api_dir = str(Path(__file__).parent.parent.parent / "api" / "api")
if _api_api_dir not in sys.path:
    sys.path.insert(0, _api_api_dir)

from _file_type import _resolve_file_type


class TestFileTypeParsing:
    """file_type 解析逻辑测试 — 直接测试生产代码"""

    # --- 正常用例 ---

    @pytest.mark.unit
    def test_strategy_string(self):
        """字符串 'strategy' → STRATEGY"""
        assert _resolve_file_type("strategy") == FILE_TYPES.STRATEGY

    @pytest.mark.unit
    def test_selector_uppercase(self):
        """大写 'SELECTOR' → SELECTOR"""
        assert _resolve_file_type("SELECTOR") == FILE_TYPES.SELECTOR

    @pytest.mark.unit
    def test_integer_sizer(self):
        """整数 5 → SIZER"""
        assert _resolve_file_type(5) == FILE_TYPES.SIZER

    @pytest.mark.unit
    def test_digit_string_strategy(self):
        """数字字符串 '6' → STRATEGY"""
        assert _resolve_file_type("6") == FILE_TYPES.STRATEGY

    @pytest.mark.unit
    def test_risk_alias(self):
        """别名 'risk' → RISKMANAGER (#5774)"""
        assert _resolve_file_type("risk") == FILE_TYPES.RISKMANAGER

    @pytest.mark.unit
    def test_risk_uppercase(self):
        """别名 'RISK' → RISKMANAGER"""
        assert _resolve_file_type("RISK") == FILE_TYPES.RISKMANAGER

    @pytest.mark.unit
    def test_risk_manager_snake_case(self):
        """snake_case 'risk_manager' → RISKMANAGER (#5578)"""
        assert _resolve_file_type("risk_manager") == FILE_TYPES.RISKMANAGER

    @pytest.mark.unit
    def test_riskmanager_compact_compat(self):
        """连写 'riskmanager' → RISKMANAGER（兼容，回归守护 #5578 ③）"""
        assert _resolve_file_type("riskmanager") == FILE_TYPES.RISKMANAGER

    @pytest.mark.unit
    def test_mixed_case(self):
        """混合大小写 'Strategy' → STRATEGY"""
        assert _resolve_file_type("Strategy") == FILE_TYPES.STRATEGY

    @pytest.mark.unit
    def test_analyzer_int(self):
        """整数 1 → ANALYZER"""
        assert _resolve_file_type(1) == FILE_TYPES.ANALYZER

    # --- 错误用例 ---

    @pytest.mark.unit
    def test_invalid_string_raises(self):
        """无效字符串抛 ValueError"""
        with pytest.raises(ValueError, match="Unknown file_type"):
            _resolve_file_type("nonexistent")

    @pytest.mark.unit
    def test_invalid_int_raises(self):
        """无效整数抛 ValueError"""
        with pytest.raises(ValueError, match="Invalid file_type"):
            _resolve_file_type(999)
