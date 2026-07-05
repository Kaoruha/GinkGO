# Issue: #5408 组件参数端点名称映射断裂，类名 vs 文件名导致全部 404
# Upstream: api.api.components.get_component_parameters / get_all_component_parameters
# Downstream: file_service.get_by_name / extract_component_parameters
# Role: 参数端点复用动态 AST 提取器(与 /components/{uuid} 同源)，废弃过时硬编码死表

"""
组件参数端点测试 (#5408)

实测确认的根因：
1. 路由顺序: api/api/components.py 中 /{uuid} 先声明，吞噬字面量
   /parameters 与 /parameters/{name}。
2. 数据源错接: /parameters 端点经 ComponentParameterService 查硬编码死表
   (COMPONENT_PARAMETER_DEFINITIONS, 10 个过时 PascalCase key，且与实际
   组件库脱节)；而组件实例化(ComponentLoader)与 /components/{uuid} 用的是
   动态 AST 提取器。两套不一致，前端拿文件名查死表必然 404/空。

修复方向：
1. /{uuid} 后置于 /parameters 之后（切片1，本文件）
2. 参数端点直接组合 file_service + extract_component_parameters（同源动态提取）
3. #5792 dashboard 单数→复数重定向（见 test_dashboard_5792.py）
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRouteOrderNotSwallowingParameters:
    """切片1: /{uuid} 不得吞噬 /parameters 字面量路由"""

    def test_get_all_parameters_returns_200_not_404(self):
        """GET /components/parameters 命中 get_all 端点(200)，而非被 /{uuid} 当 uuid 查成 404"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api import components

        app = FastAPI()
        app.include_router(components.router, prefix="/components")
        client = TestClient(app)

        # mock file_service: 若 /{uuid} 误吞 "parameters"，get_by_uuid 应失败得 404
        mock_result = MagicMock()
        mock_result.is_success.return_value = False  # 显式 False（MagicMock 默认 truthy 陷阱）
        mock_result.data = None
        mock_fs = MagicMock()
        mock_fs.get_by_uuid.return_value = mock_result

        with patch.object(components, "get_file_service", return_value=mock_fs):
            resp = client.get("/components/parameters")

        assert resp.status_code == 200, (
            f"应命中 get_all_component_parameters(200)，实际 {resp.status_code} " f"(疑似被 /{{uuid}} 路由吞掉)"
        )


class TestDynamicExtractionFromSource:
    """切片2: /parameters/{name} 从源码动态提取参数（与 /components/{uuid} 同源）"""

    def test_get_parameters_extracts_from_source_not_dead_table(self):
        """查死表里没有的组件名 → 应从源码动态提取，而非查过时硬编码表"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api import components

        # 假组件源码（类名含 component_name，确保 extract 能匹配到 __init__）
        fake_code = (
            "class FakeTestStrategy:\n"
            "    def __init__(self, buy_threshold=0.5, period=20):\n"
            "        self.buy_threshold = buy_threshold\n"
            "        self.period = period\n"
        )

        app = FastAPI()
        app.include_router(components.router, prefix="/components")
        client = TestClient(app)

        # get_by_name 返回 {files: [...]}（复数列表，注意非 get_by_uuid 的 file 单数）
        mock_file = MagicMock()
        mock_file.name = "fake_test_strategy"
        mock_file.type = 6  # FILE_TYPES.STRATEGY
        mock_file.uuid = "fake-uuid-1234"

        mock_name_result = MagicMock()
        mock_name_result.is_success.return_value = True
        mock_name_result.data = {"files": [mock_file], "count": 1}

        # get_content 返回 data=bytes（直接，不包 dict）
        mock_content_result = MagicMock()
        mock_content_result.is_success.return_value = True
        mock_content_result.data = fake_code.encode("utf-8")

        mock_fs = MagicMock()
        mock_fs.get_by_name.return_value = mock_name_result
        mock_fs.get_content.return_value = mock_content_result

        with patch.object(components, "get_file_service", return_value=mock_fs):
            resp = client.get("/components/parameters/fake_test_strategy")

        assert resp.status_code == 200, f"实际 {resp.status_code}: {resp.text}"
        param_names = [p["name"] for p in resp.json()["data"]]
        assert "buy_threshold" in param_names, f"应从源码提取，实际 {param_names}"
        assert "period" in param_names

    def test_get_all_parameters_extracts_from_source(self):
        """GET /components/parameters 返回所有组件动态提取的参数 dict（key=文件名）"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api import components

        code_a = "class FakeStratA:\n" "    def __init__(self, fast=5):\n" "        self.fast = fast\n"
        code_b = "class FakeStratB:\n" "    def __init__(self, slow=20):\n" "        self.slow = slow\n"

        mock_file_a = MagicMock()
        mock_file_a.name = "fake_strat_a"
        mock_file_a.type = 6
        mock_file_a.uuid = "uuid-a"

        mock_file_b = MagicMock()
        mock_file_b.name = "fake_strat_b"
        mock_file_b.type = 6
        mock_file_b.uuid = "uuid-b"

        mock_list_result = MagicMock()
        mock_list_result.is_success.return_value = True
        mock_list_result.data = {"data": [mock_file_a, mock_file_b], "total": 2}

        code_map = {"uuid-a": code_a.encode("utf-8"), "uuid-b": code_b.encode("utf-8")}

        def content_side_effect(file_id):
            r = MagicMock()
            r.is_success.return_value = True
            r.data = code_map[file_id]
            return r

        mock_fs = MagicMock()
        mock_fs.list_components.return_value = mock_list_result
        mock_fs.get_content.side_effect = content_side_effect

        app = FastAPI()
        app.include_router(components.router, prefix="/components")
        client = TestClient(app)

        with patch.object(components, "get_file_service", return_value=mock_fs):
            resp = client.get("/components/parameters")

        assert resp.status_code == 200, f"实际 {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "fake_strat_a" in data, f"key 应为文件名，实际 {list(data.keys())}"
        assert "fake_strat_b" in data
        assert any(p["name"] == "fast" for p in data["fake_strat_a"])


class TestBuiltinComponentParameterFallback:
    """#6085/#5758/#5836: DB 未同步内置组件时，参数端点仍应从源码发现内置组件。"""

    def test_get_all_parameters_falls_back_to_builtin_sources_when_db_empty(self):
        """GET /components/parameters 不应在 DB 为空时返回空系统。"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api import components

        mock_list_result = MagicMock()
        mock_list_result.is_success.return_value = True
        mock_list_result.data = {"data": [], "total": 0}

        mock_fs = MagicMock()
        mock_fs.list_components.return_value = mock_list_result

        app = FastAPI()
        app.include_router(components.router, prefix="/components")
        client = TestClient(app)

        with patch.object(components, "get_file_service", return_value=mock_fs):
            resp = client.get("/components/parameters")

        assert resp.status_code == 200, f"实际 {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "moving_average_crossover" in data
        assert any(p["name"] == "short_period" for p in data["moving_average_crossover"])

    def test_get_builtin_parameters_by_file_name_when_db_misses(self):
        """GET /components/parameters/{name} 应支持内置组件文件名查询。"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api import components

        mock_name_result = MagicMock()
        mock_name_result.is_success.return_value = False
        mock_name_result.data = None

        mock_fs = MagicMock()
        mock_fs.get_by_name.return_value = mock_name_result

        app = FastAPI()
        app.include_router(components.router, prefix="/components")
        client = TestClient(app)

        with patch.object(components, "get_file_service", return_value=mock_fs):
            resp = client.get("/components/parameters/moving_average_crossover")

        assert resp.status_code == 200, f"实际 {resp.status_code}: {resp.text}"
        param_names = [p["name"] for p in resp.json()["data"]]
        assert "short_period" in param_names
        assert "long_period" in param_names
