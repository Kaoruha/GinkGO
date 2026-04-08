"""
性能: 222MB RSS, 3.68s, 14 tests [PASS]
GinkgoTushare 数据源单元测试（Mock tushare API）

测试范围:
1. 构造和连接逻辑
2. 分页窗口大小计算
3. 日线数据获取（单次/分段）
4. 复权因子获取
5. 空数据处理
6. 异常处理
"""

import pytest
import pandas as pd
import datetime
from unittest.mock import patch, MagicMock

from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare


def _make_mock_pro():
    """创建 mock tushare pro API"""
    mock = MagicMock()


@pytest.mark.unit
class TestTushareConstruction:
    """测试 GinkgoTushare 构造"""

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_construction_calls_connect(self, mock_conf, mock_ts):
        """构造时应自动连接"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        source = GinkgoTushare()
        assert source.pro is not None

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_inherits_source_base(self, mock_conf, mock_ts):
        """继承 GinkgoSourceBase"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        from ginkgo.data.sources.source_base import GinkgoSourceBase
        source = GinkgoTushare()
        assert isinstance(source, GinkgoSourceBase)


@pytest.mark.unit
class TestTushareWindowCalculation:
    """测试分页窗口大小计算"""

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_daybar_window_short_span(self, mock_conf, mock_ts):
        """短日期跨度：3年内直接获取"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        source = GinkgoTushare()
        assert source._calculate_daybar_window_size(365) == 365

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_daybar_window_long_span(self, mock_conf, mock_ts):
        """长日期跨度：3年以上分段"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        source = GinkgoTushare()
        result = source._calculate_daybar_window_size(365 * 10)
        assert result == 1095 * 3

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_daybar_window_boundary_3years(self, mock_conf, mock_ts):
        """边界：刚好3年"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        source = GinkgoTushare()
        assert source._calculate_daybar_window_size(365 * 3) == 365 * 3

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_adjustfactor_window_short_span(self, mock_conf, mock_ts):
        """复权因子：2年内直接获取"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        source = GinkgoTushare()
        assert source._calculate_optimal_window_size(365) == 365

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_adjustfactor_window_long_span(self, mock_conf, mock_ts):
        """复权因子：2年以上分段"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_ts.pro_api.return_value = MagicMock()
        source = GinkgoTushare()
        result = source._calculate_optimal_window_size(365 * 5)
        assert result == 365 * 10


@pytest.mark.unit
class TestTushareFetchDaybar:
    """测试日线数据获取"""

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_single_segment_fetch(self, mock_conf, mock_ts):
        """短日期跨度：单次获取"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            "trade_date": ["20240101", "20240102"],
            "open": [10.0, 10.5],
            "high": [10.5, 11.0],
            "low": [9.8, 10.2],
            "close": [10.2, 10.8],
            "vol": [100000, 120000],
        })
        mock_pro.daily.return_value = mock_df

        source = GinkgoTushare()
        result = source.fetch_cn_stock_daybar("000001.SZ", "2024-01-01", "2024-01-02")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_empty_result_returns_empty_df(self, mock_conf, mock_ts):
        """API 返回空数据时返回空 DataFrame"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_pro.daily.return_value = pd.DataFrame()

        source = GinkgoTushare()
        result = source.fetch_cn_stock_daybar("000001.SZ", "2024-01-01", "2024-01-02")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_exception_propagates(self, mock_conf, mock_ts):
        """API 异常应传播"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_pro.daily.side_effect = Exception("API rate limit")

        source = GinkgoTushare()
        with pytest.raises(Exception, match="API rate limit"):
            source.fetch_cn_stock_daybar("000001.SZ", "2024-01-01", "2024-01-02")


@pytest.mark.unit
class TestTushareFetchStockinfo:
    """测试股票信息获取"""

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_fetch_stockinfo_returns_df(self, mock_conf, mock_ts):
        """获取股票信息返回 DataFrame"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            "ts_code": ["000001.SZ"],
            "name": ["平安银行"],
            "industry": ["银行"],
        })
        mock_pro.stock_basic.return_value = mock_df

        source = GinkgoTushare()
        result = source.fetch_cn_stockinfo()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_fetch_stockinfo_empty(self, mock_conf, mock_ts):
        """空股票信息返回空 DataFrame"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_pro.stock_basic.return_value = pd.DataFrame()

        source = GinkgoTushare()
        result = source.fetch_cn_stockinfo()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


@pytest.mark.unit
class TestTushareFetchTradeDay:
    """测试交易日获取"""

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_fetch_trade_day(self, mock_conf, mock_ts):
        """获取交易日历"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({"cal_date": ["20240101"]})
        mock_pro.trade_cal.return_value = mock_df

        source = GinkgoTushare()
        result = source.fetch_cn_stock_trade_day()

        assert isinstance(result, pd.DataFrame)

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_fetch_trade_day_empty(self, mock_conf, mock_ts):
        """交易日历为空返回空 DataFrame"""
        mock_conf.TUSHARETOKEN = "test_token"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_pro.trade_cal.return_value = pd.DataFrame()

        source = GinkgoTushare()
        result = source.fetch_cn_stock_trade_day()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
