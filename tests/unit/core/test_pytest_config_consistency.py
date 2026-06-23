"""#6021: pyproject.toml pytest 配置自洽测试。

addopts/timeout 引用 pytest-timeout 时，dev 依赖与 required_plugins 必须声明它，
否则未装包的环境跑 `pytest` 报 `unrecognized arguments: --timeout=60`（须手动
`-o addopts=` 绕过）。本测试静态校验配置自洽，防回归。
"""
import tomllib
from pathlib import Path


def _load_pyproject() -> tuple[Path, dict]:
    """从本测试文件向上定位仓库根的 pyproject.toml。"""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        cand = parent / "pyproject.toml"
        if cand.exists():
            return cand, tomllib.loads(cand.read_text(encoding="utf-8"))
    raise FileNotFoundError("pyproject.toml not found from test location")


def _uses_timeout(ini: dict) -> bool:
    addopts = ini.get("addopts", [])
    if any("--timeout" in str(a) for a in addopts):
        return True
    return "timeout" in ini  # 全局 timeout = N 同样需 pytest-timeout


def test_pytest_timeout_declared_in_dev_deps_when_used():
    """#6021: addopts/ini 引用 --timeout → dev 依赖必须声明 pytest-timeout。

    未声明时未装包环境跑 pytest 报 unrecognized arguments(--timeout=60)。
    """
    _, data = _load_pyproject()
    ini = data["tool"]["pytest"]["ini_options"]
    if not _uses_timeout(ini):
        return
    dev_deps = data["project"]["optional-dependencies"].get("dev", [])
    assert any("pytest-timeout" in d for d in dev_deps), (
        "addopts/ini 引用 --timeout，但 dev 依赖未声明 pytest-timeout → "
        "pytest 报 unrecognized arguments: --timeout=60 (#6021)"
    )


def test_pytest_timeout_in_required_plugins_when_used():
    """#6021: addopts/ini 引用 --timeout → required_plugins 必须含 pytest-timeout。

    required_plugins 在 pytest 启动期强校验插件齐全，缺则明确报 'missing
    required plugin'，而非 addopts 的 unrecognized arguments 困惑报错；
    并防止配置与依赖再次解耦（回归护栏）。
    """
    _, data = _load_pyproject()
    ini = data["tool"]["pytest"]["ini_options"]
    if not _uses_timeout(ini):
        return
    required = ini.get("required_plugins", [])
    assert "pytest-timeout" in required, (
        "required_plugins 缺 pytest-timeout → 启动期无强校验，配置与依赖可再次解耦 (#6021 回归)"
    )


def test_pytest_timeout_plugin_is_installed():
    """#6021 端到端验收: pytest-timeout 已安装可 import（dev 环境装了 .[dev]）。

    配置自洽(前两测)是必要条件，本测验证充分条件——包确实装了。
    CI/开发者 `pip install -e .[dev]` 后此测绿；裸环境红提示装包。
    """
    import importlib

    importlib.import_module("pytest_timeout")
