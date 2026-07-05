# Issue #5827: component list API must include built-in trading components.

import asyncio
import pytest
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

    def test_builtin_components_paginate_across_pages(self):
        """DB 空 + page_size=10：page>=2 必须返回不同组件，且多页累计可见数 == total（#4566 双契约）。"""
        from api.components import list_components

        seen = {}
        for p in [1, 2, 3, 4, 5, 6]:
            mock_service = MagicMock()
            mock_service.list_components.return_value = make_mock_result()
            with patch("api.components.get_file_service", return_value=mock_service):
                result = run_async(list_components(page=p, page_size=10))
            seen[p] = [item["name"] for item in result["data"]]

        # 跨页不重复
        assert seen[1] != seen[2], f"page1==page2 跨页重复: {seen[1]}"

        # 累计可见数 == total（翻页能遍历全部，无遗漏无重复）
        all_names = set()
        for names in seen.values():
            all_names.update(names)
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result()
        with patch("api.components.get_file_service", return_value=mock_service):
            total = run_async(list_components(page=1, page_size=10))["meta"]["total"]
        assert len(all_names) == total, f"6 页可见 {len(all_names)} != total {total}"

    def test_builtin_discovery_excludes_test_fixtures_and_placeholders(self):
        """#5827: 发现规则不暴露测试夹具（simple_test_strategy）与无类占位（moving_loss_limit/price_action）。"""
        from api.components import list_components

        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result()
        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(page=1, page_size=200))

        names = {item["name"] for item in result["data"]}
        # simple_test_strategy：测试夹具（文件名含 test）
        assert "simple_test_strategy" not in names
        # moving_loss_limit / price_action：无 class 定义的占位文件（纯注释）
        assert "moving_loss_limit" not in names
        assert "price_action" not in names
        # 真实内置策略仍可被发现
        assert "dual_thrust" in names
        assert "moving_average_crossover" in names


class TestBuiltinComponentDetail:
    """#5827 review③: GET /components/{uuid} 识别 builtin: 前缀，回源码读详情，不 404。"""

    def test_get_builtin_component_by_uuid_returns_detail(self):
        from api.components import get_component

        mock_service = MagicMock()
        with patch("api.components.get_file_service", return_value=mock_service):
            data = run_async(get_component("builtin:strategy:dual_thrust"))["data"]

        assert data["name"] == "dual_thrust"
        assert data["component_type"] == "strategy"
        assert data["code"]  # 源码非空
        assert data["uuid"] == "builtin:strategy:dual_thrust"
        # builtin 路径不查 DB
        mock_service.get_by_uuid.assert_not_called()

    def test_get_builtin_component_unknown_returns_404(self):
        from fastapi import HTTPException
        from api.components import get_component

        mock_service = MagicMock()
        with patch("api.components.get_file_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(get_component("builtin:strategy:nonexistent_xyz"))
        assert exc.value.status_code == 404


class TestBuiltinComponentParameters:
    """#5827 review③: GET /components/parameters/{name} 对内置组件名回源码读参数，不 404。"""

    def test_get_parameters_for_builtin_name_does_not_404(self):
        from api.components import get_component_parameters

        mock_service = MagicMock()
        miss = MagicMock()
        miss.is_success.return_value = True
        miss.data = {"files": []}
        mock_service.get_by_name.return_value = miss

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(get_component_parameters("dual_thrust"))

        assert "data" in result  # 端点可达，不 404

    def test_get_parameters_for_unknown_name_returns_404(self):
        from fastapi import HTTPException
        from api.components import get_component_parameters

        mock_service = MagicMock()
        miss = MagicMock()
        miss.is_success.return_value = True
        miss.data = {"files": []}
        mock_service.get_by_name.return_value = miss

        with patch("api.components.get_file_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(get_component_parameters("nonexistent_xyz"))
        assert exc.value.status_code == 404
