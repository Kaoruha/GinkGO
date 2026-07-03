"""TDD tests for #4893: CNAllSelector 忽略传入的股票列表参数。

根因: cn_all_selector.py __init__(name, *args, **kwargs) 不接 codes 形参，
且 *args 转发给 SelectorBase.__init__（只收 name）会 TypeError；pick() 固定查
全 A 股 get_stockinfos_df() 填 _interested，调用方传入的 codes 被丢弃。
修复: __init__ 加 codes 形参（mirror FixedSelector），ensure_list 归一化后存
_interested。codes 非空 → pick() 早返该子集；codes 空（默认）→ 保留全市场回退
（cn_all 本意，区别于 FixedSelector 的空告警）。
"""
from typing import List, Union
from unittest.mock import patch, MagicMock

import pytest

from ginkgo.trading.selectors.cn_all_selector import CNAllSelector


class TestCNAllSelectorRespectsCodes:
    """#4893: 传入 codes 子集时 pick 返回该子集，非全 A 股。"""

    def test_codes_subset_returned_not_full_market(self):
        """tracer bullet: codes=['000001','600519','000858'] → pick 返回该子集。"""
        sel = CNAllSelector("cn_all", codes=["000001", "600519", "000858"])
        # 修复前: __init__ 不接 codes → TypeError；修复后: pick 早返 codes 子集
        assert sel.pick() == ["000001", "600519", "000858"]

    def test_codes_as_positional_arg_index1(self):
        """component_loader 按 index 排序后 component_class(*params) 位置绑定：
        index0=name, index1=codes。故第二位置参应被 codes 接收。"""
        sel = CNAllSelector("cn_all", ["000001", "600519", "000858"])
        assert sel.pick() == ["000001", "600519", "000858"]

    def test_codes_as_json_string_normalized(self):
        """ensure_list 契约: JSON 字符串 '["a","b"]' → ["a","b"]。"""
        sel = CNAllSelector("cn_all", codes='["000001", "600519"]')
        assert sel.pick() == ["000001", "600519"]

    def test_codes_as_comma_string_normalized(self):
        """ensure_list 契约: 逗号分隔字符串 → list。"""
        sel = CNAllSelector("cn_all", codes="000001,600519,000858")
        assert sel.pick() == ["000001", "600519", "000858"]

    def test_single_code_string_wrapped_to_list(self):
        """ensure_list 契约: 单值 → [val]。"""
        sel = CNAllSelector("cn_all", codes="000001")
        assert sel.pick() == ["000001"]


class TestCNAllSelectorEmptyCodesFallsBackToMarket:
    """#4893: codes 空（默认）须保留全市场查询——cn_all 的本意。
    component_loader.py:337 / engine_assembly_service.py:311 无参实例化依赖此行为。
    """

    def test_default_codes_queries_stockinfo_service(self):
        """无 codes → pick() 走全市场 get_stockinfos_df() 回退路径。"""
        fake_df = MagicMock()
        fake_df.empty = False
        fake_df.__getitem__ = MagicMock(return_value=MagicMock(tolist=lambda: ["000001", "600519"]))
        fake_result = MagicMock(success=True, data=fake_df)

        with patch("ginkgo.data.containers.container.stockinfo_service") as mock_svc:
            mock_svc.return_value.get_stockinfos_df.return_value = fake_result
            sel = CNAllSelector()  # 无参，fallback 路径
            result = sel.pick()

        assert result == ["000001", "600519"]
        mock_svc.return_value.get_stockinfos_df.assert_called_once()

    def test_empty_string_codes_also_falls_back(self):
        """显式 codes='' 等价默认，走全市场回退（不似 FixedSelector 那样恒空）。"""
        fake_df = MagicMock()
        fake_df.empty = False
        fake_df.__getitem__ = MagicMock(return_value=MagicMock(tolist=lambda: ["900001"]))
        fake_result = MagicMock(success=True, data=fake_df)

        with patch("ginkgo.data.containers.container.stockinfo_service") as mock_svc:
            mock_svc.return_value.get_stockinfos_df.return_value = fake_result
            sel = CNAllSelector("cn_all", codes="")
            result = sel.pick()

        assert result == ["900001"]
        mock_svc.return_value.get_stockinfos_df.assert_called_once()

    def test_codes_set_does_not_query_db(self):
        """有 codes 时 pick() 早返，不应触发全市场查询（性能 + 避免 #4893 脏 ticker）。"""
        with patch("ginkgo.data.containers.container.stockinfo_service") as mock_svc:
            mock_svc.return_value.get_stockinfos_df = MagicMock()  # 不应被调用
            sel = CNAllSelector("cn_all", codes=["000001"])
            result = sel.pick()

        assert result == ["000001"]
        mock_svc.return_value.get_stockinfos_df.assert_not_called()
