"""#5567: components 端点 500 响应不泄露 str(e) 内部细节。

FastAPI 默认 HTTPException handler 精确匹配优先于全局 Exception handler，
raise HTTPException(500, detail=f"...{str(e)}") 会把 SQL/traceback/连接串
直接返回客户端。修复：detail 改 generic，异常详情已在 logger.error 记录。

参考 [[arch_global_error_handler_trace_id]]：global_error_handler 的
isinstance(HTTPException) 分支是死代码（HTTPException 走 Starlette 默认 handler），
所以端点必须在 raise 前自行脱敏。
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# conftest 的 api_modules autouse fixture 是 session scope，但模块级 import 先于
# fixture 激活。自行 insert api/ 和 api/api/ 确保 from components 可导入
# （参考 test_node_graph_file_type.py 的自 insert 范式，对齐 [[arch_api_test_import_collapse]]）。
_api_dir = str(Path(__file__).parent.parent.parent / "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)
_api_api_dir = str(Path(_api_dir) / "api")
if _api_api_dir not in sys.path:
    sys.path.insert(0, _api_api_dir)

# #5464: config.py 全局 Settings() 需合法 SECRET_KEY
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

from components import (  # noqa: E402
    ComponentCreate,
    create_component,
    delete_component,
    get_component,
    get_component_parameters,
    list_components,
    update_component,
)

# 模拟内部异常细节（SQL/表名/连接串/IP）——这些绝不应出现在 500 响应里
SENSITIVE = "SQL: SELECT * FROM secret_internal_table; conn=postgres://u:p@10.0.0.1/db"


def _raise_sensitive(*_a, **_kw):
    raise RuntimeError(SENSITIVE)


class TestListComponentsSanitization:
    """list_components 500 响应 detail 不含异常内部细节。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.list_components.side_effect = _raise_sensitive
        with patch("components.get_file_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(list_components(page=1, page_size=20))

        assert exc.value.status_code == 500
        # 不泄露 SQL/连接串/内部表名/IP
        assert "SQL" not in exc.value.detail
        assert "secret_internal_table" not in exc.value.detail
        assert "postgres" not in exc.value.detail
        assert "10.0.0.1" not in exc.value.detail
        # generic 消息（无 str(e) 后缀）
        assert exc.value.detail == "Failed to list components"


class TestGetComponentSanitization:
    """get_component 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_by_uuid.side_effect = _raise_sensitive
        with patch("components.get_file_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_component("some-uuid"))

        assert exc.value.status_code == 500
        assert "SQL" not in exc.value.detail
        assert exc.value.detail == "Failed to get component"


class TestUpdateComponentSanitization:
    """update_component 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.update.side_effect = _raise_sensitive
        # update_component 先 get_by_uuid（返回非 None 绕过 404 分支）再 update
        mock_svc.get_by_uuid.return_value = MagicMock()
        with patch("components.get_file_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(update_component("some-uuid", data=MagicMock()))

        assert exc.value.status_code == 500
        assert "SQL" not in exc.value.detail
        assert exc.value.detail == "Failed to update component"


class TestDeleteComponentSanitization:
    """delete_component 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.soft_delete.side_effect = _raise_sensitive
        with patch("components.get_file_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(delete_component("some-uuid"))

        assert exc.value.status_code == 500
        assert "SQL" not in exc.value.detail
        assert exc.value.detail == "Failed to delete component"


class TestGetComponentParametersSanitization:
    """get_component_parameters 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_component_parameters.side_effect = _raise_sensitive
        with patch("components.get_component_parameter_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_component_parameters("some-name"))

        assert exc.value.status_code == 500
        assert "SQL" not in exc.value.detail
        assert exc.value.detail == "Failed to get component parameters"


class TestCreateComponentSanitization:
    """create_component 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.add.side_effect = _raise_sensitive
        data = ComponentCreate(name="x", component_type="strategy", code="pass", description="d")
        with patch("components.get_file_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(create_component(data=data))

        assert exc.value.status_code == 500
        assert "SQL" not in exc.value.detail
        assert exc.value.detail == "Failed to create component"
