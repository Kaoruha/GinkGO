# Issue: #5481 dashboard/system 端点异常响应泄露内部错误细节
# Upstream: api.api.dashboard._safe_detail, api.api.system
# Downstream: core.config.settings (DEBUG 守卫)
# Role: 验证生产环境异常响应脱敏，DEBUG 模式才附 str(e)

"""
#5481: dashboard/system 端点异常响应脱敏测试

验证基础设施下线时，响应体不泄露内部细节（DB 连接串/堆栈片段）。
生产模式返 generic message，DEBUG 模式才附完整异常信息。
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSafeDetail:
    """_safe_detail: 生产脱敏 + DEBUG 详查"""

    def test_debug_off_strips_internal_exception_detail(self):
        """生产模式：_safe_detail 不泄露异常里的内部地址/端口"""
        from api.dashboard import _safe_detail
        from core.config import settings

        sensitive = RuntimeError("DB connection to 10.0.0.1:3306 failed: Access denied")
        with patch.object(settings, "DEBUG", False):
            result = _safe_detail(sensitive)

        # 内部细节被剥离
        assert "10.0.0.1" not in result, f"泄露内部地址: {result}"
        assert "3306" not in result, f"泄露端口: {result}"
        assert "Access denied" not in result, f"泄露异常细节: {result}"
        # 仍是可读字符串（generic message）
        assert isinstance(result, str) and len(result) > 0

    def test_debug_on_returns_full_detail(self):
        """DEBUG 模式：_safe_detail 附完整异常信息（便于本地排查）"""
        from api.dashboard import _safe_detail
        from core.config import settings

        sensitive = RuntimeError("DB connection to 10.0.0.1:3306 failed")
        with patch.object(settings, "DEBUG", True):
            result = _safe_detail(sensitive)

        assert "10.0.0.1" in result, f"DEBUG 模式应附详情: {result}"


class TestEndpointSanitization:
    """端点异常路径响应脱敏：_check_health / system status 下线时不泄露内部细节"""

    def test_check_health_mysql_offline_detail_sanitized(self):
        """_check_health MySQL 下线时 detail 不泄露 DB 连接串/端口"""
        from api.dashboard import _check_health
        from core.config import settings

        mock_container = MagicMock()
        # MySQL 下线：portfolio_service().count() 抛含敏感信息的异常
        mock_container.portfolio_service.return_value.count.side_effect = RuntimeError(
            "DB connection to 10.0.0.1:3306 failed: Access denied for root"
        )
        # Redis 也下线，避免 _check_health 在 Redis 块因 mock 不全而崩
        mock_container.redis_service.return_value.ping.side_effect = RuntimeError("redis down")

        with patch.object(settings, "DEBUG", False), \
             patch("ginkgo.data.containers.container", mock_container):
            health = _check_health()

        mysql = next(h for h in health if h.name == "MySQL")
        assert mysql.status == "OFFLINE"
        assert "10.0.0.1" not in mysql.detail, f"泄露内部地址: {mysql.detail}"
        assert "3306" not in mysql.detail, f"泄露端口: {mysql.detail}"
        assert "Access denied" not in mysql.detail, f"泄露异常细节: {mysql.detail}"

    def test_system_status_exception_error_sanitized(self):
        """/system/status 异常时 error 字段不泄露 DB 连接串"""
        import asyncio
        from api.system import get_system_status
        from core.config import settings

        sensitive = RuntimeError("DB connection to 10.0.0.1:3306 failed: Access denied")
        with patch.object(settings, "DEBUG", False), \
             patch("api.system._get_system_service", side_effect=sensitive):
            resp = asyncio.run(get_system_status())

        # resp = ok(data={"status":"error","version":"unknown","error":...})
        payload = resp.body if hasattr(resp, "body") else resp
        if isinstance(payload, (bytes, bytearray)):
            import json
            payload = json.loads(payload)
        error_text = payload.get("data", {}).get("error", "") if isinstance(payload, dict) else ""
        assert "10.0.0.1" not in error_text, f"泄露内部地址: {error_text}"
        assert "Access denied" not in error_text, f"泄露异常细节: {error_text}"
