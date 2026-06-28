"""
Unit tests for RatioSizer — 组件边界契约：通过 _data_feeder 取价，不直访 container。

背景（#3877）：RatioSizer.cal LONG 分支曾直访 container.bar_service().get()，
绕过注入的 _data_feeder 接口，违反组件边界单向流动（Sizer 不应直访 data 层）。
对齐 FixedSizer 范式（tests/unit/trading/sizers/test_fixed_sizer.py）。
"""
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Signal
from ginkgo.trading.sizers.ratio_sizer import RatioSizer


@pytest.fixture
def sizer():
    s = RatioSizer(name="TestRatioSizer", ratio="0.1")
    # mock time provider，cal() 内 current_time = self.get_time_provider().now()
    tp = MagicMock()
    tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
    s._time_provider = tp
    return s


@pytest.fixture
def mock_feeder():
    return MagicMock()


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    s = Signal(code=code, direction=direction)
    s._portfolio_id = "test-portfolio"
    s._engine_id = "test-engine"
    return s


def _make_portfolio_info(cash=Decimal("500000"), positions=None):
    return {
        "cash": cash,
        "positions": positions or {},
    }


class TestRatioSizerUsesDataFeeder:
    """RatioSizer 应通过 _data_feeder 取价，不直访 container.bar_service（组件边界）。"""

    def test_long_uses_data_feeder_not_container(self, sizer, mock_feeder):
        """LONG 分支：价格经 _data_feeder.get_historical_data 获取，container.bar_service 不被调用。

        双重锁区分 bug（直访 container）与修复（走 feeder）：
        - 正向：mock_feeder.get_historical_data 被调用
        - 反向：container.bar_service 不被调用
        """
        df = pd.DataFrame({"close": [10.0, 10.5, 11.0]})
        mock_feeder.get_historical_data.return_value = df
        sizer._data_feeder = mock_feeder

        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=Decimal("500000"))

        # 反向锁：patch container 单例源对象的 bar_service。
        # 修复后 ratio_sizer 不再 import container，patch 单例属性对任意 import
        # 方式都成立；若 fix 被回退（直访 container），此 spy 会被调用 → 断言失败。
        from ginkgo.data.containers import container as _container_singleton
        with patch.object(_container_singleton, "bar_service") as mock_bar_service:
            order = sizer.cal(info, signal)

        # 正向锁：data_feeder 被调用
        mock_feeder.get_historical_data.assert_called_once()
        # 反向锁：container.bar_service 不应被直访（边界违规修复后）
        mock_bar_service.assert_not_called()
        # 端到端：订单成功生成
        assert order is not None
        assert order.direction == DIRECTION_TYPES.LONG
        assert order.volume > 0

    def test_long_no_data_feeder_returns_none(self, sizer):
        """LONG 分支：未绑定 _data_feeder 时 ERROR 返回 None，不崩。"""
        # 不绑定 feeder
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=Decimal("500000"))

        order = sizer.cal(info, signal)

        assert order is None
