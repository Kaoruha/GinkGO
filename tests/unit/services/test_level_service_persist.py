"""#5932: set-level 跨进程持久化。

CLI 每次调用是独立进程, 内存 _custom_levels 跨进程隔离。
set_level 必须持久化到文件, 新实例(__init__ 模拟新进程)能读到。
旧实现纯内存 → set 进程退出丢失, get 新进程读空 → INFO。
"""
import pytest
from unittest.mock import MagicMock, patch

from ginkgo.services.logging.level_service import LevelService


def _patched_env(levels_file):
    """patch GCONF 白名单 + LevelService 持久化路径 → levels_file。"""
    gconf_patch = patch("ginkgo.services.logging.level_service.GCONF")
    file_patch = patch.object(LevelService, "_LEVELS_FILE", levels_file)
    return gconf_patch, file_patch


class TestSetLevelPersistsAcrossInstances:
    """#5932: set_level 后新实例(新进程)能读到持久化级别。"""

    @pytest.mark.unit
    def test_set_then_new_instance_reads_level(self, tmp_path):
        f = tmp_path / "levels.json"
        gconf_patch, file_patch = _patched_env(f)
        with gconf_patch as mock_gconf, file_patch:
            mock_gconf.LOGGING_LEVEL_WHITELIST = ["backtest", "trading", "data"]
            svc1 = LevelService(glog=MagicMock())
            r = svc1.set_level("backtest", "DEBUG")
            assert r.is_success()
            # 新实例 = 模拟新进程, 应从持久化源读到 DEBUG
            svc2 = LevelService(glog=MagicMock())
        assert svc2.get_level("backtest") == "DEBUG", \
            f"新进程应读到持久化 DEBUG, 实际 {svc2.get_level('backtest')!r}"

    @pytest.mark.unit
    def test_reset_then_new_instance_back_to_default(self, tmp_path):
        f = tmp_path / "levels.json"
        gconf_patch, file_patch = _patched_env(f)
        with gconf_patch as mock_gconf, file_patch:
            mock_gconf.LOGGING_LEVEL_WHITELIST = ["backtest", "trading", "data"]
            svc = LevelService(glog=MagicMock())
            svc.set_level("backtest", "DEBUG")
            svc.reset_levels()
            # 新实例: 重置应已清空持久化源
            svc2 = LevelService(glog=MagicMock())
        assert svc2.get_level("backtest") == "INFO", \
            f"重置后新进程应回默认 INFO, 实际 {svc2.get_level('backtest')!r}"
