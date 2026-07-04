"""
版本解析共享核心 —— 单一真相源的算法实现。

供两处导入路径互不可达的调用方共享：
  - ``ginkgo.config.package``：打包元数据层，被 CLI 快速路径 ``main.py`` 通过
    ``sys.path.insert + import package`` 提升为顶层裸模块导入，**绕过**
    ``ginkgo/__init__.py`` 的 ServiceHub 重型加载。故 ``package.py`` 不能写
    任何 ``from ginkgo...`` 导入，只能 import 本文件（同目录 sibling）。
  - ``ginkgo.libs.utils.version``：运行时/API 路径（SystemService /
    ``GET /system/status``），无上述约束，走 ``from ginkgo.config._version_core`` 导入。

本文件因此**只依赖 stdlib**（``importlib.metadata`` / ``tomllib`` / ``os``），
永不 import 任何 ``ginkgo.*``，否则会捅破 CLI 快速路径。

fallback 链（永不抛异常，#5406 AC#3）：
  1. ``importlib.metadata``：已安装 dist 时最准（``pip install .`` 后）。
  2. 解析 ``pyproject.toml``：开发环境 / Docker 仅 COPY src 场景。向上逐层查找
     至文件系统根，不依赖固定层数 —— 兼容 src-layout（4 次 dirname 到不了 repo
     root，原 off-by-one 已修）及生产镜像 ``/app/src/ginkgo/...`` 布局。
  3. 兜底常量。
"""

import os
import importlib.metadata
from typing import Optional

try:  # py>=3.11 stdlib
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

_PACKAGE_NAME = "ginkgo"
_FALLBACK_VERSION = "0.0.0+unknown"


def _version_from_metadata() -> Optional[str]:
    """从已安装的 dist-info 读取版本（Docker 未装 dist 时返 None）。"""
    try:
        return importlib.metadata.version(_PACKAGE_NAME)
    except Exception:
        return None


def _version_from_pyproject() -> Optional[str]:
    """从 pyproject.toml [project].version 读取（开发环境 / Docker 仅 COPY src）。

    向上逐层查找至文件系统根，不依赖固定层数。
    """
    if tomllib is None:
        return None
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        parent = here
        while True:
            candidate = os.path.join(parent, "pyproject.toml")
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                version = data.get("project", {}).get("version")
                if version:
                    return version
            nxt = os.path.dirname(parent)
            if nxt == parent:  # 已到文件系统根
                break
            parent = nxt
    except Exception:
        return None
    return None


def resolve_version() -> str:
    """返回当前版本，fallback 链永不抛异常。"""
    return _version_from_metadata() or _version_from_pyproject() or _FALLBACK_VERSION
