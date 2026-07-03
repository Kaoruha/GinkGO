# #5659 — file.ts 前端文件管理 5 端点全 404，后端缺 flat 适配路由
# Upstream: api.api.file (新建适配层 router)
# Downstream: FileService.list_components / get_by_uuid / add / update / soft_delete
# Role: 验证 /api/v1/file_list、/api/v1/file/{id}、/api/v1/file、/api/v1/update_file
#       五个 flat 适配路由薄委托 FileService，对接前端 file.ts 语义

"""
文件管理 flat 适配路由测试

后端 FileService 能力完整但只通过 /components、/node-graphs/{uuid}/files 暴露；
前端 web-ui/src/api/modules/file.ts 调的 /api/v1/file_list 等 flat 端点无对应路由（全 404）。
本测试验证新建的 api.file router 提供 5 个 flat 端点，薄委托 FileService 既有方法。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import HTTPException
from ginkgo.enums import FILE_TYPES


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True, message="ok"):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    result.message = message
    return result


class TestListFiles:
    """GET /api/v1/file_list — 薄委托 FileService.list_components"""

    def test_delegates_to_list_components_with_pagination(self):
        """list_files 应将 page(1-based)→page(0-based) 下推，size 下推，返回 paginated。"""
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(
            data={"data": [{"uuid": "f1", "name": "s.py"}], "total": 1}
        )

        from api.file import list_files

        with patch("api.file.get_file_service", return_value=mock_service):
            resp = run_async(list_files(query="", page=1, size=100, type=None))

        mock_service.list_components.assert_called_once()
        _, kwargs = mock_service.list_components.call_args
        assert kwargs["page"] == 0          # 1-based → 0-based
        assert kwargs["page_size"] == 100
        assert kwargs["is_del"] is False
        assert resp["meta"]["total"] == 1
        assert resp["data"][0]["uuid"] == "f1"

    def test_passes_keyword_when_query_nonempty(self):
        """非空 query 应作为 keyword 下推到 service。"""
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(
            data={"data": [], "total": 0}
        )

        from api.file import list_files

        with patch("api.file.get_file_service", return_value=mock_service):
            run_async(list_files(query="momentum", page=1, size=50, type=None))

        _, kwargs = mock_service.list_components.call_args
        assert kwargs["keyword"] == "momentum"


class TestGetFile:
    """GET /api/v1/file/{file_id} — 薄委托 FileService.get_by_uuid"""

    def test_delegates_to_get_by_uuid(self):
        mock = MagicMock()
        mock.get_by_uuid.return_value = make_mock_result(
            data={"file": {"uuid": "f1", "name": "s.py"}, "exists": True}
        )

        from api.file import get_file

        with patch("api.file.get_file_service", return_value=mock):
            resp = run_async(get_file("f1"))

        mock.get_by_uuid.assert_called_once_with("f1")
        assert resp["data"]["uuid"] == "f1"

    def test_404_when_not_exists(self):
        mock = MagicMock()
        mock.get_by_uuid.return_value = make_mock_result(
            data={"file": None, "exists": False}
        )

        from api.file import get_file

        with patch("api.file.get_file_service", return_value=mock):
            with pytest.raises(HTTPException) as exc:
                run_async(get_file("missing"))

        assert exc.value.status_code == 404


class TestCreateFile:
    """POST /api/v1/file — 薄委托 FileService.add，提取 file_info.uuid"""

    def test_delegates_to_add_and_returns_uuid(self):
        mock = MagicMock()
        mock.add.return_value = make_mock_result(
            data={"file_info": {"uuid": "new-uuid", "name": "s.py"}}
        )

        from api.file import create_file, FileCreate

        body = FileCreate(name="s.py", type=6, content="print(1)")
        with patch("api.file.get_file_service", return_value=mock):
            resp = run_async(create_file(body))

        mock.add.assert_called_once()
        _, kwargs = mock.add.call_args
        assert kwargs["name"] == "s.py"
        assert kwargs["file_type"] == FILE_TYPES.STRATEGY
        assert kwargs["data"] == b"print(1)"
        assert resp["data"]["uuid"] == "new-uuid"


class TestUpdateFile:
    """POST /api/v1/update_file — 薄委托 FileService.update，content 编码为 bytes"""

    def test_delegates_to_update_with_encoded_content(self):
        mock = MagicMock()
        mock.get_by_uuid.return_value = make_mock_result(
            data={"file": {"uuid": "f1"}, "exists": True}
        )
        mock.update.return_value = make_mock_result()

        from api.file import update_file, FileUpdate

        body = FileUpdate(file_id="f1", content="new code")
        with patch("api.file.get_file_service", return_value=mock):
            resp = run_async(update_file(body))

        mock.update.assert_called_once_with(file_id="f1", data=b"new code")

    def test_404_when_file_not_exists(self):
        mock = MagicMock()
        mock.get_by_uuid.return_value = make_mock_result(
            data={"file": None, "exists": False}
        )

        from api.file import update_file, FileUpdate

        body = FileUpdate(file_id="missing", content="x")
        with patch("api.file.get_file_service", return_value=mock):
            with pytest.raises(HTTPException) as exc:
                run_async(update_file(body))

        assert exc.value.status_code == 404
        mock.update.assert_not_called()


class TestDeleteFile:
    """DELETE /api/v1/file/{file_id} — 薄委托 FileService.soft_delete"""

    def test_delegates_to_soft_delete(self):
        mock = MagicMock()
        mock.soft_delete.return_value = make_mock_result()

        from api.file import delete_file

        with patch("api.file.get_file_service", return_value=mock):
            resp = run_async(delete_file("f1"))

        mock.soft_delete.assert_called_once_with("f1")
