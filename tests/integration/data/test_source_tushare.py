import unittest
import pandas as pd
from ginkgo.libs.core.config import GCONF

try:
    from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
    from ginkgo.data.sources.source_base import GinkgoSourceBase
except ImportError:
    GinkgoTushare = None
    GinkgoSourceBase = None


class TuShareTest(unittest.TestCase):
    """TuShare数据源测试"""

    def setUp(self):
        """测试环境初始化"""
        if GinkgoTushare is None:
            self.skipTest("GinkgoTushare模块不可用")
        self.ts = GinkgoTushare()

    def test_inheritance(self):
        """测试继承关系"""
        self.assertIsInstance(self.ts, GinkgoSourceBase)
        self.assertTrue(hasattr(self.ts, "client"))

    def test_connect_method(self):
        """测试连接方法"""
        # 测试连接方法存在且可调用
        self.assertTrue(hasattr(self.ts, "connect"))
        self.assertTrue(callable(self.ts.connect))

        # 测试pro对象初始化
        self.assertIsNotNone(self.ts.pro)

    def test_fetch_trade_day(self):
        """测试获取交易日历数据"""
        if not hasattr(GCONF, "TUSHARETOKEN") or not GCONF.TUSHARETOKEN:
            self.skipTest("TUSHARETOKEN未配置")

        result = self.ts.fetch_cn_stock_trade_day()

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)

        # 验证数据结构（如果有数据）
        if not result.empty:
            expected_columns = ["cal_date", "is_open"]
            for col in expected_columns:
                self.assertIn(col, result.columns, f"缺少必要字段: {col}")

    def test_fetch_stock_info(self):
        """测试获取股票基本信息"""
        if not hasattr(GCONF, "TUSHARETOKEN") or not GCONF.TUSHARETOKEN:
            self.skipTest("TUSHARETOKEN未配置")

        result = self.ts.fetch_cn_stockinfo()

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)

        # 验证数据结构（如果有数据）
        if not result.empty:
            expected_columns = ["ts_code", "symbol", "name", "area", "industry", "list_date"]
            for col in expected_columns:
                self.assertIn(col, result.columns, f"缺少必要字段: {col}")

    def test_fetch_daybar_data(self):
        """测试获取日K线数据"""
        if not hasattr(GCONF, "TUSHARETOKEN") or not GCONF.TUSHARETOKEN:
            self.skipTest("TUSHARETOKEN未配置")

        # 使用平安银行的代码进行测试
        result = self.ts.fetch_cn_stock_daybar("000001.SZ", "20240101", "20240110")

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)

        # 验证数据结构（如果有数据）
        if not result.empty:
            expected_columns = ["ts_code", "trade_date", "open", "high", "low", "close", "vol"]
            for col in expected_columns:
                self.assertIn(col, result.columns, f"缺少必要字段: {col}")

            # 验证数据类型
            numeric_columns = ["open", "high", "low", "close", "vol"]
            for col in numeric_columns:
                if col in result.columns:
                    self.assertTrue(pd.api.types.is_numeric_dtype(result[col]), f"{col}字段应该是数值类型")

    def test_fetch_adjust_factor(self):
        """测试获取复权因子数据"""
        if not hasattr(GCONF, "TUSHARETOKEN") or not GCONF.TUSHARETOKEN:
            self.skipTest("TUSHARETOKEN未配置")

        result = self.ts.fetch_cn_stock_adjustfactor("000001.SZ", "20240101", "20240110")

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)

        # 验证数据结构（如果有数据）
        if not result.empty:
            expected_columns = ["ts_code", "trade_date", "adj_factor"]
            for col in expected_columns:
                self.assertIn(col, result.columns, f"缺少必要字段: {col}")

            # 验证复权因子为数值类型
            if "adj_factor" in result.columns:
                self.assertTrue(pd.api.types.is_numeric_dtype(result["adj_factor"]), "adj_factor字段应该是数值类型")

    def test_empty_data_handling(self):
        """测试空数据处理"""
        if not hasattr(GCONF, "TUSHARETOKEN") or not GCONF.TUSHARETOKEN:
            self.skipTest("TUSHARETOKEN未配置")

        # 使用不存在的股票代码或过早的日期
        result = self.ts.fetch_cn_stock_daybar("999999.SZ", "19900101", "19900102")

        # 验证返回空DataFrame而不是None
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty or len(result) == 0)
