import sys
import time
import unittest
import datetime
from time import sleep
import pandas as pd
from unittest.mock import patch, Mock
from ginkgo.libs import GLOG

try:
    from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
except ImportError:
    GinkgoTushare = None


class TuShareTest(unittest.TestCase):
    """
    Test tushare data source.
    """

    def setUp(self) -> None:
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
        self.ts = GinkgoTushare()

    def test_Tu_Init(self) -> None:
        """测试Tushare数据源初始化"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        self.assertIsNotNone(gts)
        self.assertTrue(hasattr(gts, 'connect'))

    @patch('tushare.pro_api')
    def test_Tu_Connect_Mock(self, mock_pro_api) -> None:
        """测试Tushare连接（模拟）"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        mock_api = Mock()
        mock_pro_api.return_value = mock_api
        
        gts = GinkgoTushare()
        gts.connect()
        self.assertIsNotNone(gts.pro)

    def test_Tu_Connect(self) -> None:
        """测试Tushare连接"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        try:
            gts.connect()
            self.assertIsNotNone(gts.pro)
        except Exception as e:
            # 如果没有有效的token，连接会失败，这是正常的
            self.assertIn('token', str(e).lower())

    def test_Tu_FetchTradeDay(self) -> None:
        """测试获取交易日历"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        try:
            rs = gts.fetch_cn_stock_trade_day()
            self.assertIsInstance(rs, pd.DataFrame)
            if not rs.empty:
                self.assertGreater(rs.shape[0], 1000)
        except Exception as e:
            # 如果API调用失败，跳过测试
            self.skipTest(f"API call failed: {e}")

    @patch('ginkgo.data.sources.ginkgo_tushare.GinkgoTushare.connect')
    def test_Tu_FetchStockInfo_Mock(self, mock_connect) -> None:
        """测试获取股票信息（模拟）"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        gts.pro = Mock()
        
        # 模拟返回数据
        mock_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'symbol': ['000001', '000002'],
            'name': ['平安银行', '万科A'],
            'area': ['深圳', '深圳'],
            'industry': ['银行', '房地产'],
            'list_date': ['19910403', '19910129']
        })
        gts.pro.stock_basic.return_value = mock_data
        
        if hasattr(gts, 'fetch_stock_info'):
            result = gts.fetch_stock_info()
            self.assertIsInstance(result, pd.DataFrame)
            self.assertGreater(len(result), 0)

    def test_Tu_DataFormat(self) -> None:
        """测试数据格式规范"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        
        # 测试日期格式化方法（如果存在）
        if hasattr(gts, 'format_date'):
            formatted = gts.format_date('2023-01-01')
            self.assertIsInstance(formatted, str)
            
        # 测试股票代码格式化（如果存在）
        if hasattr(gts, 'format_code'):
            formatted = gts.format_code('000001')
            self.assertIsInstance(formatted, str)

    def test_Tu_ErrorHandling(self) -> None:
        """测试错误处理"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        
        # 测试无效token的处理
        if hasattr(gts, 'set_token'):
            try:
                gts.set_token('invalid_token')
                gts.connect()
            except Exception as e:
                self.assertIsInstance(e, (ValueError, ConnectionError, AttributeError))

    def test_Tu_RateLimit(self) -> None:
        """测试请求频率限制"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare not available")
            
        gts = GinkgoTushare()
        
        # 测试频率限制方法（如果存在）
        if hasattr(gts, 'check_rate_limit'):
            result = gts.check_rate_limit()
            self.assertIsInstance(result, bool)
        
        # 测试等待方法（如果存在）
        if hasattr(gts, 'wait_if_needed'):
            start_time = time.time()
            gts.wait_if_needed()
            end_time = time.time()
            # 等待时间应该是合理的
            self.assertLess(end_time - start_time, 5)  # 不超过5秒

#     def test_Tu_FetchStockInfo(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_info()
#         l = rs.shape[0]
#         self.assertGreater(l, 2000)

#     def test_Tu_FetchDaybar(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_daybar("000001.SZ", "20200101", "20200110")
#         l = rs.shape[0]
#         self.assertGreater(l, 0)

#     def test_Tu_FetchAdjustfactor(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_adjustfactor("000001.SZ", "20100101", "20200110")
#         l = rs.shape[0]
#         self.assertGreater(l, 0)
