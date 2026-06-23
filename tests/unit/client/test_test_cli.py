"""
test_cli list_tests 命令测试。
覆盖 #6017：WORKING_PATH=None 时不应崩溃（fallback cwd，与 COMPOSE_FILE_PATH 一致）。
"""

import pytest
from unittest.mock import patch

from ginkgo.client.test_cli import list_tests


@pytest.mark.unit
class TestListTestsWorkingPathGuard:
    """list_tests 的 WORKING_PATH 防空守卫（#6017）"""

    @patch("ginkgo.libs.core.config.GCONF")
    def test_list_tests_when_working_path_none_does_not_crash(self, mock_gconf):
        """WORKING_PATH=None 时不应抛 TypeError，应 fallback 到 cwd"""
        # 显式设 None（MagicMock auto-truthy 会掩盖 bug，见 feedback_magicmock_method_attr_mask）
        mock_gconf.WORKING_PATH = None
        # 当前 Path(None) → TypeError；修复后 fallback cwd → 不崩
        list_tests()

    @patch("ginkgo.libs.core.config.GCONF")
    def test_list_tests_when_working_path_valid_executes_cleanly(self, mock_gconf, tmp_path):
        """WORKING_PATH 有效时正常执行（不抛异常）"""
        mock_gconf.WORKING_PATH = str(tmp_path)
        list_tests()
