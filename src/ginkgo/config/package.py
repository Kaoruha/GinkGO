# Upstream: 安装脚本和打包工具(setup.py/pip install读取版本信息)
# Downstream: 无(纯元数据定义模块)
# Role: 配置管理包，提供配置文件读取、环境变量解析、配置验证、分层配置(环境变量→配置文件→默认值)等功能，定义GCONF全局配置实例






import os
import logging

PACKAGENAME = "ginkgo"


def _resolve_version() -> str:
    """动态解析版本，fallback 链永不抛异常（#5406 AC#3）。

    与 libs/utils/version.get_version() 读同一真相源（importlib.metadata →
    pyproject.toml → 兜底），保证 CLI `ginkgo version` 与 API /system/status
    返回一致版本。

    独立解析、不 import ginkgo：package.py 是打包元数据层，setup.py 读取时
    ginkgo 尚未安装；CLI 快速路径（main.py）也不应触发 ServiceHub 重型加载。
    """
    # 1. importlib.metadata：已安装 dist 时最准（pip install . 后）
    try:
        import importlib.metadata
        return importlib.metadata.version(PACKAGENAME)
    except Exception:
        logging.getLogger(__name__).debug("importlib.metadata version lookup failed", exc_info=True)
    # 2. 解析 pyproject.toml：开发环境 / 构建中（向上逐层查找至 repo root）
    try:
        import tomllib
        here = os.path.dirname(os.path.abspath(__file__))
        parent = here
        while True:
            candidate = os.path.join(parent, "pyproject.toml")
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    version = tomllib.load(f).get("project", {}).get("version")
                    if version:
                        return version
            nxt = os.path.dirname(parent)
            if nxt == parent:  # 已到文件系统根
                break
            parent = nxt
    except Exception:
        logging.getLogger(__name__).debug("pyproject.toml version lookup failed", exc_info=True)
    # 3. 兜底常量（极端情况，永不抛异常）
    return "0.0.0+unknown"


VERSION = _resolve_version()
AUTHOR = "suny"
EMAIL = "sun159753@gmail.com"
DESC = "Python Backtesting library for trading research"
URL = "url://waf"
