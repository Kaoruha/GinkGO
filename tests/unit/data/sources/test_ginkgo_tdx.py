"""
GinkgoTDX 数据源单元测试（Mock mootdx API）

测试范围:
1. 构造和 bar_type 映射
2. 代码提取逻辑
3. fetch_latest_bar 参数传递
4. fetch_history_daybar 日期格式化
5. fetch_stock_list 市场拼接
6. fetch_adjustfactor 调用
7. fetch_history_transaction_detail 分页逻辑
"""

import pytest
import pandas as pd
import datetime
from unittest.mock import patch, MagicMock

from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX


@pytest.mark.unit
class TestTDXConstruction:
    """测试 GinkgoTDX 构造"""

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_construction_creates_client(self, mock_quotes):
        """构造时创建 mootdx Quotes 客户端"""
        mock_quotes.factory.return_value = MagicMock()
        tdx = GinkgoTDX()
        assert tdx.client is not None

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_inherits_source_base(self, mock_quotes):
        """继承 GinkgoSourceBase"""
        mock_quotes.factory.return_value = MagicMock()
        from ginkgo.data.sources.source_base import GinkgoSourceBase
        tdx = GinkgoTDX()
        assert isinstance(tdx, GinkgoSourceBase)

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_bar_type_mapping(self, mock_quotes):
        """bar_type 频率映射完整"""
        mock_quotes.factory.return_value = MagicMock()
        tdx = GinkgoTDX()
        assert tdx.bar_type["0"] == "5m"
        assert tdx.bar_type["4"] == "days"
        assert tdx.bar_type["7"] == "1m"
        assert tdx.bar_type["9"] == "day"
        assert len(tdx.bar_type) == 12


@pytest.mark.unit
class TestTDXFetchLatestBar:
    """测试 fetch_latest_bar"""

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_code_extraction(self, mock_quotes):
        """代码提取去掉交易所后缀"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.bars.return_value = pd.DataFrame({"open": [10.0]})

        tdx = GinkgoTDX()
        tdx.fetch_latest_bar("000001.SZ", frequency=4, count=10)
        # 应该只传数字部分给 mootdx
        mock_client.bars.assert_called_once()
        call_kwargs = mock_client.bars.call_args
        assert call_kwargs[1]["symbol"] == "000001" or call_kwargs[0][0] == "000001"

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_frequency_and_count_passed(self, mock_quotes):
        """频率和数量参数正确传递"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.bars.return_value = pd.DataFrame({"open": [10.0]})

        tdx = GinkgoTDX()
        tdx.fetch_latest_bar("600036.SH", frequency=4, count=50)
        call_kwargs = mock_client.bars.call_args[1]
        assert call_kwargs["frequency"] == 4
        assert call_kwargs["offset"] == 50


@pytest.mark.unit
class TestTDXFetchHistoryDaybar:
    """测试 fetch_history_daybar"""

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_date_formatting(self, mock_quotes):
        """日期格式化为 YYYY-MM-DD"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.k.return_value = pd.DataFrame({"open": [10.0]})

        tdx = GinkgoTDX()
        tdx.fetch_history_daybar("000001.SZ", "2024-01-01", "2024-12-31")
        call_kwargs = mock_client.k.call_args[1]
        assert call_kwargs["begin"] == "2024-01-01"
        assert call_kwargs["end"] == "2024-12-31"

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_code_extraction_for_daybar(self, mock_quotes):
        """日线获取也去掉交易所后缀"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.k.return_value = pd.DataFrame({"open": [10.0]})

        tdx = GinkgoTDX()
        tdx.fetch_history_daybar("600036.SH", "2024-01-01", "2024-12-31")
        call_kwargs = mock_client.k.call_args[1]
        assert call_kwargs["symbol"] == "600036"


@pytest.mark.unit
class TestTDXFetchStockList:
    """测试 fetch_stock_list"""

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_concatenates_sh_and_sz(self, mock_quotes):
        """合并沪深两市场股票列表"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.stocks.side_effect = [
            pd.DataFrame({"code": [1, 2]}),
            pd.DataFrame({"code": [3, 4]}),
        ]

        tdx = GinkgoTDX()
        result = tdx.fetch_stock_list()

        assert len(result) == 4
        assert mock_client.stocks.call_count == 2


@pytest.mark.unit
class TestTDXFetchAdjustfactor:
    """测试 fetch_adjustfactor"""

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_calls_xdxr(self, mock_quotes):
        """调用 mootdx xdxr 接口"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.xdxr.return_value = pd.DataFrame({"code": ["000001"]})

        tdx = GinkgoTDX()
        result = tdx.fetch_adjustfactor("000001.SZ")

        mock_client.xdxr.assert_called_once()
        call_kwargs = mock_client.xdxr.call_args[1]
        assert call_kwargs["symbol"] == "000001"


@pytest.mark.unit
class TestTDXFetchLive:
    """测试 fetch_live"""

    @patch("ginkgo.data.sources.ginkgo_tdx.Quotes")
    def test_passes_codes_to_quotes(self, mock_quotes):
        """传递代码列表给 mootdx quotes"""
        mock_client = MagicMock()
        mock_quotes.factory.return_value = mock_client
        mock_client.quotes.return_value = pd.DataFrame({"code": ["000001"]})

        tdx = GinkgoTDX()
        result = tdx.fetch_live(["000001.SZ", "600036.SH"])

        mock_client.quotes.assert_called_once()
        call_kwargs = mock_client.quotes.call_args[1]
        assert "symbol" in call_kwargs
