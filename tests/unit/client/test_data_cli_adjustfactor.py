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
from datetime import datetime
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

import pandas as pd

from ginkgo.client.data_cli import app
from ginkgo.data.services.base_service import ServiceResult

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


class TestGetAdjustfactor:
    """CLI get adjustfactor 直调 service.get_adjustfactors_df（修复 not yet implemented 桩）

    旧桩 (data_cli get adjustfactor) 只打印 "not yet implemented"，从不查库。
    收敛后：经 container 调 adjustfactor_service.get_adjustfactors_df，与 sync/update 同源；
    start/end 从 "YYYYMMDD" 转 datetime（DB timestamp 过滤需 datetime 类型）。
    """

    @pytest.mark.unit
    def test_get_adjustfactor_success_calls_service_with_datetime(self):
        """get adjustfactor --code X --start ... --end ... 接 get_adjustfactors_df(datetime)

        RED: 桩输出 "not yet implemented"，从不调 service.get_adjustfactors_df。
        """
        mock_svc = MagicMock()
        mock_svc.get_adjustfactors_df.return_value = ServiceResult(
            success=True,
            message="ok",
            data=pd.DataFrame([{
                "code": "000001.SZ",
                "timestamp": datetime(2025, 11, 1),
                "adjust_type": "fore",
                "adj_factor": 1.0,
            }]),
        )

        with patch("ginkgo.data.containers.container.adjustfactor_service", return_value=mock_svc):
            result = runner.invoke(
                app,
                ["get", "adjustfactor", "--code", "000001.SZ", "--start", "20251101", "--end", "20251107"],
            )

        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        # 不再是桩
        assert "not yet implemented" not in result.output
        # 真实查库：经 service.get_adjustfactors_df
        mock_svc.get_adjustfactors_df.assert_called_once()
        kwargs = mock_svc.get_adjustfactors_df.call_args.kwargs
        assert kwargs["code"] == "000001.SZ"
        # start/end 从 "YYYYMMDD" 转 datetime（DB timestamp__gte/lte 需 datetime）
        assert kwargs["start_date"] == datetime(2025, 11, 1)
        assert kwargs["end_date"] == datetime(2025, 11, 7)

    @pytest.mark.unit
    def test_get_adjustfactor_service_failure_exits_nonzero(self):
        """service 返回失败 → exit 1 + 失败信息（不静默成功）"""
        mock_svc = MagicMock()
        mock_svc.get_adjustfactors_df.return_value = ServiceResult(
            success=False, message="DB down", data=pd.DataFrame(),
        )

        with patch("ginkgo.data.containers.container.adjustfactor_service", return_value=mock_svc):
            result = runner.invoke(
                app,
                ["get", "adjustfactor", "--code", "000001.SZ", "--start", "20251101", "--end", "20251107"],
            )

        assert result.exit_code == 1
        assert "Failed" in result.output or "failed" in result.output.lower()

    @pytest.mark.unit
    def test_get_adjustfactor_empty_result_shows_friendly(self):
        """空结果 → 友好提示，exit 0（不崩溃、不误报失败）"""
        mock_svc = MagicMock()
        mock_svc.get_adjustfactors_df.return_value = ServiceResult(
            success=True, message="ok", data=pd.DataFrame(),
        )

        with patch("ginkgo.data.containers.container.adjustfactor_service", return_value=mock_svc):
            result = runner.invoke(
                app,
                ["get", "adjustfactor", "--code", "000001.SZ", "--start", "20251101", "--end", "20251107"],
            )

        assert result.exit_code == 0, f"exit={result.exit_code} out={result.output}\nexc={result.exception}"
        assert "No adjustfactor data found" in result.output
