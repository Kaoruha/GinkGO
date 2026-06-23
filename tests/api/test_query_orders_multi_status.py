# Issue: #6047
# Upstream: api.trading._expand_status_enums, api.trading._query_orders
# Downstream: pytest
# Role: _query_orders 多状态过滤修复 — status 列表须全部生效，非仅首个

"""
_query_orders 多状态过滤测试

根因：_query_orders 第 590 行 first_status=status_filter[0] 只取首个状态组，
第 593 行 enums[0] 只取同组首个 enum。两层截断致多状态过滤失效
（?status=pending&status=filled 只返回 pending 的 NEW，丢弃 SUBMITTED + FILLED）。

修复：抽纯函数 _expand_status_enums 完整展开所有匹配 enum；
_query_orders 对每个 enum 各查一次合并。
"""

import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace


class TestExpandStatusEnums:
    """验证 _expand_status_enums 把状态字符串列表完整展开为 enum 列表"""

    def test_pending_expands_to_both_new_and_submitted(self):
        """#6047: pending 须映射到 [NEW, SUBMITTED] 全组，非仅首个 enum"""
        from api.trading import _expand_status_enums
        from ginkgo.enums import ORDERSTATUS_TYPES

        result = _expand_status_enums(["pending"])
        assert ORDERSTATUS_TYPES.NEW in result
        assert ORDERSTATUS_TYPES.SUBMITTED in result
        assert len(result) == 2

    def test_multiple_status_groups_all_expanded(self):
        """#6047: [pending, filled] 须展开为 3 个 enum（NEW + SUBMITTED + FILLED），非仅首个状态组"""
        from api.trading import _expand_status_enums
        from ginkgo.enums import ORDERSTATUS_TYPES

        result = _expand_status_enums(["pending", "filled"])
        assert set(result) == {
            ORDERSTATUS_TYPES.NEW,
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.FILLED,
        }
        assert len(result) == 3

    def test_duplicates_deduped_order_preserved(self):
        """#6047: 重复状态去重，且按 status_filter 首次出现顺序排列"""
        from api.trading import _expand_status_enums
        from ginkgo.enums import ORDERSTATUS_TYPES

        result = _expand_status_enums(["filled", "pending", "filled"])
        assert result == [
            ORDERSTATUS_TYPES.FILLED,
            ORDERSTATUS_TYPES.NEW,
            ORDERSTATUS_TYPES.SUBMITTED,
        ]

    def test_none_or_empty_returns_empty(self):
        """#6047: 无过滤（None/空列表）返回空列表，表示查全部"""
        from api.trading import _expand_status_enums

        assert _expand_status_enums(None) == []
        assert _expand_status_enums([]) == []

    def test_unknown_status_ignored(self):
        """#6047: 未识别的状态字符串静默忽略，不报错"""
        from api.trading import _expand_status_enums

        assert _expand_status_enums(["unknown_status"]) == []
        # 混合：有效 + 无效，仅有效的展开
        from ginkgo.enums import ORDERSTATUS_TYPES
        result = _expand_status_enums(["filled", "bogus"])
        assert result == [ORDERSTATUS_TYPES.FILLED]


class TestQueryOrdersMultiStatus:
    """端到端：_query_orders 多状态过滤须返回所有匹配状态的订单"""

    @staticmethod
    def _make_record(uuid, status_enum, code="000001.SZ"):
        """构造一条订单记录（status 存 enum 的 int 值，模拟 DB 行）"""
        return SimpleNamespace(
            uuid=uuid, code=code, status=status_enum.value,
            direction=1, limit_price=10.0, volume=100,
            transaction_volume=0, transaction_price=0,
            business_timestamp=None, timestamp=None,
        )

    def test_multi_status_returns_orders_from_all_groups(self):
        """#6047: [pending, filled] 须返回 NEW+SUBMITTED+FILLED 三类订单，非仅首个状态"""
        from api.trading import _query_orders
        from ginkgo.enums import ORDERSTATUS_TYPES

        new_rec = self._make_record("o-new", ORDERSTATUS_TYPES.NEW)
        sub_rec = self._make_record("o-sub", ORDERSTATUS_TYPES.SUBMITTED)
        fill_rec = self._make_record("o-fill", ORDERSTATUS_TYPES.FILLED)

        def fake_get(account_id, status=None, page_size=None):
            bucket = {
                ORDERSTATUS_TYPES.NEW.value: [new_rec],
                ORDERSTATUS_TYPES.SUBMITTED.value: [sub_rec],
                ORDERSTATUS_TYPES.FILLED.value: [fill_rec],
            }
            data = bucket.get(status, [])
            result = MagicMock()
            result.success = True
            result.data = {"data": data, "total": len(data)}
            return result

        mock_service = MagicMock()
        mock_service.get_orders_by_portfolio.side_effect = fake_get

        with patch("api.trading._get_result_service", return_value=mock_service):
            orders = _query_orders("acct-1", ["pending", "filled"])

        # 三类订单都出现（修复前只返回 NEW 一个）
        uuids = {o["order_id"] for o in orders}
        assert uuids == {"o-new", "o-sub", "o-fill"}
        # service 按 enum 逐个查询（3 次），非旧逻辑的单次 first_status
        assert mock_service.get_orders_by_portfolio.call_count == 3

    def test_no_filter_queries_once_with_none_status(self):
        """#6047: 无 status 过滤时单次查询 status=None（不退化为多次）"""
        from api.trading import _query_orders

        result = MagicMock()
        result.success = True
        result.data = {"data": [], "total": 0}
        mock_service = MagicMock()
        mock_service.get_orders_by_portfolio.return_value = result

        with patch("api.trading._get_result_service", return_value=mock_service):
            _query_orders("acct-1", None)

        assert mock_service.get_orders_by_portfolio.call_count == 1
        # status 参数为 None
        called_kwargs = mock_service.get_orders_by_portfolio.call_args
        assert called_kwargs.kwargs.get("status") is None
