"""
模块导入冒烟测试

验证所有包含聚合导入的 __init__.py 可正常导入，
防止因文件缺失或合并遗漏导致 ModuleNotFoundError。

性能: ~1s, N tests [PASS]
"""

import pytest
import importlib
from pathlib import Path

pytestmark = pytest.mark.unit

# 收集所有含 3+ 条 import 语句的 __init__.py 对应的模块路径
_PROJECT_ROOT = Path(__file__).parent.parent.parent / "src"
_GINKGO_SRC = _PROJECT_ROOT / "ginkgo"


def _collect_importable_modules():
    """扫描 ginkgo 包下所有含聚合导入的 __init__.py，返回模块路径列表。"""
    modules = []
    for init_file in sorted(_GINKGO_SRC.rglob("__init__.py")):
        rel = init_file.relative_to(_PROJECT_ROOT)
        parts = list(rel.with_suffix("").parts)
        count = 0
        with open(init_file) as f:
            for line in f:
                if line.startswith(("from ", "import ")):
                    count += 1
        if count >= 3:
            modules.append(".".join(parts))
    return modules


_IMPORTABLE_MODULES = _collect_importable_modules()

@pytest.mark.parametrize("module_path", _IMPORTABLE_MODULES, ids=_IMPORTABLE_MODULES)
def test_module_import(module_path):
    """验证模块可正常导入，不抛出 ModuleNotFoundError 或 ImportError。"""
    importlib.import_module(module_path)


def test_importable_modules_not_empty():
    """验证扫描到了模块，防止扫描逻辑本身失效。"""
    assert len(_IMPORTABLE_MODULES) > 20, (
        f"只扫描到 {len(_IMPORTABLE_MODULES)} 个模块，预期 > 20"
    )
