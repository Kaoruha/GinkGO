"""epic #6851 ADR-037 D3: MPortfolio.update(slippage=...) smoke (CI gate 覆盖信号).

D3 给 MPortfolio 加 slippage 列 + update 接受 slippage (L131-132:
``if slippage is not None: self.slippage = slippage``). 被 containers import 链触达
但 update 方法体无 smoke 调 → diff coverage gate 红. 本 smoke 调 update(name, slippage=...)
补覆盖信号 (singledispatchmethod 分派 name:str, True/False 两分支).
"""
from ginkgo.data.models.model_portfolio import MPortfolio


def test_update_sets_slippage():
    p = MPortfolio()
    p.update("test-portfolio", slippage=0.001)
    assert p.slippage == 0.001


def test_update_without_slippage_unchanged():
    """不传 slippage 时守卫 False 分支 (if slippage is not None → 不赋值)."""
    p = MPortfolio()
    before = p.slippage
    p.update("test-portfolio")
    assert p.slippage == before
