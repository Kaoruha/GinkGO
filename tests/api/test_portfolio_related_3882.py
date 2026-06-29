"""
#3882: _get_related_portfolios 消费 find_by_source/target_portfolio 的 dict 返回。

验证 dict 访问路径（dep["target_portfolio_id"] / deployments[0]["source_portfolio_id"]）
在 BACKTEST 与 PAPER/LIVE 两分支均正确提取——防止回退到属性访问（[[arch_service_dict_wrapped_return]]）。
"""

import sys
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_path = os.path.join(os.path.dirname(__file__), '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.base_service import ServiceResult


def _portfolio_model(uuid: str, mode: int = 1, state: str = "READY"):
    return SimpleNamespace(
        uuid=uuid,
        name=f"name-{uuid}",
        mode=mode,
        state=state,
        annual_return=0.12,
        max_drawdown=0.05,
    )


class TestGetRelatedPortfoliosBacktestMode:
    """BACKTEST(mode=0)：find_by_source_portfolio 返 dict 列表，提取 deployed PAPER/LIVE。"""

    @pytest.mark.unit
    @patch("api.portfolio._map_state", return_value="READY")
    @patch("api.portfolio.get_portfolio_service")
    @patch("api.portfolio._get_deployment_service")
    def test_extracts_target_from_dict(self, mock_dep_svc, mock_port_svc, _map_state):
        from api.portfolio import _get_related_portfolios

        deployment_svc = MagicMock()
        deployment_svc.find_by_source_portfolio.return_value = ServiceResult.success(
            data=[{"deployment_id": "d1", "target_portfolio_id": "pf-tgt", "source_portfolio_id": "pf-src"}]
        )
        mock_dep_svc.return_value = deployment_svc

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=[_portfolio_model("pf-tgt", mode=1)])
        mock_port_svc.return_value = portfolio_svc

        related = _get_related_portfolios("pf-src", mode_int=0)

        assert len(related) == 1
        assert related[0]["uuid"] == "pf-tgt"
        assert related[0]["mode"] == "PAPER"
        # 验证 dict 访问而非属性访问：deployment_svc 收到的 target_portfolio_id 是 dict key 的值
        _, kwargs = portfolio_svc.get.call_args
        assert kwargs["portfolio_id"] == "pf-tgt"


class TestGetRelatedPortfoliosPaperMode:
    """PAPER/LIVE(mode!=0)：find_by_target_portfolio 返 dict 列表，提取 source BACKTEST。"""

    @pytest.mark.unit
    @patch("api.portfolio._get_latest_backtest_metrics", return_value={})
    @patch("api.portfolio._map_state", return_value="READY")
    @patch("api.portfolio.get_portfolio_service")
    @patch("api.portfolio._get_deployment_service")
    def test_extracts_source_from_dict(self, mock_dep_svc, mock_port_svc, _map_state, _bt_metrics):
        from api.portfolio import _get_related_portfolios

        deployment_svc = MagicMock()
        deployment_svc.find_by_target_portfolio.return_value = ServiceResult.success(
            data=[{"deployment_id": "d1", "source_portfolio_id": "pf-src", "target_portfolio_id": "pf-cur"}]
        )
        mock_dep_svc.return_value = deployment_svc

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=[_portfolio_model("pf-src", mode=0)])
        mock_port_svc.return_value = portfolio_svc

        related = _get_related_portfolios("pf-cur", mode_int=1)

        assert len(related) >= 1
        source_entry = next(r for r in related if r.get("relation") == "source")
        assert source_entry["uuid"] == "pf-src"
        assert source_entry["mode"] == "BACKTEST"
        # dict 访问：source_id 来自 deployments[0]["source_portfolio_id"]
        first_call_args = portfolio_svc.get.call_args_list[0]
        assert first_call_args.kwargs["portfolio_id"] == "pf-src"
