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
    """从 pyproject.toml [project].version 读取（开发环境兜底）。"""
    if tomllib is None:
        return None
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        # ginkgo/libs/utils/version.py → 向上逐层找 pyproject.toml
        for parent in (here, os.path.dirname(here),
                       os.path.dirname(os.path.dirname(here)),
                       os.path.dirname(os.path.dirname(os.path.dirname(here)))):
            candidate = os.path.join(parent, "pyproject.toml")
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                version = data.get("project", {}).get("version")
                if version:
                    return version
    except Exception:
        return None
    return None


def get_version() -> str:
    """返回当前版本，fallback 链永不抛异常。"""
    return _version_from_metadata() or _version_from_pyproject() or _FALLBACK_VERSION
