"""Arena portfolio 列表端点测试 (#5861)

验证 GET /api/v1/arena/portfolios 返回 501 Not Implemented。

#5861 AC#1：Arena 端点要么实现要么返回 501。竞技场 portfolio 集合的
业务语义未定义（哪些 portfolio 参与竞技场），当前以 501 诚实标记
未实现，不返 {"items": []} 空数据伪装"已实现但无数据"。
"""
import asyncio

import pytest


class TestArenaPortfoliosNotImplemented:
    """#5861 AC#1: GET /arena/portfolios 返回 501（非空 stub 伪装）"""

    def test_returns_501(self, api_modules):
        """未实现时返回 501，不返空列表 stub 伪装已实现"""
        from fastapi import HTTPException
        from api.arena import get_arena_portfolios

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_arena_portfolios())
        assert exc.value.status_code == 501

    def test_detail_indicates_not_implemented(self, api_modules):
        """501 detail 明确标记未实现（消费者可区分'无数据'vs'未实现'）"""
        from fastapi import HTTPException
        from api.arena import get_arena_portfolios

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_arena_portfolios())
        assert "not implemented" in exc.value.detail.lower()
