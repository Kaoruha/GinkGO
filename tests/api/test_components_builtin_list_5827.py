# Issue #5827: component list API must include built-in trading components.

import asyncio
from unittest.mock import MagicMock, patch


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(total=0, rows=None):
    result = MagicMock()
    result.is_success.return_value = True
    result.data = {"data": rows or [], "total": total}
    return result


class TestComponentsBuiltins:
    def test_empty_db_still_returns_builtin_trading_components(self):
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result()

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(page=1, page_size=100))

        names = {item["name"] for item in result["data"]}
        types = {item["component_type"] for item in result["data"]}

        assert "moving_average_crossover" in names
        assert "cn_all_selector" in names
        assert "fixed_sizer" in names
        assert "no_risk" in names
        assert {"strategy", "selector", "sizer", "risk"}.issubset(types)
        assert result["meta"]["total"] >= 4

    def test_component_type_filter_applies_to_builtin_components(self):
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result()

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(component_type="selector", page=1, page_size=100))

        assert {item["component_type"] for item in result["data"]} == {"selector"}
        assert "cn_all_selector" in {item["name"] for item in result["data"]}

    def test_name_filter_applies_to_builtin_components(self):
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result()

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(name="moving_average", page=1, page_size=100))

        names = {item["name"] for item in result["data"]}
        assert "moving_average_crossover" in names
        assert "random_signal_strategy" not in names
