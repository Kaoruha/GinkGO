"""TDD tests for #5363: FixedSelector 默认 codes="" → ensure_list("")=[] → pick() 返空，
回测静默零信号/零交易，无任何告警。

根因: fixed_selector.py __init__ `codes: Union[str,List[str]] = ""`，
`self._interested = ensure_list(codes)` 当 codes="" 得 []，pick() 直接返回 self._interested。
修复: __init__ 检测 _interested 为空时发 GLOG.WARNING（装配期一次性，非 pick 每 bar 刷屏）。
"""
from unittest.mock import patch

import pytest

from ginkgo.trading.selectors.fixed_selector import FixedSelector


class TestFixedSelectorEmptyCodesWarns:
    """#5363: 空 codes 不应静默——须在装配期(__init__)发明确告警。"""

    def test_init_empty_codes_emits_warning(self):
        """codes="" 时 __init__ 应发 WARNING，提示 pick 将恒空致零信号。"""
        with patch("ginkgo.trading.selectors.fixed_selector.GLOG") as mock_glog:
            FixedSelector(codes="")
        # 修复前: 无 WARNING 调用（静默）
        # 修复后: WARNING 被调用，消息含 codes/空 等关键词
        mock_glog.WARNING.assert_called_once()
        msg = mock_glog.WARNING.call_args[0][0]
        assert "codes" in msg.lower() or "空" in msg, (
            "空 codes 的告警消息应点明根因（codes 为空）#5363"
        )

    def test_init_default_codes_emits_warning(self):
        """不传 codes（走默认 ""）同样应告警——这是 issue 复现路径。"""
        with patch("ginkgo.trading.selectors.fixed_selector.GLOG") as mock_glog:
            FixedSelector()
        mock_glog.WARNING.assert_called_once()

    def test_init_with_codes_does_not_warn(self):
        """有 codes 时不应告警（避免误报，且不影响正常回测）。"""
        with patch("ginkgo.trading.selectors.fixed_selector.GLOG") as mock_glog:
            sel = FixedSelector(codes="000001.SZ")
        mock_glog.WARNING.assert_not_called()
        # 有 codes 正常出信号（验收: 有 codes 回测正常产生信号）
        assert sel.pick() == ["000001.SZ"]

    def test_pick_empty_codes_returns_empty(self):
        """行为不变: 空 codes 时 pick() 仍返回 []（告警不改变返回值）。"""
        with patch("ginkgo.trading.selectors.fixed_selector.GLOG"):
            sel = FixedSelector(codes="")
        assert sel.pick() == []
