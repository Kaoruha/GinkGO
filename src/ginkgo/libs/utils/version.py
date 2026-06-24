"""
版本读取工具 —— 单一真相源。

提供 get_version() fallback 链，供 SystemService 与 CLI 共用：
1. importlib.metadata（已装 dist 时最准）
2. 解析 pyproject.toml（开发环境 / Docker 仅 COPY src 场景）
3. 兜底常量（极端情况，永不抛异常）
"""

import os
import importlib.metadata
from typing import Optional

try:  # py>=3.11 stdlib
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

_FALLBACK_VERSION = "0.0.0+unknown"
_PACKAGE_NAME = "ginkgo"


def _version_from_metadata() -> Optional[str]:
    """从已安装的 dist-info 读取版本（Docker 未装 dist 时返 None）。"""
    try:
        return importlib.metadata.version(_PACKAGE_NAME)
    except Exception:
        return None


def _version_from_pyproject() -> Optional[str]:
    """从 pyproject.toml [project].version 读取（开发环境 / Docker 仅 COPY src 场景）。

    向上逐层查找 pyproject.toml 直到文件系统根，不依赖固定层数 —— 兼容
    src-layout（src/ginkgo/libs/utils/ → ... → repo root，4 次 dirname）及
    生产镜像 /app/src/ginkgo/libs/utils/ → /app 布局（pyproject 需 COPY 进镜像，
    见 Dockerfile.api-server）。原实现固定遍历 4 层，src-layout 下 repo root
    在第 5 层，永远返 None（off-by-one）。
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


def get_version() -> str:
    """返回当前版本，fallback 链永不抛异常。"""
    return _version_from_metadata() or _version_from_pyproject() or _FALLBACK_VERSION
