"""#5962: ginkgo data sync day --code 缺格式校验，接受 INVALIDCODE 并报告成功。

验收（本 PR 聚焦格式校验，P1+P2）：
- INVALIDCODE / 000001（缺后缀）→ 报错非零退出，不触达 bar_service
- 000001.SZ（合法格式）→ 放行，调 bar_service.sync_smart

DB 存在性校验（"code not found"）属 service 层，本 PR 不做（见 PR body scope）。
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

from ginkgo.client.data_cli import app, _is_valid_stock_code

runner = CliRunner()


class TestIsValidStockCode:
    """#5962: 格式契约 NNNNNN.SH/NNNNNN.SZ（6 位数字 + 大写交易所后缀）"""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "code",
        [
            # 后缀记法（data get stockinfo -c 风格）
            "000001.SZ", "600000.SH", "510300.SH", "000001.SH", "159915.SZ", "200002.SZ", "900901.SH",
            # 前缀记法（position/adjustfactor/tick mapper 风格）
            "SH600000", "SZ000001", "SH510300", "SZ159915",
        ],
    )
    def test_accepts_valid_formats(self, code):
        """后缀 NNNNNN.SH/NNNNNN.SZ + 前缀 SHNNNNNN/SZNNNNNN 两种项目既有记法"""
        assert _is_valid_stock_code(code) is True, f"{code} 应合法"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "code",
        ["INVALIDCODE", "000001", "000001.sz", "000001.sh", "00001.SZ", "0000001.SZ", "000001.HK", " 000001.SZ", "", None],
    )
    def test_rejects_invalid_formats(self, code):
        """非数字/缺后缀/小写后缀/位数错/他交易所/空白/空"""
        assert _is_valid_stock_code(code) is False, f"{repr(code)} 应非法"


def _ok_result():
    r = MagicMock()
    r.is_success.return_value = True
    r.message = "ok"
    raw = MagicMock()
    raw.records_added = 0
    r.data = raw
    return r


class TestSyncDayCodeValidation:
    """#5962: --code 格式校验门（try 块外，干净非零退出）"""

    @pytest.mark.unit
    def test_invalid_code_rejected_before_service(self):
        """INVALIDCODE → 非零退出 + 不触达 bar_service（校验门先于 try）"""
        mock_bar = MagicMock()
        mock_bar.sync_smart.return_value = _ok_result()

        with patch("ginkgo.data.containers.container.bar_service", return_value=mock_bar), \
             patch("ginkgo.data.containers.container.stockinfo_service", return_value=MagicMock()):
            result = runner.invoke(app, ["sync", "day", "--code", "INVALIDCODE"])

        assert result.exit_code != 0, \
            f"INVALIDCODE 应非零退出（exit={result.exit_code}）output={result.output}"
        assert "INVALIDCODE" in result.output or "nvalid" in result.output.lower(), \
            f"错误提示应含代码或 invalid 字样: {result.output}"
        mock_bar.sync_smart.assert_not_called()

    @pytest.mark.unit
    def test_missing_suffix_rejected(self):
        """000001（缺 .SH/.SZ 后缀）→ 格式错误非零退出"""
        mock_bar = MagicMock()

        with patch("ginkgo.data.containers.container.bar_service", return_value=mock_bar), \
             patch("ginkgo.data.containers.container.stockinfo_service", return_value=MagicMock()):
            result = runner.invoke(app, ["sync", "day", "--code", "000001"])

        assert result.exit_code != 0, f"缺后缀应非零退出: {result.output}"
        mock_bar.sync_smart.assert_not_called()

    @pytest.mark.unit
    def test_valid_code_proceeds_to_sync(self):
        """000001.SZ（合法格式）→ 放行，bar_service.sync_smart 被调"""
        mock_bar = MagicMock()
        mock_bar.sync_smart.return_value = _ok_result()

        with patch("ginkgo.data.containers.container.bar_service", return_value=mock_bar), \
             patch("ginkgo.data.containers.container.stockinfo_service", return_value=MagicMock()):
            result = runner.invoke(app, ["sync", "day", "--code", "000001.SZ"])

        assert result.exit_code == 0, \
            f"合法 code 应放行（exit={result.exit_code}）output={result.output}\nexc={result.exception}"
        mock_bar.sync_smart.assert_called_once()
        assert mock_bar.sync_smart.call_args.kwargs.get("code") == "000001.SZ" or \
               mock_bar.sync_smart.call_args.args[0] == "000001.SZ"
