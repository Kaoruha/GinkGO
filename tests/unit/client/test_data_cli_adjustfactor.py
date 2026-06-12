"""#5868/收敛: ginkgo data sync adjustfactor 应直调 service.sync+calculate

旧代码 `from ginkgo.data import fetch_and_update_adjustfactor, recalculate_adjust_factors_for_code`
→ 这两个函数在 src/ 零定义 → 每次 `ginkgo data sync adjustfactor` 必 ImportError → 命令死代码。
收敛后：CLI 经 container 直调 adjustfactor_service.sync(code, fast_mode=...) + calculate(code)，
与 timer/worker/API handler 全链路一致（sync 落原始因子 → calculate 推导 fore/back）。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client.data_cli import app

runner = CliRunner()


def _ok_result():
    """构造一个 success 的 ServiceResult 替身"""
    r = MagicMock()
    r.success = True
    r.is_success.return_value = True
    r.message = "ok"
    return r


class TestSyncAdjustfactorWiring:
    """CLI sync adjustfactor 直调 service（修复 ImportError 死代码）"""

    @pytest.mark.unit
    def test_sync_adjustfactor_calls_service_sync_then_calculate(self):
        """ginkgo data sync adjustfactor --code X 应调 service.sync(X) 后 calculate(X)

        RED: 旧代码 import 不存在的函数 → ImportError，sync/calculate 永不被调，
        命令 exit_code != 0。
        """
        mock_svc = MagicMock()
        mock_svc.sync.return_value = _ok_result()
        mock_svc.calculate.return_value = _ok_result()

        with patch("ginkgo.data.containers.container.adjustfactor_service", return_value=mock_svc):
            result = runner.invoke(app, ["sync", "adjustfactor", "--code", "000001.SZ"])

        # 命令不应因 ImportError 崩溃
        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        mock_svc.sync.assert_called_once()
        assert mock_svc.sync.call_args.args[0] == "000001.SZ"
        # sync 成功后衔接 calculate（与 timer/worker/API handler 对齐）
        mock_svc.calculate.assert_called_once_with("000001.SZ")
