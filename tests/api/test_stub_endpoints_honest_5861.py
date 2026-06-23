# Issue: #5861 stub 端点返假数据 → 改诚实信号（501 / implemented 标记）
# Upstream: api.api.arena / api.api.settings
# Role: 未实现端点返 501，mock 端点标记 implemented:false，消除假数据误导

"""
#5861 端点诚实信号测试

验证：
1. Arena 端点（完全 TODO stub）返回 501 Not Implemented，而非假空数据
2. API Stats（硬编码 mock）保留结构但标记 implemented:false，前端不破坏
3. User Groups / Notification Recipients 已接线（非 stub），不在本测试范围
"""

import asyncio
import pytest
from fastapi import HTTPException


def run_async(coro):
    return asyncio.run(coro)


class TestArenaStubReturns501:
    """Arena 2 端点是完全 TODO stub（前端无依赖），应返 501 而非假装成功的空数据"""

    def test_arena_portfolios_returns_501(self):
        from api.arena import get_arena_portfolios
        with pytest.raises(HTTPException) as exc:
            run_async(get_arena_portfolios())
        assert exc.value.status_code == 501

    def test_arena_comparison_returns_501(self):
        from api.arena import get_arena_comparison
        with pytest.raises(HTTPException) as exc:
            run_async(get_arena_comparison())
        assert exc.value.status_code == 501


class TestApiStatsHonestMarker:
    """API Stats 硬编码 mock（前端 settings.ts:446 有依赖），
    保留结构不破坏前端，但加 implemented:false 标记消除 99.8% 假统计误导"""

    def test_api_stats_marks_not_implemented(self):
        from api.settings import get_api_stats
        resp = run_async(get_api_stats())
        assert resp["data"]["implemented"] is False
        # 保留原有字段结构（前端兼容）
        assert "today_calls" in resp["data"]
