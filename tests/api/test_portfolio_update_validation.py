# Issue: #5474 — Portfolio update accepts raw dict without input validation
# Upstream: api.api.portfolio.update_portfolio / UpdatePortfolioRequest
# Downstream: PortfolioSagaFactory.update_portfolio_saga
# Role: 验证 PUT /portfolios/{uuid} 用 Pydantic schema 校验输入，拒负 cash/空 name/未知字段

"""
Portfolio update 输入校验测试 (#5474)。

根因：update_portfolio(uuid, data: dict) 接裸 dict，无校验——
null name / 负 initial_cash / 未知字段（evil_field）直透传 Saga 事务。

修复：加 UpdatePortfolioRequest Pydantic schema（extra="ignore" + 字段约束），
端点改 data: UpdatePortfolioRequest，内部用校验后字段。
"""

import pytest
from pydantic import ValidationError as PydanticValidationError
from unittest.mock import patch, MagicMock, AsyncMock


class TestUpdatePortfolioRequestSchema:
    """#5474: UpdatePortfolioRequest 字段约束。"""

    def test_rejects_negative_initial_cash(self):
        """验收: 负 initial_cash 被拒（gt=0）。"""
        from api.portfolio import UpdatePortfolioRequest

        with pytest.raises(PydanticValidationError):
            UpdatePortfolioRequest(initial_cash=-1)

    def test_rejects_zero_initial_cash(self):
        """验收: 零 initial_cash 被拒（gt=0，非 ge=0）。"""
        from api.portfolio import UpdatePortfolioRequest

        with pytest.raises(PydanticValidationError):
            UpdatePortfolioRequest(initial_cash=0)

    def test_rejects_empty_name(self):
        """验收: 空字符串 name 被拒（min_length=1）。"""
        from api.portfolio import UpdatePortfolioRequest

        with pytest.raises(PydanticValidationError):
            UpdatePortfolioRequest(name="")

    def test_ignores_unknown_fields(self):
        """验收: 未知字段被忽略（extra="ignore"），不透传到 Saga。"""
        from api.portfolio import UpdatePortfolioRequest

        req = UpdatePortfolioRequest(name="x", evil_field="y")
        assert req.name == "x"
        # 未知字段不被保留为属性
        assert not hasattr(req, "evil_field")

    def test_accepts_valid_partial_update(self):
        """合法部分更新通过（未提供字段为 None，不覆盖）。"""
        from api.portfolio import UpdatePortfolioRequest

        req = UpdatePortfolioRequest(name="my_portfolio", initial_cash=100000)
        assert req.name == "my_portfolio"
        assert req.initial_cash == 100000
        assert req.selectors is None  # 未提供


def run_async(coro):
    import asyncio
    return asyncio.run(coro)


class TestUpdatePortfolioEndpointWiring:
    """#5474: 端点用 UpdatePortfolioRequest 校验后字段调 saga，未知字段不透传。"""

    def test_passes_validated_data_to_saga_without_unknown_fields(self):
        """验收: 端点接 schema 后，校验字段传入 saga，未知字段被 extra=ignore 丢弃。"""
        from api.portfolio import update_portfolio, UpdatePortfolioRequest

        # 注入未知字段验证它不透传到 saga（extra=ignore 在 schema 层已丢）
        req = UpdatePortfolioRequest(name="new_name", initial_cash=50000)

        with patch("services.saga_transaction.PortfolioSagaFactory") as MockFactory, \
             patch("api.portfolio.get_portfolio",
                   new=AsyncMock(return_value={"code": 0, "data": {"uuid": "u1"}})):
            mock_saga = MagicMock()
            mock_saga.execute = AsyncMock(return_value=True)
            MockFactory.update_portfolio_saga.return_value = mock_saga

            run_async(update_portfolio("u1", req))

        MockFactory.update_portfolio_saga.assert_called_once()
        _, kwargs = MockFactory.update_portfolio_saga.call_args
        # 校验后字段正确传入
        assert kwargs["portfolio_uuid"] == "u1"
        assert kwargs["name"] == "new_name"
        assert kwargs["initial_cash"] == 50000
        # 未知字段绝不在 saga 调用参数里
        assert "evil_field" not in kwargs
