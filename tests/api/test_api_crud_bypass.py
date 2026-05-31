"""
Tests for API→CRUD bypass elimination (#4582).

Verifies that API layer uses Service methods instead of directly
accessing CRUD instances (_crud_repo, _result_crud, container.analyzer_record_crud()).

Issue: #4582
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


def _repo_root() -> Path:
    """Get repo root (works in worktree too)."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(result.stdout.strip())


_API_ROOT = _repo_root() / "api" / "api"


def _read_api_source(filename: str) -> str:
    """Read API source file, stripping comments."""
    lines = (_API_ROOT / filename).read_text().splitlines()
    # Remove comment lines (which may reference the banned pattern in docs)
    return "\n".join(line for line in lines if not line.strip().startswith("#"))


# ── Slice 1: PortfolioService.list_paginated ──────────────────────────


class TestPortfolioServiceListPaginated:
    """PortfolioService.list_paginated should wrap CRUD find+count."""

    def test_returns_service_result_with_items_and_total(self):
        """list_paginated returns ServiceResult with items list and total count."""
        from ginkgo.data.services.portfolio_service import PortfolioService

        mock_crud = MagicMock()
        mock_crud.find.return_value = [MagicMock(uuid="p1"), MagicMock(uuid="p2")]
        mock_crud.count.return_value = 2

        svc = PortfolioService(
            crud_repo=mock_crud,
            portfolio_file_mapping_crud=MagicMock(),
        )
        result = svc.list_paginated(
            filters={"name": "test"},
            page=1,
            page_size=20,
            order_by="update_at",
            desc_order=True,
        )

        assert isinstance(result, ServiceResult)
        assert result.success
        assert result.data["total"] == 2
        assert len(result.data["items"]) == 2
        mock_crud.find.assert_called_once_with(
            filters={"name": "test"},
            page=1,
            page_size=20,
            order_by="update_at",
            desc_order=True,
        )
        mock_crud.count.assert_called_once_with(filters={"name": "test"})


class TestPortfolioApiNoCrudBypass:
    """api/api/portfolio.py must not access portfolio_service._crud_repo."""

    def test_no_crud_repo_access(self):
        source = _read_api_source("portfolio.py")
        assert "_crud_repo" not in source, (
            "portfolio.py still accesses _crud_repo directly"
        )


# ── Slice 2: AnalyzerService.find_by_portfolio ────────────────────────


class TestAnalyzerServiceFindByPortfolio:
    """AnalyzerService.find_by_portfolio should delegate to CRUD."""

    def test_returns_service_result_with_records(self):
        from ginkgo.data.services.analyzer_service import AnalyzerService

        mock_crud = MagicMock()
        mock_crud.find_by_portfolio.return_value = [MagicMock(name="net_value")]

        svc = AnalyzerService(analyzer_crud=mock_crud)
        result = svc.find_by_portfolio(
            portfolio_id="pf-1", task_id="task-1"
        )

        assert isinstance(result, ServiceResult)
        assert result.success
        assert len(result.data) == 1
        mock_crud.find_by_portfolio.assert_called_once_with(
            portfolio_id="pf-1", analyzer_name=None,
            task_id="task-1", start_date=None, end_date=None,
        )


class TestBacktestApiNoCrudBypass:
    """api/api/backtest.py must not call container.analyzer_record_crud()."""

    def test_no_analyzer_record_crud_access(self):
        source = _read_api_source("backtest.py")
        assert "analyzer_record_crud" not in source, (
            "backtest.py still directly calls container.analyzer_record_crud()"
        )


# ── Slice 3: ValidationService.list_results + get_result ──────────────


class TestValidationServiceListResults:
    """ValidationService.list_results should wrap CRUD find+count."""

    def test_returns_service_result_with_items_and_total(self):
        from ginkgo.data.services.validation_service import ValidationService

        mock_result_crud = MagicMock()
        mock_result_crud.find.return_value = [MagicMock(uuid="r1")]
        mock_result_crud.count.return_value = 1

        svc = ValidationService(
            analyzer_record_crud=MagicMock(),
            validation_result_crud=mock_result_crud,
        )
        result = svc.list_results(
            portfolio_id="pf-1", method="segment_stability",
            page=0, page_size=20,
        )

        assert isinstance(result, ServiceResult)
        assert result.success
        assert result.data["total"] == 1
        assert len(result.data["items"]) == 1


class TestValidationServiceGetResult:
    """ValidationService.get_result should wrap CRUD get."""

    def test_returns_service_result_with_record(self):
        from ginkgo.data.services.validation_service import ValidationService

        mock_record = MagicMock(uuid="r-1", task_id="t-1")
        mock_result_crud = MagicMock()
        mock_result_crud.get.return_value = mock_record

        svc = ValidationService(
            analyzer_record_crud=MagicMock(),
            validation_result_crud=mock_result_crud,
        )
        result = svc.get_result("r-1")

        assert isinstance(result, ServiceResult)
        assert result.success
        assert result.data == mock_record
        mock_result_crud.get.assert_called_once_with("r-1")


class TestValidationApiNoCrudBypass:
    """api/api/validation.py must not access svc._result_crud."""

    def test_no_result_crud_access(self):
        source = _read_api_source("validation.py")
        assert "_result_crud" not in source, (
            "validation.py still accesses _result_crud directly"
        )
