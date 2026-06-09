"""
Import 回归检测测试

防止 #5915 类问题再次发生：
- 循环导入（config.py/logger.py 不应引用 ginkgo.libs）
- from __future__ import annotations 必须在所有 import 前
- ginkgo.libs 全局单例可正常初始化

性能: ~2s, N tests [PASS]
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SRC_ROOT = Path(__file__).parent.parent.parent / "src" / "ginkgo"

# 早期启动模块：在 ginkgo.libs.__init__ 创建单例前被导入，
# 绝对不能 from ginkgo.libs import ... 否则循环依赖
_EARLY_BOOT_MODULES = [
    "libs/core/config.py",
    "libs/core/logger.py",
]


def _read_source(rel_path: str) -> str:
    """读取源文件内容"""
    full = _SRC_ROOT / rel_path
    if not full.exists():
        pytest.skip(f"{rel_path} not found")
    return full.read_text()


class TestEarlyBootNoGinkgoLibsImport:
    """早期启动模块禁止反向引用 ginkgo.libs，防止循环导入。"""

    @pytest.mark.parametrize("rel_path", _EARLY_BOOT_MODULES)
    def test_no_ginkgo_libs_import(self, rel_path: str):
        """config.py / logger.py 源码不含 'from ginkgo.libs import'"""
        source = _read_source(rel_path)
        assert "from ginkgo.libs import" not in source, (
            f"{rel_path} 包含 'from ginkgo.libs import ...'，"
            f"会导致循环导入（#5915）。"
            f"请改用 print() 或 logging 标准库。"
        )


def _collect_future_import_files() -> list[Path]:
    """收集所有含 from __future__ import 的 .py 文件"""
    files = []
    for py_file in _SRC_ROOT.rglob("*.py"):
        try:
            source = py_file.read_text()
            if "from __future__ import" in source:
                files.append(py_file)
        except (OSError, UnicodeDecodeError):
            continue
    return files


class TestFutureImportFirst:
    """from __future__ import 必须是文件中第一条 import 语句。"""

    @pytest.mark.parametrize(
        "py_file",
        _collect_future_import_files(),
        ids=lambda p: str(p.relative_to(_SRC_ROOT)),
    )
    def test_future_before_all_imports(self, py_file: Path):
        """AST 分析：__future__ import 节点必须在所有其他 import 节点之前"""
        source = py_file.read_text()
        tree = ast.parse(source)

        future_idx = None
        first_other_import = None

        for i, node in enumerate(tree.body):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                future_idx = i
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if future_idx is None and first_other_import is None:
                    first_other_import = i

        rel = py_file.relative_to(_SRC_ROOT)
        assert future_idx is not None, f"{rel}: 含 __future__ 引用但 AST 解析失败"
        assert first_other_import is None or future_idx < first_other_import, (
            f"{rel}: 'from __future__ import' 在第 {future_idx} 条语句，"
            f"但其他 import 在第 {first_other_import} 条。"
            f"__future__ import 必须在所有 import 之前（#5915 / clock.py）。"
        )


class TestGinkgoLibsSingletonImportable:
    """验证 ginkgo.libs 全局单例可正常初始化，防止启动即崩溃。"""

    def test_glog_importable(self):
        """from ginkgo.libs import GLOG 不抛异常"""
        from ginkgo.libs import GLOG  # noqa: F401

    def test_gconf_importable(self):
        """from ginkgo.libs import GCONF 不抛异常"""
        from ginkgo.libs import GCONF  # noqa: F401

    def test_gtm_importable(self):
        """from ginkgo.libs import GTM 不抛异常"""
        from ginkgo.libs import GTM  # noqa: F401

    def test_glog_has_info_method(self):
        """GLOG 实例具有 INFO 等日志方法"""
        from ginkgo.libs import GLOG

        assert hasattr(GLOG, "INFO"), "GLOG 缺少 INFO 方法"
        assert callable(GLOG.INFO)
