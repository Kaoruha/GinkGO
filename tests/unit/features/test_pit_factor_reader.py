"""PITFactorReader 测试 -- #6793 Phase 2

验证因子读取入口的 point-in-time 硬约束:
- at_time 必传 (None raise, 不可绕过)
- 只返回 timestamp <= at_time 的因子值
- 已知泄漏因子 (ts > at_time) 被拦截 (防御性双保险, 即使底层漏过滤)
- at_time 下推到 crud (SQL 层 timestamp__lte)
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

try:
    from ginkgo.features.readers.pit_factor_reader import PITFactorReader
    HAS_READER = True
except ImportError:
    HAS_READER = False


def _factor(value, ts):
    """构造真实 MFactor (reader 通过 .timestamp / .factor_value 访问)。"""
    from ginkgo.data.models import MFactor
    return MFactor(
        entity_id="000001.SZ", factor_name="ROC",
        factor_value=Decimal(str(value)), timestamp=ts,
    )


@pytest.mark.skipif(not HAS_READER, reason="PITFactorReader not available")
@pytest.mark.unit
class TestPITFactorReader:
    def test_at_time_required_raises(self):
        """at_time=None → raise ValueError (PIT 硬约束, 不可绕过)。"""
        reader = PITFactorReader(MagicMock())
        with pytest.raises(ValueError, match="at_time"):
            reader.get_factor_value("000001.SZ", "ROC", at_time=None)

    def test_returns_value_when_factor_before_at_time(self):
        """因子 ts <= at_time → 返回 factor_value。"""
        crud = MagicMock()
        crud.get_latest_factors_by_entity.return_value = [_factor(1.5, datetime(2024, 1, 15))]
        reader = PITFactorReader(crud)
        val = reader.get_factor_value("000001.SZ", "ROC", at_time=datetime(2024, 6, 1))
        assert val == 1.5

    def test_rejects_known_leak_future_factor(self):
        """已知泄漏因子 (ts=2024-12-01 > at_time=2024-06-01) → 返回 None (拦截)。

        模拟底层 crud 漏过滤返回了未来值, reader 防御层仍拦截。
        """
        crud = MagicMock()
        crud.get_latest_factors_by_entity.return_value = [_factor(999.0, datetime(2024, 12, 1))]
        reader = PITFactorReader(crud)
        val = reader.get_factor_value("000001.SZ", "ROC", at_time=datetime(2024, 6, 1))
        assert val is None

    def test_passes_at_time_to_crud(self):
        """at_time 下推到 crud.get_latest_factors_by_entity (SQL 层 timestamp__lte)。"""
        crud = MagicMock()
        crud.get_latest_factors_by_entity.return_value = []
        reader = PITFactorReader(crud)
        at = datetime(2024, 6, 1)
        reader.get_factor_value("000001.SZ", "ROC", at_time=at)
        kwargs = crud.get_latest_factors_by_entity.call_args[1]
        assert kwargs["at_time"] == at
        assert kwargs["entity_id"] == "000001.SZ"
        assert kwargs["factor_names"] == ["ROC"]

    def test_no_factor_returns_none(self):
        """crud 返回空 (该 entity 在 at_time 前无此因子) → 返回 None。"""
        crud = MagicMock()
        crud.get_latest_factors_by_entity.return_value = []
        reader = PITFactorReader(crud)
        val = reader.get_factor_value("000001.SZ", "ROC", at_time=datetime(2024, 6, 1))
        assert val is None
