"""
CLI 版本真相源契约测试（#5406 AC#3）。

验证 config/package.py 的 VERSION 与 API 侧 get_version() 同源，确保
`ginkgo version` CLI 与 GET /system/status 返回一致版本。

package.py 是打包元数据层（被 setup.py / pip install 读取），不能 import
ginkgo 包（打包时尚未安装；CLI 快速路径也不应触发 ServiceHub 重型加载），
故独立解析同一真相源（importlib.metadata → pyproject.toml → 兜底），
结果与 libs/utils/version.get_version() 收敛。
"""

import pytest

from ginkgo.config.package import VERSION as PACKAGE_VERSION
from ginkgo.libs.utils.version import get_version


@pytest.mark.unit
class TestPackageVersionSource:
    """package.VERSION 必须与 API get_version() 同源（#5406 AC#3）。"""

    def test_package_version_equals_api_version(self):
        """CLI package.VERSION == API get_version()。

        AC#3 核心：`ginkgo version` 与 /system/status 返回同一版本。
        package.py 硬编码 0.8.1 而 get_version()=0.8.2 时此断言失败。
        """
        assert PACKAGE_VERSION == get_version(), (
            f"CLI {PACKAGE_VERSION!r} ≠ API {get_version()!r}，#5406 AC#3 违反"
        )

    def test_package_version_nonempty(self):
        """VERSION 非空、非占位符。"""
        assert PACKAGE_VERSION
        assert PACKAGE_VERSION != "unknown"
