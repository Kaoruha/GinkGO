"""
VolumeActivate (成交量激活策略) 单元测试

覆盖范围:
- TestConstruction: 默认参数、自定义参数、无效参数验证
- TestCal: 成交量激增/萎缩触发、正常区间无信号、自定义阈值

Related: #5500
"""

import os
import sys

# 相对路径解析 src：worktree 内测 worktree 源码，合并后测主仓库源码
# （editable 安装锚定主仓库，须 sys.path.insert(0) 覆盖）
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), *([".."] * 4), "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from ginkgo.trading.strategies.volume_activate import StrategyVolumeActivate
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES


def _make_price_event(code: str = "000001.SZ"):
    """创建模拟的 EventPriceUpdate"""
    event = MagicMock(spec=EventPriceUpdate)
    event.code = code
    event.__class__ = EventPriceUpdate
    return event


def _make_portfolio_info(now: datetime = None):
    """创建模拟的 portfolio_info 字典"""
    if now is None:
        now = datetime(2024, 1, 20, 15, 0, 0)
    return {
        "uuid": "portfolio-001",
        "engine_id": "engine-001",
        "task_id": "run-001",
        "now": now,
        "interested_codes": ["000001.SZ"],
        "positions": {},
    }


def _bind_context(strategy):
    """绑定 portfolio/engine/task 上下文 + mock data_feeder"""
    ctx = MagicMock()
    ctx.portfolio_id = "portfolio-001"
    ctx.engine_id = "engine-001"
    ctx.task_id = "run-001"
    strategy._context = ctx
    strategy.bind_data_feeder(MagicMock())
    strategy.business_timestamp = datetime(2024, 1, 20, 15, 0, 0)
    return strategy


def _volume_df(volumes):
    """构造含 volume 列的历史 DataFrame"""
    return pd.DataFrame({"volume": volumes})


# ──────────────────────────────────────────────
# TestConstruction
# ──────────────────────────────────────────────

class TestConstruction:
    """VolumeActivate 构造与参数验证测试"""

    def test_default_params(self):
        """默认参数：volume_high=2.0, volume_low=0.5"""
        s = StrategyVolumeActivate()
        assert s._volume_high == 2.0
        assert s._volume_low == 0.5

    def test_custom_params(self):
        """自定义阈值参数"""
        s = StrategyVolumeActivate(volume_high=3.0, volume_low=0.3)
        assert s._volume_high == 3.0
        assert s._volume_low == 0.3

    def test_invalid_high_le_low_raises(self):
        """volume_high <= volume_low 应抛 ValueError"""
        with pytest.raises(ValueError, match="volume_high"):
            StrategyVolumeActivate(volume_high=0.5, volume_low=0.5)
        with pytest.raises(ValueError, match="volume_high"):
            StrategyVolumeActivate(volume_high=0.3, volume_low=0.5)

    def test_invalid_low_le_zero_raises(self):
        """volume_low <= 0 应抛 ValueError"""
        with pytest.raises(ValueError, match="volume_low"):
            StrategyVolumeActivate(volume_low=0)
        with pytest.raises(ValueError, match="volume_low"):
            StrategyVolumeActivate(volume_low=-0.1)


# ──────────────────────────────────────────────
# TestCal
# ──────────────────────────────────────────────

class TestCal:
    """VolumeActivate cal 方法核心逻辑测试"""

    def test_volume_surge_generates_long_signal(self):
        """#5500: 成交量激增（r > volume_high 默认 2.0）触发 LONG 信号。

        根因：原 ``if r < 0.67 and r > 0.6`` 是 0.07 宽的窄窗，几乎永不命中。
        修复后 r > volume_high 或 r < volume_low 触发。
        volume=[100,100,100,100,500] → mean=180, r≈2.78 > 2.0 → LONG。
        """
        s = _bind_context(StrategyVolumeActivate())
        portfolio_info = _make_portfolio_info()
        s.data_feeder.get_historical_data.return_value = _volume_df(
            [100, 100, 100, 100, 500]
        )

        result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.LONG

    def test_normal_volume_no_signal(self):
        """正常成交量（r ≈ 1.0，落在高低阈值之间）不触发信号。"""
        s = _bind_context(StrategyVolumeActivate())
        portfolio_info = _make_portfolio_info()
        s.data_feeder.get_historical_data.return_value = _volume_df(
            [100, 100, 100, 100, 100]
        )

        result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert result == []

    def test_empty_df_no_signal(self):
        """空 DataFrame（数据不足）不触发信号，不抛异常"""
        s = _bind_context(StrategyVolumeActivate())
        portfolio_info = _make_portfolio_info()
        s.data_feeder.get_historical_data.return_value = pd.DataFrame()

        result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert result == []

    def test_volume_collapse_generates_signal(self):
        """成交量萎缩（r < volume_low 默认 0.5）触发信号。

        volume=[100,100,100,100,30] → mean=86, r≈0.349 < 0.5 → 信号。
        """
        s = _bind_context(StrategyVolumeActivate())
        portfolio_info = _make_portfolio_info()
        s.data_feeder.get_historical_data.return_value = _volume_df(
            [100, 100, 100, 100, 30]
        )

        result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.LONG

    def test_custom_threshold_triggers(self):
        """自定义 volume_high=1.5：r≈1.67 > 1.5 触发信号。

        volume=[100,100,100,100,200] → mean=120, r≈1.667。
        """
        s = _bind_context(StrategyVolumeActivate(volume_high=1.5, volume_low=0.3))
        portfolio_info = _make_portfolio_info()
        s.data_feeder.get_historical_data.return_value = _volume_df(
            [100, 100, 100, 100, 200]
        )

        result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.LONG
