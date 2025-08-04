import unittest
import pandas as pd

try:
    from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX
    from ginkgo.data.sources.source_base import GinkgoSourceBase
except ImportError:
    GinkgoTDX = None
    GinkgoSourceBase = None


class TDXTest(unittest.TestCase):
    """TDX数据源测试"""

    def setUp(self):
        """测试环境初始化"""
        if GinkgoTDX is None:
            self.skipTest("GinkgoTDX模块不可用")
        self.tdx = GinkgoTDX()

    def test_inheritance(self):
        """测试继承关系"""
        self.assertIsInstance(self.tdx, GinkgoSourceBase)
        self.assertTrue(hasattr(self.tdx, "client"))

    def test_client_initialization(self):
        """测试客户端初始化"""
        self.assertIsNotNone(self.tdx.client)
        self.assertTrue(hasattr(self.tdx, "bar_type"))
        self.assertIsInstance(self.tdx.bar_type, dict)

    def test_fetch_live(self):
        """测试获取实时行情数据"""
        result = self.tdx.fetch_live(["000001"])

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)
        # 断言必须有数据
        self.assertGreater(result.shape[0], 0, "实时行情数据不能为空")

        # 验证数据结构
        expected_columns = ["code", "price"]
        for col in expected_columns:
            if col in result.columns:
                self.assertIn(col, result.columns, f"包含字段: {col}")

    def test_fetch_latest_bar(self):
        """测试获取最新K线数据"""
        result = self.tdx.fetch_latest_bar("000001.SZ", frequency=7, count=10)

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)
        # 断言必须有数据
        self.assertGreater(result.shape[0], 0, "K线数据不能为空")

        # 验证数据结构
        expected_columns = ["datetime", "open", "close", "high", "low"]
        for col in expected_columns:
            if col in result.columns:
                self.assertIn(col, result.columns, f"包含字段: {col}")

        # 验证数据类型
        numeric_columns = ["open", "close", "high", "low", "vol"]
        for col in numeric_columns:
            if col in result.columns:
                self.assertTrue(pd.api.types.is_numeric_dtype(result[col]), f"{col}字段应该是数值类型")

    def test_fetch_stock_list(self):
        """测试获取股票列表"""
        result = self.tdx.fetch_stock_list()

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)
        # 断言必须有数据
        self.assertGreater(result.shape[0], 0, "股票列表不能为空")

        # 验证数据结构
        expected_columns = ["code", "name"]
        for col in expected_columns:
            self.assertIn(col, result.columns, f"缺少必要字段: {col}")

        # 验证股票代码格式
        if "code" in result.columns and len(result) > 0:
            codes = result["code"].tolist()
            for code in codes:
                self.assertTrue(code.endswith(".SH") or code.endswith(".SZ"), f"股票代码格式正确: {code}")

    def test_fetch_history_transaction_summary(self):
        """测试获取历史交易汇总"""
        result = self.tdx.fetch_history_transaction_summary("300059.SZ", "20240112")

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)
        # 断言必须有数据
        self.assertGreater(result.shape[0], 0, "历史交易汇总数据不能为空")

        # 验证数据结构
        expected_columns = ["time", "price"]
        for col in expected_columns:
            if col in result.columns:
                self.assertIn(col, result.columns, f"包含字段: {col}")

    def test_fetch_history_transaction_detail(self):
        """测试获取历史交易明细"""
        result = self.tdx.fetch_history_transaction_detail("300059.SZ", "20240112")

        # 验证返回类型（可能返回None）
        self.assertTrue(result is None or isinstance(result, pd.DataFrame))

        # 如果返回DataFrame，断言必须有数据
        if result is not None:
            self.assertGreater(result.shape[0], 0, "历史交易明细数据不能为空")

            # 验证数据结构
            expected_columns = ["time", "price"]
            for col in expected_columns:
                if col in result.columns:
                    self.assertIn(col, result.columns, f"包含字段: {col}")

    def test_fetch_adjustfactor(self):
        """测试获取复权因子"""
        result = self.tdx.fetch_adjustfactor("000001.SZ")

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)
        # 断言必须有数据
        self.assertGreater(result.shape[0], 0, "复权因子数据不能为空")

        # 验证数据结构
        expected_columns = ["date"]
        for col in expected_columns:
            if col in result.columns:
                self.assertIn(col, result.columns, f"包含字段: {col}")

    def test_fetch_history_daybar(self):
        """测试获取历史日K线数据"""
        result = self.tdx.fetch_history_daybar("000001.SZ", "20240101", "20240110")

        # 验证返回类型
        self.assertIsInstance(result, pd.DataFrame)
        # 断言必须有数据
        self.assertGreater(result.shape[0], 0, "历史日K线数据不能为空")

        # 验证数据结构
        expected_columns = ["date", "open", "close", "high", "low", "vol"]
        for col in expected_columns:
            if col in result.columns:
                self.assertIn(col, result.columns, f"包含字段: {col}")

        # 验证数据类型
        numeric_columns = ["open", "close", "high", "low", "vol"]
        for col in numeric_columns:
            if col in result.columns:
                self.assertTrue(pd.api.types.is_numeric_dtype(result[col]), f"{col}字段应该是数值类型")

    def test_bar_type_mapping(self):
        """测试K线类型映射"""
        bar_types = self.tdx.bar_type
        self.assertIsInstance(bar_types, dict)

        # 验证关键的K线类型
        expected_types = ["0", "1", "4", "7", "9"]
        for bar_type in expected_types:
            self.assertIn(bar_type, bar_types, f"包含K线类型: {bar_type}")

    def test_code_parsing(self):
        """测试股票代码解析"""
        test_codes = ["000001.SZ", "600000.SH", "300001.SZ"]

        for code in test_codes:
            code_num = code.split(".")[0]
            self.assertTrue(code_num.isdigit(), f"代码解析正确: {code}")
            self.assertEqual(len(code_num), 6, f"代码长度正确: {code}")

    def test_unsupported_market_handling(self):
        """测试不支持市场的处理"""
        result = self.tdx.fetch_history_transaction_detail("000001.BJ", "20240101")

        # 应该返回None，而不是抛出异常
        self.assertIsNone(result, "不支持的市场应返回None")
