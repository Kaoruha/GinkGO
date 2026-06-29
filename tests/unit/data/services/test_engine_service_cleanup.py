"""
EngineService 僵尸引擎清理单元测试（Mock 依赖）

覆盖 #5779：cleanup_stale_engines 识别并清理从未运行的引擎
（backtest_start_date 与 backtest_end_date 均空 = 创建后未启动）。
"""

import sys
import os
import datetime
import pytest
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ENGINESTATUS_TYPES


@pytest.fixture
def mock_deps():
    return {
        "crud_repo": MagicMock(),
        "engine_portfolio_mapping_crud": MagicMock(),
        "param_crud": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    with patch("ginkgo.libs.GLOG"):
        return EngineService(
            crud_repo=mock_deps["crud_repo"],
            engine_portfolio_mapping_crud=mock_deps["engine_portfolio_mapping_crud"],
            param_crud=mock_deps["param_crud"],
        )


def _make_engine(uuid, start=None, end=None):
    """构造引擎 mock。start/end 默认 None（僵尸）。"""
    e = MagicMock()
    e.uuid = uuid
    e.name = f"engine-{uuid}"
    e.backtest_start_date = start
    e.backtest_end_date = end
    return e


class TestCleanupStaleEngines:
    """#5779: 僵尸引擎（从未运行）批量清理。"""

    def test_dry_run_identifies_zombies_by_null_dates(self, service, mock_deps):
        """dry_run=True 仅识别不删除：start+end 双空才算僵尸。"""
        run_engine = _make_engine("ran-1", start=datetime.datetime(2026, 1, 1),
                                   end=datetime.datetime(2026, 6, 1))
        zombie_a = _make_engine("zombie-1")  # 双空
        zombie_b = _make_engine("zombie-2")  # 双空
        mock_deps["crud_repo"].find.return_value = [run_engine, zombie_a, zombie_b]

        result = service.cleanup_stale_engines(is_live=0, dry_run=True)

        assert result.is_success()
        assert result.data["dry_run"] is True
        assert result.data["stale_count"] == 2
        assert set(result.data["stale_uuids"]) == {"zombie-1", "zombie-2"}

    def test_real_delete_calls_delete_batch_with_zombie_uuids(self, service, mock_deps):
        """dry_run=False 调 delete_batch 仅传僵尸 uuid，运行过的引擎不传入。"""
        run_engine = _make_engine("ran-1", start=datetime.datetime(2026, 1, 1))
        zombie = _make_engine("zombie-9")
        mock_deps["crud_repo"].find.return_value = [run_engine, zombie]

        captured = ServiceResult.success(data={"successful_deletions": 1}, message="ok")
        service.delete_batch = MagicMock(return_value=captured)

        result = service.cleanup_stale_engines(is_live=0, dry_run=False)

        assert result.is_success()
        service.delete_batch.assert_called_once_with(["zombie-9"])

    def test_no_zombies_skips_delete(self, service, mock_deps):
        """无僵尸时不调 delete_batch，返回 stale_count=0。"""
        run_only = _make_engine("ran-1", start=datetime.datetime(2026, 1, 1),
                                 end=datetime.datetime(2026, 6, 1))
        mock_deps["crud_repo"].find.return_value = [run_only]
        service.delete_batch = MagicMock()

        result = service.cleanup_stale_engines(is_live=0, dry_run=False)

        assert result.is_success()
        assert result.data["stale_count"] == 0
        service.delete_batch.assert_not_called()
