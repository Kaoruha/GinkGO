"""
#2715: drivers/__init__.py + data/__init__.py 懒加载改造

验证 import ginkgo.data.drivers 不再触发全量模块加载，
同时保持所有公开接口的向后兼容性。

性能: ~1s, N tests [PASS]
"""

import subprocess
import sys
import pytest

pytestmark = pytest.mark.unit

_MEASURE_SCRIPT = """
import sys
before = set(sys.modules.keys())
import ginkgo.data.drivers
after = set(sys.modules.keys())
ginkgo_modules = sorted(m for m in (after - before) if m.startswith('ginkgo'))
print(len(ginkgo_modules))
"""


def _run_subprocess(script):
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return result.stdout.strip().split("\n")[-1]


class TestDriversLazyImport:
    """#2715: 验证 drivers 包懒加载减少导入足迹"""

    def test_import_footprint_under_50(self):
        """import ginkgo.data.drivers 应加载 < 50 个 ginkgo 模块（当前极限 ~39，含 libs 31 + 5 driver + 3 其他）

        39 个模块是 PEP 562 + 保留业务逻辑在 __init__.py 的极限。
        libs(31) 被 CircuitBreaker/装饰器顶层依赖，无法再降。
        5 个 driver 被类型注解和 ConnectionManager 直接依赖，无法再降。
        """
        count = int(_run_subprocess(_MEASURE_SCRIPT))
        assert count < 50, f"Expected < 50 ginkgo modules, got {count}"


class TestLazyImportBackwardCompat:
    """#2715: 验证懒加载后公开接口仍可正常使用"""

    _IMPORT_COMPAT_SCRIPT = """
import sys
from ginkgo.data.drivers import {symbol}
print(type({symbol}).__name__)
"""

    @pytest.mark.parametrize("symbol", [
        "GinkgoClickhouse",
        "GinkgoMysql",
        "GinkgoMongo",
        "GinkgoRedis",
        "DatabaseDriverBase",
        "GinkgoProducer",
        "GinkgoConsumer",
    ])
    def test_class_import(self, symbol):
        """from ginkgo.data.drivers import XxxClass 返回正确的类"""
        output = _run_subprocess(self._IMPORT_COMPAT_SCRIPT.format(symbol=symbol))
        assert output in ("type", "ABCMeta"), f"Expected class type, got {output}"

    def test_function_import_get_db_connection(self):
        """from ginkgo.data.drivers import get_db_connection 返回 callable"""
        output = _run_subprocess("""
from ginkgo.data.drivers import get_db_connection
print(callable(get_db_connection))
""")
        assert output == "True"

    def test_function_import_kafka_topic_llen(self):
        """from ginkgo.data.drivers import kafka_topic_llen 返回 callable"""
        output = _run_subprocess("""
from ginkgo.data.drivers import kafka_topic_llen
print(callable(kafka_topic_llen))
""")
        assert output == "True"


class TestDataInitLazyImport:
    """#2715: 验证 ginkgo.data 包的 container/seeding/get_crud 懒加载"""

    _DATA_IMPORT_SCRIPT = """
from ginkgo.data import {symbol}
print(type({symbol}).__name__)
"""

    def test_container_import(self):
        """from ginkgo.data import container 返回容器实例"""
        output = _run_subprocess("""
from ginkgo.data import container
print(type(container).__name__)
""")
        assert output.endswith("Container"), f"Expected *Container, got {output}"

    def test_get_crud_import(self):
        """from ginkgo.data import get_crud 返回 callable"""
        output = _run_subprocess("""
from ginkgo.data import get_crud
print(callable(get_crud))
""")
        assert output == "True"

    def test_seeding_import(self):
        """from ginkgo.data import seeding 返回模块"""
        output = _run_subprocess("""
from ginkgo.data import seeding
print(type(seeding).__name__)
""")
        assert output == "module"


class TestLazyImportPerformance:
    """#2715: 前后性能对比"""

    def test_before_after_comparison(self):
        """打印改造前后 ginkgo 模块加载数对比"""
        count = int(_run_subprocess(_MEASURE_SCRIPT))
        # 改造前: 211, 改造后应 < 100
        before = 211
        reduction = (1 - count / before) * 100
        print(f"\n  改造前: {before} ginkgo 模块")
        print(f"  改造后: {count} ginkgo 模块")
        print(f"  减少: {reduction:.0f}%")
        assert count < before, f"No improvement: {count} >= {before}"
