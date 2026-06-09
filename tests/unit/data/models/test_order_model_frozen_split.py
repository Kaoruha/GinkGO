"""
MOrder / MOrderRecord frozen 字段拆分测试

验证 frozen 列已拆分为 frozen_money + frozen_volume，
与 MPosition 保持一致的 schema 模式。
"""
import pytest
from decimal import Decimal
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.models.model_order import MOrder
from ginkgo.data.models.model_order_record import MOrderRecord


class TestMOrderFrozenSplit:
    """MOrder.frozen → frozen_money + frozen_volume 拆分"""

    @pytest.mark.unit
    def test_no_legacy_frozen_column(self):
        """MOrder 不应再有 frozen 列"""
        m = MOrder()
        assert not hasattr(m, "frozen"), "MOrder 应移除 frozen 列，改为 frozen_money + frozen_volume"

    @pytest.mark.unit
    def test_has_frozen_money(self):
        """MOrder 应有 frozen_money 列"""
        m = MOrder()
        assert hasattr(m, "frozen_money")

    @pytest.mark.unit
    def test_has_frozen_volume(self):
        """MOrder 应有 frozen_volume 列"""
        m = MOrder()
        assert hasattr(m, "frozen_volume")

    @pytest.mark.unit
    def test_frozen_money_default_none_before_flush(self):
        """frozen_money 未设置时为 None（SQLAlchemy default 需要 flush）"""
        m = MOrder()
        assert m.frozen_money is None

    @pytest.mark.unit
    def test_frozen_volume_default_none_before_flush(self):
        """frozen_volume 未设置时为 None（SQLAlchemy default 需要 flush）"""
        m = MOrder()
        assert m.frozen_volume is None

    @pytest.mark.unit
    def test_frozen_money_settable(self):
        """frozen_money 可通过构造设置"""
        m = MOrder(frozen_money=Decimal("15000.50"))
        assert m.frozen_money == Decimal("15000.50")

    @pytest.mark.unit
    def test_frozen_volume_settable(self):
        """frozen_volume 可通过构造设置"""
        m = MOrder(frozen_volume=500)
        assert m.frozen_volume == 500


class TestMOrderRecordFrozenSplit:
    """MOrderRecord.frozen → frozen_money + frozen_volume 拆分"""

    @pytest.mark.unit
    def test_no_legacy_frozen_column(self):
        """MOrderRecord 不应再有 frozen 列"""
        m = MOrderRecord()
        assert not hasattr(m, "frozen"), "MOrderRecord 应移除 frozen 列，改为 frozen_money + frozen_volume"

    @pytest.mark.unit
    def test_has_frozen_money(self):
        """MOrderRecord 应有 frozen_money 列"""
        m = MOrderRecord()
        assert hasattr(m, "frozen_money")

    @pytest.mark.unit
    def test_has_frozen_volume(self):
        """MOrderRecord 应有 frozen_volume 列"""
        m = MOrderRecord()
        assert hasattr(m, "frozen_volume")
