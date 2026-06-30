"""
#5766: /health 深度健康检查

此前 /health 与 /api/health 硬编码返回静态 {status: healthy}，
不检查任何核心依赖；当 /system/status 报 error（如 clock.py import error）
时仍谎报健康。修复让健康端点复用 SystemService.get_system_status()，
error 时降级为 unhealthy。

测试直接覆盖 compute_health() 逻辑（健康判定核心），避开 FastAPI app
启动连带副作用；端点本身仅 return compute_health()（透传）。
"""

from unittest.mock import patch

import pytest


@pytest.mark.integration
class TestComputeHealth:
    """compute_health: 联动 SystemService 的深度健康判定"""

    def test_unhealthy_when_system_status_reports_error(self):
        """SystemService 报 error（如 clock.py import error）时降级 unhealthy"""
        from health import compute_health

        with patch(
            "ginkgo.core.services.system_service.SystemService.get_system_status",
            return_value={"status": "error", "error": "clock.py import error"},
        ):
            result = compute_health()

        assert result["status"] == "unhealthy"
        assert result["service"] == "ginkgo-api-server"
        assert "clock.py import error" in result["error"]

    def test_healthy_when_system_status_running(self):
        """SystemService 正常（status=running）时返回 healthy"""
        from health import compute_health

        with patch(
            "ginkgo.core.services.system_service.SystemService.get_system_status",
            return_value={"status": "running", "modules": {}, "infrastructure": {}},
        ):
            result = compute_health()

        assert result["status"] == "healthy"
        assert result["service"] == "ginkgo-api-server"

    def test_unhealthy_when_systemservice_itself_raises(self):
        """SystemService 构造/调用异常时降级 unhealthy（健康端点永不 500）"""
        from health import compute_health

        with patch(
            "ginkgo.core.services.system_service.SystemService",
            side_effect=RuntimeError("service hub offline"),
        ):
            result = compute_health()

        assert result["status"] == "unhealthy"
        assert "service hub offline" in result["error"]
