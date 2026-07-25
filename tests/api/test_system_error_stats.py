# Issue #6785: 可观测层接入 4/4 — GET/POST /system/error-stats 错误热点观测端点
# Upstream: api.system.get_error_stats / reset_error_stats (new endpoints)
# Downstream: 运维/排障（查询当前 API 进程累计错误热点 + 排障后清零）
# Role: 把 GLOG 进程内 error_stats 经 SystemService 暴露成 API 端点（分层 API→Service→GLOG）。

"""
#6785 错误热点观测端点测试。

GLOG.get_error_stats/clear_error_stats 已实现 (logger.py:519/538) 但无 API 端点暴露。
本切片在 SystemService 加包装、api.system 加端点：

- ``GET /system/error-stats``     查询进程内错误统计
- ``POST /system/error-stats/reset``  清零统计

两端点均需管理员鉴权。遵循 #5899：DB 实查 ``credential.is_admin``，不信任 JWT payload 里的
``req.state.is_admin``（用户被降权后旧 token 仍带 is_admin=True），fail-closed（DB 失败 → 403）。
"""

import asyncio

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


def _make_req(user_uuid="u-admin"):
    """构造带中间件注入 user_uuid 的 mock Request。"""
    req = MagicMock()
    req.state.user_uuid = user_uuid
    return req


class TestErrorStatsGetEndpoint:
    """GET /system/error-stats 查询 + admin 鉴权 (#6785)。"""

    def test_admin_returns_error_stats(self):
        """管理员 → 返回 SystemService.get_error_stats 的结构化计数。"""
        from api.system import get_error_stats

        req = _make_req("u-admin")
        mock_cred = MagicMock()
        mock_cred.is_admin = True
        mock_user_svc = MagicMock()
        mock_user_svc.get_credential.return_value = mock_cred
        mock_sys_svc = MagicMock()
        mock_sys_svc.get_error_stats.return_value = {
            "total_error_patterns": 1,
            "top_error_patterns": [{"pattern_hash": "h1", "count": 3}],
            "total_error_count": 3,
        }
        with patch("api.auth.get_user_service", return_value=mock_user_svc), \
             patch("api.system._get_system_service", return_value=mock_sys_svc):
            result = run_async(get_error_stats(req))

        mock_user_svc.get_credential.assert_called_once_with("u-admin")
        assert result["data"]["total_error_count"] == 3

    def test_non_admin_blocked_403(self):
        """非管理员 → 403（不暴露内部错误分布）。"""
        from api.system import get_error_stats

        req = _make_req("u-normal")
        mock_cred = MagicMock()
        mock_cred.is_admin = False
        mock_user_svc = MagicMock()
        mock_user_svc.get_credential.return_value = mock_cred
        mock_sys_svc = MagicMock()
        with patch("api.auth.get_user_service", return_value=mock_user_svc), \
             patch("api.system._get_system_service", return_value=mock_sys_svc):
            with pytest.raises(HTTPException) as exc:
                run_async(get_error_stats(req))

        assert exc.value.status_code == 403
        mock_sys_svc.get_error_stats.assert_not_called()

    def test_db_failure_fail_closed_403(self):
        """get_credential 抛异常（DB 不可用）→ fail-closed 403（#5899：不信 JWT is_admin）。"""
        from api.system import get_error_stats

        req = _make_req("u-admin")
        mock_user_svc = MagicMock()
        mock_user_svc.get_credential.side_effect = RuntimeError("db down")
        mock_sys_svc = MagicMock()
        with patch("api.auth.get_user_service", return_value=mock_user_svc), \
             patch("api.system._get_system_service", return_value=mock_sys_svc):
            with pytest.raises(HTTPException) as exc:
                run_async(get_error_stats(req))

        assert exc.value.status_code == 403
        mock_sys_svc.get_error_stats.assert_not_called()


class TestErrorStatsResetEndpoint:
    """POST /system/error-stats/reset 清零 + admin 鉴权 (#6785)。"""

    def test_admin_reset_calls_service(self):
        """管理员 → 调 SystemService.reset_error_stats 清零。"""
        from api.system import reset_error_stats

        req = _make_req("u-admin")
        mock_cred = MagicMock()
        mock_cred.is_admin = True
        mock_user_svc = MagicMock()
        mock_user_svc.get_credential.return_value = mock_cred
        mock_sys_svc = MagicMock()
        mock_sys_svc.reset_error_stats.return_value = {"reset": True}
        with patch("api.auth.get_user_service", return_value=mock_user_svc), \
             patch("api.system._get_system_service", return_value=mock_sys_svc):
            result = run_async(reset_error_stats(req))

        mock_sys_svc.reset_error_stats.assert_called_once()
        assert result["data"] == {"reset": True}

    def test_non_admin_reset_blocked_403(self):
        """非管理员 reset → 403（清零同样需管理员，防误清排障数据）。"""
        from api.system import reset_error_stats

        req = _make_req("u-normal")
        mock_cred = MagicMock()
        mock_cred.is_admin = False
        mock_user_svc = MagicMock()
        mock_user_svc.get_credential.return_value = mock_cred
        mock_sys_svc = MagicMock()
        with patch("api.auth.get_user_service", return_value=mock_user_svc), \
             patch("api.system._get_system_service", return_value=mock_sys_svc):
            with pytest.raises(HTTPException) as exc:
                run_async(reset_error_stats(req))

        assert exc.value.status_code == 403
        mock_sys_svc.reset_error_stats.assert_not_called()
