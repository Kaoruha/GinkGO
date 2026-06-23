"""#5920: data get day -c SH600000 返回无数据（DB 存后缀 600000.SH）。

读取侧加前缀→后缀归一化（与 #5962 写入侧校验门对偶），让前缀/后缀两种
项目既有记法（见 arch_ashare_code_market_prefix_gap）在 get 查询时返回相同数据。

验收：-c SH600000 与 -c 600000.SH 返回相同数据（归一化后查同一 DB key）。
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
import pandas as pd

from ginkgo.client.data_cli import app, _normalize_stock_code

runner = CliRunner()


class TestNormalizeStockCode:
    """#5920: 前缀→后缀归一化（DB stockinfo 存后缀为事实源）"""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "prefix,suffix",
        [("SH600000", "600000.SH"), ("SZ000001", "000001.SZ"),
         ("SH510300", "510300.SH"), ("SZ159915", "159915.SZ")],
    )
    def test_prefix_to_suffix(self, prefix, suffix):
        """SHNNNNNN/SZNNNNNN → NNNNNN.SH/NNNNNN.SZ"""
        assert _normalize_stock_code(prefix) == suffix

    @pytest.mark.unit
    @pytest.mark.parametrize("code", ["600000.SH", "000001.SZ", "510300.SH", "000001.SH"])
    def test_suffix_unchanged(self, code):
        """已是后缀形式 → 原样返回（幂等）"""
        assert _normalize_stock_code(code) == code

    @pytest.mark.unit
    @pytest.mark.parametrize("code", ["INVALIDCODE", "000001", "000001.sz", "HK0001", "", None])
    def test_unrecognized_passthrough(self, code):
        """无法识别的格式 → 原样返回（交由下游/DB 判定，读取侧不报错）"""
        assert _normalize_stock_code(code) == code


class TestGetDayCodeNormalization:
    """#5920: data get day -c 归一化后传 bar_service"""

    @pytest.mark.unit
    def test_prefix_code_normalized_before_query(self):
        """-c SH600000 → bar_service.get_bars_df 收到 code='600000.SH'"""
        df = pd.DataFrame({"code": ["600000.SH"], "timestamp": ["2025-01-02"],
                           "open": [10.0], "high": [11.0], "low": [9.0],
                           "close": [10.5], "volume": [1000], "amount": [10500.0]})
        mock_bar = MagicMock()
        ok = MagicMock()
        ok.success = True
        ok.data = df
        mock_bar.get_bars_df.return_value = ok

        with patch("ginkgo.data.containers.container.bar_service", return_value=mock_bar):
            result = runner.invoke(app, ["get", "day", "-c", "SH600000",
                                         "-s", "20250102", "-e", "20250110"])

        assert result.exit_code == 0, \
            f"前缀 code 应正常查询（exit={result.exit_code}）output={result.output}\nexc={result.exception}"
        mock_bar.get_bars_df.assert_called_once()
        called_code = mock_bar.get_bars_df.call_args.kwargs.get("code")
        assert called_code == "600000.SH", \
            f"SH600000 应归一化为 600000.SH 再查，实得 {called_code!r}"

    @pytest.mark.unit
    def test_suffix_code_query_unchanged(self):
        """-c 600000.SH → bar_service.get_bars_df 收到 code='600000.SH'（回归）"""
        df = pd.DataFrame({"code": ["600000.SH"], "timestamp": ["2025-01-02"],
                           "open": [10.0], "high": [11.0], "low": [9.0],
                           "close": [10.5], "volume": [1000], "amount": [10500.0]})
        mock_bar = MagicMock()
        ok = MagicMock()
        ok.success = True
        ok.data = df
        mock_bar.get_bars_df.return_value = ok

        with patch("ginkgo.data.containers.container.bar_service", return_value=mock_bar):
            result = runner.invoke(app, ["get", "day", "-c", "600000.SH",
                                         "-s", "20250102", "-e", "20250110"])

        assert result.exit_code == 0, f"后缀 code 应正常: {result.output}"
        called_code = mock_bar.get_bars_df.call_args.kwargs.get("code")
        assert called_code == "600000.SH", f"后缀应原样，实得 {called_code!r}"
