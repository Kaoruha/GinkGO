"""
Unit tests for RatioSizer None-data guard (#6043).

RatioSizer.cal() at ratio_sizer.py:110-111:
    result = container.bar_service().get(...)
    if not result.success or len(result.data) == 0:

When bar_service returns success=True but data=None (ServiceResult explicitly
allows None data, base_service.py:36), `len(None)` raises TypeError. The
TypeError is swallowed by the broad `except Exception` at L163-165 and logged
as ERROR "failed to create order" + return None — a semantic mismatch (data
missing misreported as order-creation failure).

The fix routes data=None through the existing CRITICAL "has no data" guard
(L112) instead of the except path, so the log correctly classifies the cause.

RatioSizer still uses container.bar_service() (not migrated to _data_feeder),
so tests patch ginkgo.trading.sizers.ratio_sizer.container — same pattern as
test_atr_sizer.py.
"""
import datetime
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Signal
from ginkgo.trading.sizers.ratio_sizer import RatioSizer


@pytest.fixture
def sizer():
    s = RatioSizer(name="TestRatioSizer", ratio="0.1")
    # RatioSizer.cal uses self.get_time_provider().now() (L105); pin it for
    # deterministic bar_service date-range args.
    tp = MagicMock()
    tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
    s.get_time_provider = MagicMock(return_value=tp)
    return s


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    # RatioSizer.cal L89 校验 signal.is_valid()（atr_sizer 不校验，故其测试无需有效信号）。
    # is_valid 需 portfolio_id/engine_id/code/direction(DIRECTION_TYPES实例)/timestamp(非None非未来)。
    # TimeMixin.__init__ 自动把 _timestamp=datetime.now()，故构造即带非未来时间戳，无需显式设。
    return Signal(
        portfolio_id="test-portfolio",
        engine_id="test-engine",
        code=code,
        direction=direction,
    )


def _make_portfolio_info(cash=1000000.0, positions=None):
    return {"cash": cash, "positions": positions or {}}


class TestRatioSizerNoneDataGuard:
    """#6043: bar_service 返 success=True, data=None 时走无数据守卫,
    不走 except 吞成 ERROR "failed to create order"。"""

    def test_none_data_returns_none_via_guard_not_exception(self, sizer):
        """data=None → CRITICAL "has no data" 守卫返 None；
        不触发 except 的 ERROR "failed to create order"（数据缺失≠订单创建失败）。

        修复前：len(None) → TypeError → L163 except → ERROR "failed to create order"
        修复后：result.data is None 短路 → L112 CRITICAL "has no data" → return None
        """
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=1000000.0)

        with patch("ginkgo.trading.sizers.ratio_sizer.container") as cm, \
             patch("ginkgo.trading.sizers.ratio_sizer.GLOG") as glog:
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data = None  # 关键：success=True 但 data=None
            service.get.return_value = result
            cm.bar_service.return_value = service

            order = sizer.cal(info, signal)

        # 行为契约：返 None（不创建订单）
        assert order is None

        # 守卫路径：CRITICAL "has no data" 被调（正确分类为数据缺失）
        critical_calls = [str(c) for c in glog.CRITICAL.call_args_list]
        assert any("has no data" in c for c in critical_calls), (
            f"应走 CRITICAL 无数据守卫路径，实际 CRITICAL 调用: {critical_calls}"
        )

        # 非 except 路径：ERROR "failed to create order" 未被调
        # （数据缺失不应误报为订单创建失败，否则污染日志诊断）
        error_calls = [str(c) for c in glog.ERROR.call_args_list]
        assert not any("failed to create order" in c for c in error_calls), (
            f"不应走 except 吞路径（len(None) TypeError），实际 ERROR 调用: {error_calls}"
        )

    def test_none_data_does_not_raise(self, sizer):
        """data=None 时 cal() 不向调用方抛异常（被守卫拦截，非被 except 吞）。

        区分：守卫=主动 return None；except=被动捕获后 return None。
        本测验证不抛 + 不依赖 except（通过 GLOG 分类间接验证，见上一测）。
        """
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=1000000.0)

        with patch("ginkgo.trading.sizers.ratio_sizer.container") as cm, \
             patch("ginkgo.trading.sizers.ratio_sizer.GLOG"):
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data = None
            service.get.return_value = result
            cm.bar_service.return_value = service

            # 不应抛（无论守卫还是 except 都 return None，但不应 raise 到调用方）
            order = sizer.cal(info, signal)

        assert order is None
