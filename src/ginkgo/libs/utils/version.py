"""
版本读取工具 —— 运行时/API 真相源的公共入口。

算法实现共享自 ``ginkgo.config._version_core.resolve_version``（该模块为单一
真相源；本文件只是面向运行时调用方——``SystemService`` / ``GET /system/status``
——的薄壳，保留 ``get_version()`` 公共 API）。

为何不复用 ``config.package.VERSION``：``package.py`` 被 CLI 快速路径
（``main.py``）以顶层裸模块方式导入以绕过 ServiceHub，运行时路径不应依赖该
快速路径的 sys.path 副作用。两端通过共享 ``_version_core`` 算法收敛，
``tests/unit/config/test_package_version.py`` 守护其一致性（#5406 AC#3）。
"""

from ginkgo.config._version_core import resolve_version


def get_version() -> str:
    """返回当前版本，fallback 链永不抛异常（委托给共享核心）。"""
    return resolve_version()
