"""ADR-021 L139: service 层 page_size 透传 smoke。

#6685 diff coverage gate 只采集 smoke 子集的 coverage.json。CLI ``--limit``
下推到 service 的 3 个出口方法（engine get_engines_df / fuzzy_search、
portfolio get_portfolios_df）是本 PR 新增可执行行，containers import 链
虽触达这些 service（class 定义行 executed → 非 exempt）但 smoke 不调用其
方法体，函数体内 page_size 透传行无覆盖信号。本文件用 mock 依赖（不连 DB）
补足该信号，纳入 smoke 子集供门禁测量。
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.portfolio_service import PortfolioService


@pytest.fixture
def engine_service():
    with patch("ginkgo.libs.GLOG"):
        return EngineService(
            crud_repo=MagicMock(),
            engine_portfolio_mapping_crud=MagicMock(),
            param_crud=MagicMock(),
        )


@pytest.fixture
def portfolio_service():
    with patch("ginkgo.libs.GLOG"):
        return PortfolioService(
            crud_repo=MagicMock(),
            portfolio_file_mapping_crud=MagicMock(),
        )


class TestPageSizePassthrough:
    """page_size 透传 crud（供 CLI --limit 下推，ADR-021 L139）。"""

    @pytest.mark.unit
    def test_engine_get_engines_df_passes_page_size_to_find(self, engine_service):
        """engine.get_engines_df(page_size=) → crud.find(page_size=)。"""
        engine_service._crud_repo.find.return_value = MagicMock()

        result = engine_service.get_engines_df(page_size=10)

        assert result.success is True
        assert engine_service._crud_repo.find.call_args[1]["page_size"] == 10

    @pytest.mark.unit
    def test_engine_fuzzy_search_passes_page_size_as_limit(self, engine_service):
        """engine.fuzzy_search(page_size=) → crud.fuzzy_search(limit=)。"""
        engine_service._crud_repo.fuzzy_search.return_value = MagicMock()

        result = engine_service.fuzzy_search(query="momentum", page_size=10)

        assert result.success is True
        assert engine_service._crud_repo.fuzzy_search.call_args[1]["limit"] == 10

    @pytest.mark.unit
    def test_portfolio_get_portfolios_df_passes_page_size_to_find(self, portfolio_service):
        """portfolio.get_portfolios_df(page_size=) → crud.find(page_size=)。"""
        portfolio_service._crud_repo.find.return_value = MagicMock()

        result = portfolio_service.get_portfolios_df(page_size=10)

        assert result.success is True
        assert portfolio_service._crud_repo.find.call_args[1]["page_size"] == 10
