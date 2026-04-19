"""
API 版本配置
提供统一的API版本控制和路径前缀管理
"""

from typing import Set

# API 版本号
API_VERSION = "v1"

# API 路径前缀
API_PREFIX = f"/api/{API_VERSION}"

# 不需要版本控制的端点
NO_VERSION_ENDPOINTS: Set[str] = {
    "/health",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/ws",
}

# 路由标签映射
API_TAGS = {
    "auth": "认证",
    "dashboard": "仪表盘",
    "portfolio": "投资组合",
    "backtest": "回测",
    "components": "组件",
    "data": "数据",
    "arena": "竞技场",
    "settings": "设置",
    "node-graphs": "节点图",
}

# 资源名称映射（单数 -> 复数）
RESOURCE_PLURAL_MAP = {
    "portfolio": "portfolios",
    "backtest": "backtests",
    "node-graph": "node-graphs",  # 保持连字符
    "dashboard": "dashboards",
    "component": "components",
    "setting": "settings",
    "data": "data",  # data 既是单数也是复数
    "arena": "arena",  # arena 保持单数
}

# SSE 端点特殊配置
SSE_ENDPOINTS = {
    "backtest": f"{API_PREFIX}/backtests/{{uuid}}/events",
}


def get_api_path(resource: str, action: str = "", identifier: str = "") -> str:
    """
    生成标准化的API路径

    Args:
        resource: 资源名称（如 'portfolio', 'backtest'）
        action: 操作类型（如 'list', 'create'）
        identifier: 资源标识符（如 UUID）

    Returns:
        完整的API路径

    Examples:
        >>> get_api_path('portfolio', 'list')
        '/api/v1/portfolios'
        >>> get_api_path('portfolio', 'detail', '123')
        '/api/v1/portfolios/123'
    """
    # 获取复数形式
    plural_resource = RESOURCE_PLURAL_MAP.get(resource, f"{resource}s")

    # 构建路径
    path_parts = [API_PREFIX, plural_resource]

    if identifier:
        path_parts.append(identifier)

    if action and action not in ("list", "detail"):
        path_parts.append(action)

    return "/".join(path_parts)


def is_versioned_endpoint(path: str) -> bool:
    """
    检查路径是否需要版本控制

    Args:
        path: API路径

    Returns:
        是否需要版本控制
    """
    # 检查是否在无需版本控制的列表中
    for no_version_path in NO_VERSION_ENDPOINTS:
        if path.startswith(no_version_path):
            return False

    # 检查是否是WebSocket端点
    if path.startswith("/ws"):
        return False

    return True
