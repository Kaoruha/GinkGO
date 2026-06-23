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


# #5860 取代 #5401 对 start 端点的处理：端点废弃为 410 Gone（原 success+current_status
# 返回行为已移除）。start 废弃语义测试迁移至 test_paper_trading_start_deprecated_5860.py。
# TestMapPtStatus（_map_pt_status 映射）保留——仍用于 get/list 端点（#5392 未受 #5860 影响）。
