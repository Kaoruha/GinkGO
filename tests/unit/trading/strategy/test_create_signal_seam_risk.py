"""
RiskBase.create_signal 信号发射 seam 测试（ADR-011, #6160）

验证深化后的 Risk seam（镜像 Strategy S1）：
- 构造 Signal（填 portfolio/engine/task_id）—— 契约不变
- business_timestamp：缺省 get_time_provider().now()，provider 未绑定留 None，
  调用方传值时覆盖（不查 provider）
- source：缺省 SOURCE_TYPES.RISK，可覆盖（值归组件原则）
- ClickHouse 日志：无条件 blog.signal(strategy_id=self.uuid) 恰调一次
  注：blog 的 strategy_id 参数名历史沿用，语义泛指"信号生成组件 uuid"（Strategy/Risk 共用）；
  Strategy 与 Risk 的来源区分由 Signal.source（STRATEGY/RISK）承担。
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.entities.signal import Signal
from ginkgo.entities.mixins.context_mixin import ContextMixin
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


def _make_risk():
    """构造一个带上下文 ID、无 time_provider 的 RiskBase。"""
    r = RiskBase(name="RiskSeamTest")
    r._context = type('C', (), {
        'engine_id': 'e', 'portfolio_id': 'p', 'task_id': 't',
    })()
    return r


@pytest.mark.unit
class TestCreateSignalRiskSource:
    """source 字段：缺省 RISK，可覆盖（值归组件原则）。"""

    def test_source_defaults_to_risk(self):
        r = _make_risk()
        sig = r.create_signal(code="000001", direction=DIRECTION_TYPES.LONG, reason="r")
        assert sig.source == SOURCE_TYPES.RISK

    def test_source_overridable(self):
        r = _make_risk()
        sig = r.create_signal(
            code="000001", direction=DIRECTION_TYPES.LONG, reason="r",
            source=SOURCE_TYPES.STRATEGY,
        )
        assert sig.source == SOURCE_TYPES.STRATEGY


@pytest.mark.unit
class TestCreateSignalRiskTimestamp:
    """business_timestamp：provider 缺省留 None、有则取 now()、调用方覆盖优先。"""

    def test_timestamp_none_when_no_provider(self):
        r = _make_risk()
        assert r._time_provider is None
        sig = r.create_signal(code="000001", direction=DIRECTION_TYPES.LONG, reason="r")
        assert sig.business_timestamp is None

    def test_timestamp_from_provider_when_set(self):
        r = _make_risk()
        fixed = datetime(2025, 6, 14, 10, 0)
        provider = MagicMock()
        provider.now.return_value = fixed
        r._time_provider = provider
        sig = r.create_signal(code="000001", direction=DIRECTION_TYPES.LONG, reason="r")
        assert sig.business_timestamp == fixed
        provider.now.assert_called_once()

    def test_timestamp_overridable_beats_provider(self):
        r = _make_risk()
        provider = MagicMock()
        provider.now.return_value = datetime(2025, 6, 14)
        r._time_provider = provider
        override = datetime(2024, 1, 1)
        sig = r.create_signal(
            code="000001", direction=DIRECTION_TYPES.LONG, reason="r",
            business_timestamp=override,
        )
        assert sig.business_timestamp == override
        provider.now.assert_not_called()


@pytest.mark.unit
class TestCreateSignalRiskBlog:
    """无条件 ClickHouse 信号日志（框架基础设施，ADR-011）。"""

    def test_blog_signal_called_once_with_component_uuid(self, monkeypatch):
        mock_blog = MagicMock()
        monkeypatch.setattr(ContextMixin, 'blog', mock_blog)
        r = _make_risk()
        r.create_signal(code="000001", direction=DIRECTION_TYPES.LONG, reason="block")
        mock_blog.signal.assert_called_once()
        kwargs = mock_blog.signal.call_args.kwargs
        # strategy_id 参数名历史沿用，泛指信号生成组件 uuid（Risk 复用）
        assert kwargs['strategy_id'] == r.uuid

    def test_blog_signal_receives_symbol_direction_reason(self, monkeypatch):
        mock_blog = MagicMock()
        monkeypatch.setattr(ContextMixin, 'blog', mock_blog)
        r = _make_risk()
        r.create_signal(code="000001", direction=DIRECTION_TYPES.LONG, reason="stop_loss")
        kwargs = mock_blog.signal.call_args.kwargs
        assert kwargs['symbol'] == "000001"
        assert kwargs['direction'] == DIRECTION_TYPES.LONG.value
        assert kwargs['signal_reason'] == "stop_loss"


@pytest.mark.unit
class TestCreateSignalRiskContract:
    """构造契约不变：上下文 ID 填充 + 业务参数透传 + 返回 Signal。"""

    def test_signal_carries_context_ids(self):
        r = _make_risk()
        sig = r.create_signal(code="000001", direction=DIRECTION_TYPES.LONG, reason="r")
        assert isinstance(sig, Signal)
        assert sig.portfolio_id == 'p'
        assert sig.engine_id == 'e'
        assert sig.task_id == 't'

    def test_business_params_propagated(self):
        r = _make_risk()
        sig = r.create_signal(
            code="000001", direction=DIRECTION_TYPES.SHORT,
            reason="r", volume=100, weight=0.5, strength=0.8, confidence=0.9,
        )
        assert sig.volume == 100
        assert sig.weight == 0.5
        assert sig.strength == 0.8
        assert sig.confidence == 0.9
