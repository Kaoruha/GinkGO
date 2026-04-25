"""number.py 数字工具模块单元测试
性能: 154MB RSS, 0.85s, 17 tests [PASS]

覆盖范围:
- to_decimal(): float/int/Decimal/None/非法输入转换
- Number 类型别名验证
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

_path = str(Path(__file__).parent.parent.parent)
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.libs.data.number import Number, to_decimal


# ---------------------------------------------------------------------------
# to_decimal
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestToDecimal:
    """to_decimal 类型转换测试"""

    def test_int_to_decimal(self):
        """整数转 Decimal"""
        result = to_decimal(42)
        assert result == Decimal("42")
        assert isinstance(result, Decimal)

    def test_float_to_decimal(self):
        """浮点数转 Decimal（通过 str 中转避免精度问题）"""
        result = to_decimal(3.14)
        assert result == Decimal("3.14")

    def test_negative_int(self):
        """负整数转 Decimal"""
        result = to_decimal(-100)
        assert result == Decimal("-100")

    def test_negative_float(self):
        """负浮点数转 Decimal"""
        result = to_decimal(-0.5)
        assert result == Decimal("-0.5")

    def test_zero(self):
        """零值转 Decimal"""
        result = to_decimal(0)
        assert result == Decimal("0")

    def test_zero_float(self):
        """浮点零值转 Decimal"""
        result = to_decimal(0.0)
        assert result == Decimal("0.0")

    def test_decimal_passthrough(self):
        """Decimal 实例直接返回"""
        d = Decimal("123.456")
        result = to_decimal(d)
        assert result is d

    def test_decimal_negative_passthrough(self):
        """负数 Decimal 实例直接返回"""
        d = Decimal("-999.99")
        result = to_decimal(d)
        assert result is d

    def test_none_raises_type_error(self):
        """None 输入应抛出 TypeError"""
        with pytest.raises(TypeError, match="Cannot convert None"):
            to_decimal(None)

    def test_scientific_notation_float(self):
        """科学计数法浮点数"""
        result = to_decimal(1.5e10)
        assert isinstance(result, Decimal)

    def test_very_small_float(self):
        """极小浮点数"""
        result = to_decimal(1e-10)
        assert isinstance(result, Decimal)

    def test_large_int(self):
        """大整数"""
        result = to_decimal(10**18)
        assert result == Decimal(str(10**18))


# ---------------------------------------------------------------------------
# Number 类型别名
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestNumberTypeAlias:
    """Number 类型别名验证"""

    def test_number_accepts_int(self):
        """int 符合 Number 类型"""
        assert isinstance(42, Number)

    def test_number_accepts_float(self):
        """float 符合 Number 类型"""
        assert isinstance(3.14, Number)

    def test_number_accepts_decimal(self):
        """Decimal 符合 Number 类型"""
        assert isinstance(Decimal("1"), Number)

    def test_number_rejects_str(self):
        """str 不符合 Number 类型"""
        assert not isinstance("123", Number)

    def test_number_rejects_none(self):
        """None 不符合 Number 类型"""
        assert not isinstance(None, Number)
