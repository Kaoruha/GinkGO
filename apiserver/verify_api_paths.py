#!/usr/bin/env python3
"""
API 路径验证脚本
验证所有API端点都使用了正确的版本前缀和命名规范
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from main import app
from fastapi.routing import APIRoute


def check_route_prefix(route: APIRoute) -> dict:
    """检查单个路由的前缀"""
    path = route.path
    methods = route.methods

    result = {
        "path": path,
        "methods": methods,
        "has_version_prefix": path.startswith("/api/v1"),
        "is_no_version_endpoint": is_no_version_endpoint(path),
        "uses_plural": check_plural_form(path),
        "status": "OK"
    }

    # 检查是否有错误
    if not result["is_no_version_endpoint"] and not result["has_version_prefix"]:
        result["status"] = "ERROR: 缺少版本前缀"
    elif result["has_version_prefix"] and not result["uses_plural"]:
        result["status"] = "WARNING: 未使用复数形式"

    return result


def is_no_version_endpoint(path: str) -> bool:
    """检查是否为不需要版本控制的端点"""
    no_version_patterns = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/ws/",
    ]

    for pattern in no_version_patterns:
        if path.startswith(pattern):
            return True
    return False


def check_plural_form(path: str) -> bool:
    """检查是否使用复数形式（仅对资源端点）"""
    # 特殊情况，不需要复数
    singular_exceptions = ["data", "arena", "settings", "auth"]

    # 提取资源名
    parts = path.split("/")
    if len(parts) >= 3 and parts[1] == "api" and parts[2] == "v1":
        resource = parts[3] if len(parts) > 3 else ""

        # 检查是否是例外
        if resource in singular_exceptions:
            return True

        # 检查是否是复数形式（简单规则：以s结尾或包含连字符）
        # 注意：这不是完美的规则，但对大多数情况有效
        if resource and not resource.endswith("s") and "-" not in resource:
            return False

    return True


def generate_report():
    """生成路由报告"""
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(route)

    results = [check_route_prefix(route) for route in routes]

    # 按状态分组
    ok_routes = [r for r in results if r["status"] == "OK"]
    error_routes = [r for r in results if r["status"].startswith("ERROR")]
    warning_routes = [r for r in results if r["status"].startswith("WARNING")]

    # 打印报告
    print("=" * 80)
    print("API 路径验证报告")
    print("=" * 80)
    print(f"\n总路由数: {len(results)}")
    print(f"正常路由: {len(ok_routes)}")
    print(f"警告路由: {len(warning_routes)}")
    print(f"错误路由: {len(error_routes)}")

    if error_routes:
        print("\n" + "=" * 80)
        print("错误路由（缺少版本前缀）:")
        print("=" * 80)
        for r in error_routes:
            print(f"  {r['path']} ({', '.join(r['methods'])})")

    if warning_routes:
        print("\n" + "=" * 80)
        print("警告路由（未使用复数形式）:")
        print("=" * 80)
        for r in warning_routes:
            print(f"  {r['path']} ({', '.join(r['methods'])})")

    # 显示所有路由
    print("\n" + "=" * 80)
    print("所有路由列表:")
    print("=" * 80)

    # 按模块分组
    modules = {}
    for r in results:
        # 提取模块名
        parts = r["path"].split("/")
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "v1":
            module = parts[3]
        elif len(parts) >= 2 and parts[1] in ["health", "docs", "redoc", "ws"]:
            module = "system"
        else:
            module = "other"

        if module not in modules:
            modules[module] = []
        modules[module].append(r)

    # 打印分组的路由
    for module, routes in sorted(modules.items()):
        print(f"\n[{module.upper()}]")
        for r in routes:
            status_symbol = "✓" if r["status"] == "OK" else ("!" if r["status"].startswith("WARNING") else "✗")
            print(f"  {status_symbol} {r['path']} ({', '.join(r['methods'])})")

    # 检查版本配置
    print("\n" + "=" * 80)
    print("版本配置检查:")
    print("=" * 80)
    try:
        from core.version import API_VERSION, API_PREFIX, RESOURCE_PLURAL_MAP

        print(f"  API_VERSION: {API_VERSION}")
        print(f"  API_PREFIX: {API_PREFIX}")
        print(f"  资源映射数量: {len(RESOURCE_PLURAL_MAP)}")

        # 显示一些资源映射
        print("\n  资源复数映射示例:")
        for singular, plural in list(RESOURCE_PLURAL_MAP.items())[:5]:
            print(f"    {singular} -> {plural}")

    except ImportError as e:
        print(f"  ✗ 无法导入版本配置: {e}")

    # 总结
    print("\n" + "=" * 80)
    print("验证总结:")
    print("=" * 80)

    if error_routes:
        print("  ✗ 发现错误：部分路由缺少版本前缀")
        print("  建议：更新路由定义，添加 /api/v1 前缀")
    elif warning_routes:
        print("  ! 发现警告：部分路由未使用复数形式")
        print("  建议：考虑使用复数形式以符合RESTful规范")
    else:
        print("  ✓ 所有路由都符合版本控制规范")

    print("\n" + "=" * 80)

    return len(error_routes) == 0


if __name__ == "__main__":
    success = generate_report()
    sys.exit(0 if success else 1)
