# Issue: #5392 #5401 #5605
# Upstream: api.api.trading, ginkgo.enums
# Downstream: pytest
# Role: Paper Trading 账户状态读取修复 — 状态必须反映 DB portfolio.state，而非永远 "stopped"

"""
Paper Trading 状态读取测试

根因：_get_pt_status 读从不写入的 Redis key pt:status:{id}，永远 fallback "stopped"，
与 DB portfolio.state（worker deploy/unload 时更新）完全脱节。

修复：list/detail 端点改为读已持有的 portfolio.state，映射 RUNSTATE→前端字符串。
"""

import pytest
from types import SimpleNamespace


class TestMapPtStatus:
    """验证 portfolio.state → 前端 status 字符串的映射"""

    def test_running_state_returns_running(self):
        """#5392 #5401: portfolio 处于 RUNNING 时，status 必须是 'running'（不再永远 stopped）"""
        from api.trading import _map_pt_status
        from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

        portfolio = SimpleNamespace(state=PORTFOLIO_RUNSTATE_TYPES.RUNNING)
        assert _map_pt_status(portfolio) == "running"

    def test_stopped_state_returns_stopped(self):
        """#5392 #5401: STOPPED/INITIALIZED/OFFLINE 等终态必须映射为 'stopped'"""
        from api.trading import _map_pt_status
        from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

        for terminal in (PORTFOLIO_RUNSTATE_TYPES.STOPPED,
                         PORTFOLIO_RUNSTATE_TYPES.INITIALIZED,
                         PORTFOLIO_RUNSTATE_TYPES.OFFLINE):
            assert _map_pt_status(SimpleNamespace(state=terminal)) == "stopped"

    def test_transition_states_still_running(self):
        """PAUSED/STOPPING/RELOADING 等过渡态：账户仍在 worker 内，对前端是 'running'"""
        from api.trading import _map_pt_status
        from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

        for trans in (PORTFOLIO_RUNSTATE_TYPES.PAUSED,
                      PORTFOLIO_RUNSTATE_TYPES.STOPPING,
                      PORTFOLIO_RUNSTATE_TYPES.MIGRATING):
            assert _map_pt_status(SimpleNamespace(state=trans)) == "running"

    def test_unknown_state_returns_error(self):
        """None 或未识别状态必须 fail-fast 返回 'error'，而非静默 'stopped'（掩盖 bug）"""
        from api.trading import _map_pt_status

        assert _map_pt_status(SimpleNamespace(state=None)) == "error"
        assert _map_pt_status(SimpleNamespace()) == "error"

    def test_int_state_value_normalized(self):
        """DB 枚举字段常以裸 int 返回（如 1=RUNNING），必须规范化后映射，否则端点层永远 error"""
        from api.trading import _map_pt_status
        from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

        running_int = PORTFOLIO_RUNSTATE_TYPES.RUNNING.value
        assert isinstance(running_int, int)
        assert _map_pt_status(SimpleNamespace(state=running_int)) == "running"


class TestStartReturnsCurrentStatus:
    """#5401: start 即发即忘，返回必须含当前真实状态，避免前端误判已启动"""

    def test_start_returns_current_status_not_running(self, monkeypatch):
        """worker 尚未处理 deploy，state 仍 INITIALIZED；返回应诚实反映 stopped，而非假装 running"""
        import asyncio
        from api import trading
        from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

        portfolio = SimpleNamespace(uuid="acc-1",
                                    state=PORTFOLIO_RUNSTATE_TYPES.INITIALIZED)

        # #6095 review: 真实 PortfolioService.get 经 _crud_repo.find 返回的是 list，
        # FakeResult.data 必须是 list 形状，否则测试退化成"测 mock"而非"测生产契约"。
        # 旧实现 FakeResult.data = portfolio（单对象）掩盖了 start 端点未解包 list 的 bug。
        class FakeResult:
            data = [portfolio]
            def is_success(self): return True

        class FakeSvc:
            def get(self, portfolio_id): return FakeResult()

        class FakeProducer:
            def send(self, *a, **k): return True

        monkeypatch.setattr(trading, "_get_portfolio_service", lambda: FakeSvc())
        monkeypatch.setattr(trading, "_get_kafka_producer", lambda: FakeProducer())

        resp = asyncio.run(trading.start_paper_trading("acc-1", None))

        assert resp["code"] == 0
        assert resp["data"]["success"] is True
        # 关键：current_status 反映 DB 真实状态（INITIALIZED→stopped），非误导性 "running"
        assert resp["data"]["current_status"] == "stopped"
        # 消息必须诚实说明异步性，不再宣称"已启动"
        assert "asynchronously" in resp["message"].lower()
