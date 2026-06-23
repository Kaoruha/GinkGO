"""
深度健康检查 (#5766)

此前 /health 与 /api/health 硬编码返回静态 {status: healthy}，零依赖检查；
当 /system/status 报 error（如 clock.py import error）时仍谎报健康。

compute_health() 复用 SystemService.get_system_status() 的真实探测
（含模块加载状态 + 基础设施检查），其报告 error 时降级为 unhealthy。
健康端点本身永不抛异常 —— 任何意外错误都降级为 unhealthy 而非 500，
避免健康检查自身成为故障源。

抽成独立模块以便单元测试（避开 FastAPI app 启动的连带副作用）；
main.py 的 /health、/api/health 端点透传调用本函数。
"""

from typing import Any, Dict


def compute_health() -> Dict[str, Any]:
    """
    执行核心依赖检查并返回健康状态。

    Returns:
        {"status": "healthy"|"unhealthy", "service": str, "error"?: str}
        - healthy: SystemService 探测正常（status == "running"）
        - unhealthy: SystemService 报 error，或自身抛异常
    """
    service = "ginkgo-api-server"
    try:
        from ginkgo.core.services.system_service import SystemService

        status_data = SystemService().get_system_status()
        if status_data.get("status") == "error":
            return {
                "status": "unhealthy",
                "service": service,
                "error": status_data.get("error", "unknown error"),
            }
        return {"status": "healthy", "service": service}
    except Exception as e:
        return {"status": "unhealthy", "service": service, "error": str(e)}
