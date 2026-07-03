"""TDD tests for #5163: CNAllSelector 回测宽 universe 时无数据 code 逐日刷屏 WARN + N+1 查询。

根因: cn_all_selector.pick 直接返回 stockinfo 全市场 codes，不剔除 DB 无 bar 的 code，
feeder 每日对全市场逐股 bar_service.get() N+1 查询。
修复: pick 拿到全市场 codes 后，调 bar_service.get_available_codes() 一次性剔除无数据 code。
"""
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
from ginkgo.data.services.base_service import ServiceResult


def _make_stockinfo_df(codes):
    return pd.DataFrame({"code": codes})


class TestCNAllSelectorPrefilterNoData:
    """#5163: pick 应剔除 DB 中无 bar 数据的 code（批量预过滤）。"""

    def test_pick_filters_out_codes_without_bar_data(self):
        """全市场 [A,B,C] 但 DB 仅有 [A,B] → pick 返回 [A,B]（C 被剔除）"""
        sel = CNAllSelector(name="test")
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_stockinfos_df.return_value = ServiceResult.success(
            data=_make_stockinfo_df(["A.SZ", "B.SZ", "C.SZ"])
        )
        mock_bar = MagicMock()
        mock_bar.get_available_codes.return_value = ServiceResult.success(
            data=["A.SZ", "B.SZ"]
        )
        with patch(
            "ginkgo.data.containers.container.stockinfo_service",
            return_value=mock_stockinfo,
        ), patch(
            "ginkgo.data.containers.container.bar_service",
            return_value=mock_bar,
        ):
            result = sel.pick()
        assert "C.SZ" not in result, "无数据的 C.SZ 应被预过滤剔除 #5163"
        assert set(result) == {"A.SZ", "B.SZ"}

    def test_pick_returns_all_when_bar_service_fails(self):
        """bar_service.get_available_codes 失败 → 降级返回全市场（不阻断回测）"""
        sel = CNAllSelector(name="test")
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_stockinfos_df.return_value = ServiceResult.success(
            data=_make_stockinfo_df(["A.SZ", "B.SZ", "C.SZ"])
        )
        mock_bar = MagicMock()
        mock_bar.get_available_codes.return_value = ServiceResult.error(error="db down")
        with patch(
            "ginkgo.data.containers.container.stockinfo_service",
            return_value=mock_stockinfo,
        ), patch(
            "ginkgo.data.containers.container.bar_service",
            return_value=mock_bar,
        ):
            result = sel.pick()
        # 必须实际调用了预过滤（否则是未实现）
        mock_bar.get_available_codes.assert_called_once()
        # 降级：不剔除，返回全市场（fail-open，不因预过滤失败阻断）
        assert set(result) == {"A.SZ", "B.SZ", "C.SZ"}

    def test_pick_logs_filtered_count(self):
        """剔除时应 INFO 一次被过滤数量（便于诊断，非逐股刷屏）"""
        sel = CNAllSelector(name="test")
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_stockinfos_df.return_value = ServiceResult.success(
            data=_make_stockinfo_df(["A.SZ", "B.SZ", "C.SZ", "D.SZ"])
        )
        mock_bar = MagicMock()
        mock_bar.get_available_codes.return_value = ServiceResult.success(
            data=["A.SZ"]
        )
        with patch(
            "ginkgo.data.containers.container.stockinfo_service",
            return_value=mock_stockinfo,
        ), patch(
            "ginkgo.data.containers.container.bar_service",
            return_value=mock_bar,
        ), patch("ginkgo.trading.selectors.cn_all_selector.GLOG") as mock_glog:
            result = sel.pick()
        assert set(result) == {"A.SZ"}
        # 应有一次 INFO/WARNING 记录被剔除的数量
        info_msgs = (
            [c[0][0] for c in mock_glog.INFO.call_args_list]
            + [c[0][0] for c in mock_glog.WARNING.call_args_list]
        )
        assert any("3" in m and ("filter" in m.lower() or "过滤" in m or "剔除" in m) for m in info_msgs), (
            f"应记录被剔除数量(3), 实际 INFO/WARN: {info_msgs}"
        )
