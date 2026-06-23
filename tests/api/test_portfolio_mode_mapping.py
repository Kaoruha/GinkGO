"""
portfolio mode 字符串映射锚定测试。

背景（#6029 AC2）：api/api/portfolio.py 的 mode→字符串映射原先用魔法数字内联展开，
重构后 get-portfolio 端点（L362）复用 `_map_mode`，与 list 端点（L233）一致。
`_map_mode` 此前无直接测试——本文件锚定其三分支契约，防止未来改动静默改变映射语义。
"""
import pytest


class TestMapMode:
    """`_map_mode(mode_value)` 把 PORTFOLIO_MODE_TYPES 数值映射为对外字符串。"""

    def test_backtest(self, api_modules):
        from api.portfolio import _map_mode

        assert _map_mode(0) == "BACKTEST"

    def test_paper(self, api_modules):
        from api.portfolio import _map_mode

        assert _map_mode(1) == "PAPER"

    def test_live(self, api_modules):
        from api.portfolio import _map_mode

        # LIVE(2) 走 else 分支；任意非 BACKTEST/PAPER 值同样兜底为 LIVE
        assert _map_mode(2) == "LIVE"
        assert _map_mode(99) == "LIVE"
