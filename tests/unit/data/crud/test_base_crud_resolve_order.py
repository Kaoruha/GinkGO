"""
BaseCRUD._resolve_order 单元测试（#6884：find 默认「最新在最前」+ ``-`` 前缀归一）

_resolve_order 是纯函数（仅 touch self.model_class + 模块级 GLOG），用 SimpleNamespace
造假 self、真 Python 类造假 model（避开 MagicMock 对任意属性 hasattr 恒 True 的陷阱）。
无需 DB。
"""

from types import SimpleNamespace

import pytest
from unittest.mock import patch

from ginkgo.data.crud.base_crud import BaseCRUD


# 假 model：用类属性模拟 SQLAlchemy mapped_column（hasattr/getattr 语义一致）
class _TimeSeriesModel:
    """时序模型：含 business_timestamp（优先）+ create_at + end_time"""

    business_timestamp = "BT_SENTINEL"
    create_at = "CA_SENTINEL"
    end_time = "ET_SENTINEL"


class _RelationModel:
    """关系模型：仅 create_at（无 business_timestamp）"""

    create_at = "CA_SENTINEL"


class _BareModel:
    """既无 business_timestamp 也无 create_at（如部分 ClickHouse 时序表）"""

    pass


def _crud(model_cls):
    return SimpleNamespace(model_class=model_cls)


class TestResolveOrder:
    """_resolve_order：默认序 + ``-`` 前缀 + 显式序 + 未知字段回退"""

    @pytest.mark.unit
    def test_default_timeseries_prefers_business_timestamp_desc(self):
        """缺省 order_by + 时序模型 → business_timestamp 倒序（最新在最前）"""
        attr, desc = BaseCRUD._resolve_order(_crud(_TimeSeriesModel), None, False)
        assert attr is _TimeSeriesModel.business_timestamp
        assert desc is True

    @pytest.mark.unit
    def test_default_relation_falls_back_to_create_at_desc(self):
        """缺省 order_by + 关系模型（无 business_timestamp）→ create_at 倒序"""
        attr, desc = BaseCRUD._resolve_order(_crud(_RelationModel), None, False)
        assert attr is _RelationModel.create_at
        assert desc is True

    @pytest.mark.unit
    def test_default_bare_model_no_order(self):
        """缺省 order_by + 模型无任何时间戳字段 → 不排序（保持旧行为）"""
        attr, desc = BaseCRUD._resolve_order(_crud(_BareModel), None, False)
        assert attr is None
        assert desc is True

    @pytest.mark.unit
    def test_dash_prefix_recognized_as_desc(self):
        """``order_by="-end_time"`` → 剥离 ``-``、按 end_time 倒序

        历史 bug（#6884）：旧代码 ``hasattr(model, "-end_time")`` 恒 False →
        倒序被静默忽略，``backtest_task_crud.get_completed_tasks`` 的「倒序」是假的。
        """
        attr, desc = BaseCRUD._resolve_order(_crud(_TimeSeriesModel), "-end_time", False)
        assert attr is _TimeSeriesModel.end_time
        assert desc is True

    @pytest.mark.unit
    def test_explicit_order_asc(self):
        """显式 order_by + desc_order=False → 升序"""
        attr, desc = BaseCRUD._resolve_order(_crud(_TimeSeriesModel), "end_time", False)
        assert attr is _TimeSeriesModel.end_time
        assert desc is False

    @pytest.mark.unit
    def test_explicit_order_desc(self):
        """显式 order_by + desc_order=True → 倒序"""
        attr, desc = BaseCRUD._resolve_order(_crud(_TimeSeriesModel), "end_time", True)
        assert attr is _TimeSeriesModel.end_time
        assert desc is True

    @pytest.mark.unit
    def test_dash_prefix_wins_when_desc_order_false(self):
        """``-`` 前缀与 desc_order=False 冲突时，``-`` 前缀取胜（显式倒序意图）"""
        attr, desc = BaseCRUD._resolve_order(_crud(_TimeSeriesModel), "-end_time", False)
        assert desc is True

    @pytest.mark.unit
    @patch("ginkgo.data.crud.base_crud.GLOG")
    def test_unknown_field_warns_and_falls_back_to_default(self, mock_glog):
        """显式 order_by 但字段不存在 → WARNING + 回退默认序

        typo 的响亮 raise 留给 #6885（filter 字段对称收口）；此处先回退默认序，
        避免静默无序（旧行为）也比假装排了序诚实。
        """
        attr, desc = BaseCRUD._resolve_order(
            _crud(_TimeSeriesModel), "nonexistent_field", False
        )
        assert attr is _TimeSeriesModel.business_timestamp  # 回退默认序
        assert desc is True
        assert mock_glog.WARNING.called

    @pytest.mark.unit
    @patch("ginkgo.data.crud.base_crud.GLOG")
    def test_unknown_field_on_bare_model_no_order(self, mock_glog):
        """显式未知字段 + 模型无默认序字段 → 仍 WARNING，返回 (None, True)"""
        attr, desc = BaseCRUD._resolve_order(_crud(_BareModel), "nonexistent", False)
        assert attr is None
        assert desc is True
        assert mock_glog.WARNING.called
